"""The method page's routes: what the product was built from, read from its files, and the
posts the annotators read, to explore and to download.

Public, and about the demo build only: a workspace has no annotation behind it.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse

from backend.map.deps import get_probes
from backend.map.store import MapBuild
from backend.method.build import build_facts, read_provenance
from backend.method.documents import (
    FIGURES,
    documents_of,
    figure_names,
    guides_of,
    questions_of,
)
from backend.method.explorer import LabelledStore
from backend.method.filters import Level, PageQuery
from backend.method.labels import labels_of
from backend.method.probe_files import probe_files_of
from backend.method.review_doc import review_of
from backend.method.schema import LabelledPage, Method
from backend.probes.pack import Probes
from backend.settings import Settings, get_settings

router = APIRouter(prefix="/method", tags=["method"])

REPOSITORY = "https://github.com/AlexAnsart/DecodeTheNoise"
MAX_PAGE = 100
# A figure changes when the report is written again, with a deploy: an hour is short enough.
FIGURE_MAX_AGE = 3600
DOWNLOAD_NAME = "labelled.jsonl"
NO_FILE = "No labelled posts are published on this server."
OTHER_MODEL = (
    "The labelled posts were embedded with another model than the one of this server's "
    "probes: no probe can be read on them."
)


@lru_cache(maxsize=1)
def _store_at(path: Path) -> LabelledStore:
    return LabelledStore(path)


def get_store(settings: Annotated[Settings, Depends(get_settings)]) -> LabelledStore:
    """One store for the process: it keeps the vectors of the file between two requests."""
    return _store_at(settings.labelled_path)


@router.get("")
def method(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[LabelledStore, Depends(get_store)],
) -> Method:
    """Every part is read from a file of the repository or of the build, now. A part whose file
    is not there is null or empty."""
    build: MapBuild | None = request.app.state.build
    # The review as this server runs it; a server started without its services shows none.
    services = getattr(request.app.state, "services", None)
    docs = settings.method_docs_dir
    guides = guides_of(docs)
    return Method(
        commit=settings.git_commit,
        repository=REPOSITORY,
        build=build_facts(build) if build else None,
        provenance=read_provenance(build.folder) if build else None,
        labels=labels_of(questions_of(guides), settings.reports_dir),
        guides=guides,
        documents=documents_of(docs),
        figures=figure_names(docs),
        probe_files=probe_files_of(settings.reports_dir),
        review=review_of(getattr(services, "reviewer", None)),
        labelled=store.summary(),
    )


@router.get("/figures/{name}")
def figure(name: str, settings: Annotated[Settings, Depends(get_settings)]) -> FileResponse:
    docs = settings.method_docs_dir
    # The name is looked up in the listing and never joined to a path as it came.
    if name not in figure_names(docs):
        raise HTTPException(status_code=404, detail="No figure with this name.")
    return FileResponse(
        docs / FIGURES / name,
        media_type="image/png",
        headers={"Cache-Control": f"public, max-age={FIGURE_MAX_AGE}"},
    )


@router.get("/labelled")
def labelled(
    request: Request,
    store: Annotated[LabelledStore, Depends(get_store)],
    probes: Annotated[Probes, Depends(get_probes)],
    label: str = "",
    answer: str = "",
    split: str = "",
    round_name: Annotated[str, Query(alias="round")] = "",
    kind: str = "",
    probe: str = "",
    level: Level | None = None,
    q: str = "",
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = 25,
) -> LabelledPage:
    """A page of the labelled posts. `label` keeps the posts that have a settled answer on it,
    `answer` those with this answer; `split`, `round` and `kind` (`annotation`, `second reader`)
    keep theirs; `q` keeps the posts whose text holds every word. `probe` orders the posts by
    its score, highest first, and `level` compares it with the settled answer on its own label
    (`flagged`, `agreed`, `false alarm`, `missed`). The scores are computed now, from the vector
    of each post."""
    file_key = store.embedding_key()
    if file_key is None:
        return LabelledPage(total=0, posts=[])
    # The probes of this server read the vectors of its own embedding model only.
    scored = file_key == request.app.state.embedder.key
    if probe:
        if probe not in {info.key for info in probes.shown()}:
            raise HTTPException(status_code=404, detail="No probe with this key is shown.")
        if not scored:
            raise HTTPException(status_code=409, detail=OTHER_MODEL)
    query = PageQuery(
        label=label or None,
        answer=answer or None,
        split=split or None,
        round=round_name or None,
        kind=kind or None,
        probe=probe or None,
        level=level if probe else None,
        words=tuple(q.split()),
        offset=offset,
        limit=limit,
    )
    return store.page(probes, query, scored=scored)


@router.get(f"/{DOWNLOAD_NAME}")
def download(store: Annotated[LabelledStore, Depends(get_store)]) -> StreamingResponse:
    """Every labelled post with its readings, one JSON object per line."""
    if store.summary() is None:
        raise HTTPException(status_code=404, detail=NO_FILE)
    return StreamingResponse(
        store.lines(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{DOWNLOAD_NAME}"'},
    )

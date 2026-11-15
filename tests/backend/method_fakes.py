"""The method routes served from temp folders: documents, reports, a file of labelled posts
and a hand-made probe pack. Nothing is there until a test writes it."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from analyze_fakes import FakeEmbedder
from fastapi import FastAPI
from fastapi.testclient import TestClient
from probe_fakes import PACK_DIMS, PACK_EMBEDDING_KEY, FakeProbe, vector_with_logits, write_pack

from backend.method.labelled import ANNOTATION, LabelledRecord, write_labelled
from backend.method.routes import router
from backend.method.schema import Reading
from backend.probes.pack import load_probes
from backend.settings import Settings, get_settings

COMMIT = "abc1234"
# Both probes flag from a raw output of 0 and are `probable` from 2.
PROBES = [
    FakeProbe("call_vote", possible_cut=0.0, probable_cut=2.0),
    FakeProbe("theme:sport", possible_cut=0.0, probable_cut=2.0),
]
FLAGGED, NOT_FLAGGED = 3.0, -3.0


@dataclass
class MethodApi:
    client: TestClient
    app: FastAPI
    docs: Path
    reports: Path
    labelled: Path
    # The arrays of the probe pack, to make a vector a probe scores as wanted.
    arrays: dict[str, np.ndarray]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def method_api(root: Path) -> MethodApi:
    docs, reports = root / "docs", root / "reports"
    labelled = root / "method" / "labelled.sqlite"
    arrays = write_pack(root / "pack", PROBES)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.build = None
    app.state.probes = load_probes(root / "pack", PACK_EMBEDDING_KEY)
    app.state.embedder = FakeEmbedder(
        key=PACK_EMBEDDING_KEY, default=np.zeros(PACK_DIMS, dtype=np.float32)
    )
    settings = Settings(
        _env_file=None,
        method_docs_dir=docs,
        reports_dir=reports,
        labelled_path=labelled,
        git_commit=COMMIT,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    return MethodApi(TestClient(app), app, docs, reports, labelled, arrays)


def post(
    key: str,
    text: str,
    answers: dict[str, str],
    split: str = "train",
    round_name: str = "m1",
    kind: str = ANNOTATION,
    stratum: str = "random",
) -> LabelledRecord:
    """A post read once, by a reader who answered what was settled."""
    reading = Reading(
        reader=f"{round_name}-calls-a-001", answers=answers or {"call_vote": "yes"}, quotes={}
    )
    return LabelledRecord(
        id=key,
        text=text,
        split=split,
        round=round_name,
        kind=kind,
        stratum=stratum,
        answers=answers,
        readings=[reading],
    )


def write_posts(
    api: MethodApi,
    posts: list[tuple[LabelledRecord, list[float]]],
    embedding_key: str = PACK_EMBEDDING_KEY,
) -> None:
    """Each post comes with the raw output wanted from each probe of `PROBES`, in order."""
    vectors = np.stack([vector_with_logits(api.arrays, logits) for _, logits in posts])
    write_labelled(api.labelled, [record for record, _ in posts], vectors, embedding_key)

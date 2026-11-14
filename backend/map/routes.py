"""The map itself: a JSON manifest, one binary file of typed arrays, and what the probes read.

Mounted twice: under `/api` for the demo build, under `/api/v1` for the caller's workspace.
"""

from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response

from backend.map.deps import get_build, get_probes
from backend.map.schema import MapManifest, PointReading
from backend.map.store import MapBuild
from backend.probes.pack import Probes
from backend.review.schema import NO_REVIEW, Review
from backend.workspace.snapshot import build_at

router = APIRouter(prefix="/map", tags=["map"])

_OCTETS = "application/octet-stream"


@router.get("")
def manifest(
    build: Annotated[MapBuild, Depends(get_build)], probes: Annotated[Probes, Depends(get_probes)]
) -> MapManifest:
    return build.manifest.model_copy(update={"probes": list(probes.shown())})


MOVED = "The map changed since this version: read the manifest again."


@router.get("/buffers")
def buffers(
    request: Request, build: Annotated[MapBuild, Depends(get_build)], v: int | None = None
) -> Response:
    if build.blob is not None:
        # A workspace map changes: the buffers asked for are those of the manifest just read,
        # even when points arrived in between. Arrays of two versions never mix.
        if v is not None and v != build.manifest.version:
            earlier = build_at(request.state.workspace, v)
            if earlier is None or earlier.blob is None:
                raise HTTPException(status_code=409, detail=MOVED)
            build = earlier
        return Response(build.blob, media_type=_OCTETS, headers={"Cache-Control": "no-store"})
    # The front end adds the build name to the URL, so a URL never changes content.
    return FileResponse(
        build.buffers_path,
        media_type=_OCTETS,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


def probe_scores(request: Request, build: MapBuild, probes: Probes) -> np.ndarray:
    """One row per point, one column per probe. Kept for a build made offline, which never
    changes; computed on demand for a workspace (one matrix product)."""
    if build.manifest.live:
        return probes.scores(build.vectors)
    cache: dict[str, np.ndarray] = request.app.state.score_cache
    if build.manifest.build not in cache:
        cache[build.manifest.build] = probes.scores(build.vectors)
    return cache[build.manifest.build]


@router.get("/scores/{key}")
def scores(
    key: str,
    request: Request,
    build: Annotated[MapBuild, Depends(get_build)],
    probes: Annotated[Probes, Depends(get_probes)],
) -> Response:
    """float32 per point: the probe's score, 0.5 where `possible` starts and 0.8 `probable`."""
    shown = {info.key for info in probes.shown()}
    if key not in shown:
        raise HTTPException(status_code=404, detail="No probe with this key is shown.")
    column = probe_scores(request, build, probes)[:, probes.column(key)]
    return Response(np.ascontiguousarray(column, dtype="<f4").tobytes(), media_type=_OCTETS)


def _review(build: MapBuild, index: int) -> Review | None:
    if not build.manifest.live:
        return None
    with build.items_lock:
        row = build.items.execute("SELECT review FROM items WHERE idx = ?", (index,)).fetchone()
    if row is None or row[0] is None:
        return NO_REVIEW
    return Review.model_validate_json(row[0])


@router.get("/reading/{index}")
def reading(
    index: int,
    build: Annotated[MapBuild, Depends(get_build)],
    probes: Annotated[Probes, Depends(get_probes)],
) -> PointReading:
    if not 0 <= index < build.manifest.n:
        raise HTTPException(status_code=404, detail="No point with this index on the map.")
    row = probes.scores(build.vectors[index : index + 1])[0]
    return PointReading(
        index=index,
        probes=probes.readings(row),
        scores=probes.score_map(row),
        review=_review(build, index),
    )

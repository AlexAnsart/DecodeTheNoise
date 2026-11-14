"""Posts of the demo dataset, in the format the API takes: what "send sample posts" sends.

They go through the same route as anyone's posts. Taken from a few zones, so the map they
build shows clear subjects, and always the same ones, so their vectors are embedded once.
"""

from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from backend.ingest.rows import to_datetime
from backend.ingest.schema import ItemIn
from backend.items.routes import read_items
from backend.map.deps import get_build
from backend.map.store import MapBuild

router = APIRouter(tags=["sample"])

SEED = 7
ZONES = 8
MAX_COUNT = 500
_KINDS = frozenset({"original", "reply", "repost", "quote"})


class SamplePosts(BaseModel):
    # The build the posts come from.
    source: str
    items: list[ItemIn]


def _zone_of_point(build: MapBuild) -> np.ndarray | None:
    column = next((c for c in build.manifest.columns if c.key == "zone"), None)
    spec = build.manifest.buffers.get(column.buffer) if column else None
    if spec is None:
        return None
    return np.fromfile(
        build.buffers_path,
        dtype=np.dtype(spec.dtype).newbyteorder("<"),
        count=spec.length,
        offset=spec.offset,
    )


def sample_indices(build: MapBuild, count: int) -> list[int]:
    """`count` points from a few zones spread over the largest, the same on every call."""
    rng = np.random.default_rng(SEED)
    n = build.manifest.n
    zone = _zone_of_point(build)
    if zone is None or not build.manifest.zones:
        return sorted(rng.choice(n, size=min(count, n), replace=False).tolist())
    ranks = np.unique(np.linspace(0, min(len(build.manifest.zones), 3 * ZONES) - 1, ZONES))
    picked: list[int] = []
    for rank in ranks.astype(int):
        members = np.flatnonzero(zone == rank)
        take = min(len(members), count // len(ranks))
        picked.extend(rng.choice(members, size=take, replace=False).tolist())
    return sorted(picked)


@router.get("/sample")
def sample(
    request: Request,
    build: Annotated[MapBuild, Depends(get_build)],
    count: Annotated[int, Query(ge=1, le=MAX_COUNT)] = 200,
) -> SamplePosts:
    cache: dict[tuple[str, int], SamplePosts] = request.app.state.sample_cache
    key = (build.manifest.build, count)
    if key not in cache:
        items = []
        for item in read_items(build, sample_indices(build, count)):
            kind = item.attrs.get("post_type")
            items.append(
                ItemIn(
                    id=item.item_id,
                    text=item.text,
                    created_at=to_datetime(item.created_at),
                    actor_id=item.actor_id or None,
                    kind=kind if kind in _KINDS else None,
                    urls=item.urls[:20],
                    lang=item.lang,
                    source="demo",
                )
            )
        cache[key] = SamplePosts(source=build.manifest.build, items=items)
    return cache[key]

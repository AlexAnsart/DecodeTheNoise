"""Reads items by point index from the map's database, for tooltips, cards and lists."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.items.schema import Item, ItemsRequest, ItemsResponse
from backend.map.deps import get_build
from backend.map.store import MapBuild

router = APIRouter(prefix="/map/items", tags=["map"])

_COLUMNS = "idx, item_id, actor_id, text, created_at, lang, repost_of, urls, attrs"


def read_items(build: MapBuild, indices: list[int]) -> list[Item]:
    """Items in the order asked; an index outside the build is skipped."""
    if not indices:
        return []
    marks = ",".join("?" * len(indices))
    with build.items_lock:
        rows = build.items.execute(
            f"SELECT {_COLUMNS} FROM items WHERE idx IN ({marks})", indices
        ).fetchall()
    by_index = {
        row[0]: Item(
            index=row[0],
            item_id=row[1],
            # A workspace item may have no actor.
            actor_id=row[2] or "",
            text=row[3],
            created_at=row[4],
            lang=row[5],
            repost_of=row[6],
            urls=json.loads(row[7]),
            attrs=json.loads(row[8]),
        )
        for row in rows
    }
    return [by_index[i] for i in indices if i in by_index]


@router.post("")
def items(body: ItemsRequest, build: Annotated[MapBuild, Depends(get_build)]) -> ItemsResponse:
    return ItemsResponse(items=read_items(build, body.indices))

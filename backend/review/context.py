"""What a review reads about the points of a map: the text of a point, the probes that flag
it, its nearest points and the other items of its actor. The same code reads the demo build
and a workspace: both are a `MapBuild`.
"""

import numpy as np

from backend.analyze.place import strongest
from backend.map.store import MapBuild
from backend.probes.scoring import Probes
from backend.review.prompt import MAX_ACTOR_ITEMS, MAX_NEIGHBOURS, ReviewRequest
from backend.workspace.schema import ReviewMode

_VARIABLES = 500


def _by_index(build: MapBuild, column: str, indices: list[int]) -> dict[int, str | None]:
    """One column of the items behind the given points."""
    out: dict[int, str | None] = {}
    with build.items_lock:
        for start in range(0, len(indices), _VARIABLES):
            part = indices[start : start + _VARIABLES]
            marks = ",".join("?" * len(part))
            query = f"SELECT idx, {column} FROM items WHERE idx IN ({marks})"
            out.update(dict(build.items.execute(query, part)))
    return out


def texts_of(build: MapBuild, indices: list[int]) -> dict[int, str]:
    return {index: text or "" for index, text in _by_index(build, "text", indices).items()}


def actors_of(build: MapBuild, indices: list[int]) -> dict[int, str | None]:
    return _by_index(build, "actor_id", indices)


def request_at(
    build: MapBuild, probes: Probes, index: int, mode: ReviewMode, min_score: float
) -> ReviewRequest | None:
    """The review of one point: its text, the probes that send it to the review under `mode`,
    and its context. None when the point has no item."""
    with build.items_lock:
        row = build.items.execute(
            "SELECT text, actor_id FROM items WHERE idx = ?", (index,)
        ).fetchone()
        same_actor = (
            build.items.execute(
                "SELECT text FROM items WHERE actor_id = ? AND idx != ? "
                "ORDER BY created_at DESC LIMIT ?",
                (row[1], index, MAX_ACTOR_ITEMS),
            ).fetchall()
            if row is not None and row[1]
            else []
        )
    if row is None:
        return None
    vector = build.vectors[index]
    flagged = probes.triggers(probes.scores(vector[None, :])[0], mode, min_score)
    cosines = build.vectors @ vector
    # A point is not its own neighbour.
    cosines[index] = -np.inf
    near = strongest(cosines, MAX_NEIGHBOURS)[0].tolist()
    texts = texts_of(build, near)
    return ReviewRequest(
        text=row[0],
        probes=tuple(flagged),
        neighbours=tuple(texts[i] for i in near if i in texts),
        actor_items=tuple(found[0] for found in same_actor),
    )

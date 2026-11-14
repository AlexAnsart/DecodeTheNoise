"""Runs the LLM review of one flagged item in the background, and stores what it read."""

import logging
from collections.abc import Hashable

import httpx

from backend.ingest.rows import Row, row_of, rows_at
from backend.map.schema import NO_NEIGHBOUR
from backend.review.reader import ReviewRequest, review_item
from backend.review.schema import Review
from backend.services import Services
from backend.workspace.state import Workspace

logger = logging.getLogger(__name__)

NEIGHBOUR_TEXTS = 8
ACTOR_TEXTS = 5


def _request(services: Services, workspace: Workspace, row: Row) -> ReviewRequest | None:
    """What the review reads: the item, the probes that flagged it, and its context."""
    index = row.idx
    if index is None or index >= workspace.n:
        return None
    settings = workspace.settings
    scores = services.probes.scores(workspace.vectors[index][None, :])[0]
    probes = services.probes.triggers(scores, settings.review_mode, settings.review_min_score)
    if not probes:
        return None
    near = [int(i) for i in workspace.knn.index[index] if i != NO_NEIGHBOUR][:NEIGHBOUR_TEXTS]
    with workspace.db_lock:
        neighbours = rows_at(workspace.db, near)
        same_actor = (
            workspace.db.execute(
                "SELECT text FROM items WHERE actor_id = ? AND item_id != ? "
                "ORDER BY created_at DESC LIMIT ?",
                (row.actor_id, row.item_id, ACTOR_TEXTS),
            ).fetchall()
            if row.actor_id
            else []
        )
    return ReviewRequest(
        text=row.text,
        probes=tuple(probes),
        neighbours=tuple(neighbours[i].text for i in near if i in neighbours),
        actor_items=tuple(found[0] for found in same_actor),
    )


def _store(workspace: Workspace, row: Row, review: Review | None) -> None:
    with workspace.lock:
        with workspace.db_lock, workspace.db:
            # The item was sent again with another text meanwhile: this review is not about it.
            workspace.db.execute(
                "UPDATE items SET review = ? WHERE item_id = ? AND content_hash = ?",
                (review.model_dump_json() if review else None, row.item_id, row.content_hash),
            )
        workspace.touch()


def review_flagged(services: Services, key: Hashable) -> None:
    if not isinstance(key, tuple) or services.chat is None:
        return
    workspace_id, item_id = key
    workspace = services.workspaces.get(workspace_id)
    if workspace is None:
        return
    with workspace.lock:
        with workspace.db_lock:
            row = row_of(workspace.db, item_id)
        request = _request(services, workspace, row) if row is not None else None
    if row is None:
        return
    if request is None:
        _store(workspace, row, None)
    else:
        try:
            review = review_item(services.chat, services.llm_model, request)
        except httpx.HTTPError as error:
            logger.warning("review of %s in %s failed: %s", item_id, workspace_id, error)
            review = Review(status="failed", reason="The LLM did not answer.")
        _store(workspace, row, review)
    services.changed(workspace)

"""Runs the LLM review of one flagged item in the background, and stores what it read."""

import logging
from collections.abc import Hashable

import httpx

from backend.ingest.rows import Row, row_of
from backend.review.context import request_at
from backend.review.prompt import ReviewRequest
from backend.review.schema import Review
from backend.services import Services
from backend.workspace.snapshot import build_of
from backend.workspace.state import Workspace

logger = logging.getLogger(__name__)


def _request(services: Services, workspace: Workspace, row: Row) -> ReviewRequest | None:
    """What the review reads: the item, the probes that send it there under the settings of
    the workspace, and its context. None when no probe sends it any more."""
    index = row.idx
    if index is None or index >= workspace.n:
        return None
    settings = workspace.settings
    asked = request_at(
        build_of(workspace), services.probes, index, settings.review_mode, settings.review_min_score
    )
    return asked if asked is not None and asked.probes else None


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
    reviewer = services.reviewer
    if not isinstance(key, tuple) or reviewer.chat is None:
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
            # The same question is answered from the cache: it is never paid twice.
            review = reviewer.item(request)
        except httpx.HTTPError as error:
            logger.warning("review of %s in %s failed: %s", item_id, workspace_id, error)
            review = Review(status="failed", reason="The LLM did not answer.")
        _store(workspace, row, review)
    services.changed(workspace)

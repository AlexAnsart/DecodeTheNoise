"""Takes items into a workspace: stores them as sent, then embeds them and sets each one
down on the map. The same code serves one post answered at once and a batch worked through in
the background. Every group of posts embedded leaves a line in the log: how many came from the
cache, how long the model took, what still waits.
"""

import logging
import time
from dataclasses import dataclass

import numpy as np

from backend.accounts.limits import ALL_WORKSPACES, GLOBAL_REVIEWS_PER_DAY, REVIEWS
from backend.ingest.rows import (
    content_hash,
    count_pending,
    embedded_text,
    known_hashes,
    pending_rows,
    row_of,
    upsert,
)
from backend.ingest.schema import ItemIn, Rejected
from backend.review.schema import Review
from backend.services import Services
from backend.workspace.files import PENDING, PLACED, append_vectors, write_vector
from backend.workspace.state import Workspace

logger = logging.getLogger(__name__)

FULL = "The workspace is full: {limit} items at most. Empty it to send more."


@dataclass(frozen=True)
class Stored:
    accepted: int
    updated: int
    unchanged: int
    rejected: list[Rejected]


def store_items(workspace: Workspace, items: list[ItemIn]) -> Stored:
    """Writes the items as sent. Nothing is embedded here: new texts wait as pending."""
    now = int(time.time() * 1000)
    accepted = updated = unchanged = 0
    rejected: list[Rejected] = []
    # The last item of the request wins when an id is sent twice.
    by_id = {item.id: item for item in items}
    with workspace.lock, workspace.db_lock, workspace.db:
        known = known_hashes(workspace.db, list(by_id))
        room = workspace.limits.items - workspace.items
        for item in by_id.values():
            before = known.get(item.id)
            if before is None and accepted >= room:
                reason = FULL.format(limit=workspace.limits.items)
                rejected.append(Rejected(id=item.id, reason=reason))
                continue
            if before is not None and before[0] == content_hash(item.text.strip()):
                unchanged += 1
                continue
            upsert(workspace.db, item, placed=before is not None and before[1] is not None, now=now)
            if before is None:
                accepted += 1
            else:
                updated += 1
        workspace.items += accepted
        workspace.set_pending(count_pending(workspace.db))
    return Stored(accepted, updated, unchanged, rejected)


def review_state(services: Services, workspace: Workspace, scores: np.ndarray) -> Review | None:
    """Whether the probes send this item to the LLM review, under the settings of the
    workspace. `scores` is the score of the item for each probe."""
    settings = workspace.settings
    if not services.probes.triggers(scores, settings.review_mode, settings.review_min_score):
        return None
    if services.chat is None:
        return Review(status="skipped", reason="No LLM is configured on this server.")
    if services.accounts.used_today(workspace.id, REVIEWS) >= workspace.limits.reviews_per_day:
        return Review(status="skipped", reason="The daily review limit of this workspace is used.")
    if services.accounts.used_today(ALL_WORKSPACES, REVIEWS) >= GLOBAL_REVIEWS_PER_DAY:
        return Review(status="skipped", reason="The daily review limit of this server is used.")
    services.accounts.use(workspace.id, REVIEWS)
    services.accounts.use(ALL_WORKSPACES, REVIEWS)
    return Review(status="queued")


def _log_group(workspace: Workspace, cached: int, computed: int, seconds: float) -> None:
    speed = f"{computed / seconds:.1f} a second" if computed else "no model call"
    logger.info(
        "workspace %s: %d posts placed, %d from the cache, %d embedded in %.2fs (%s), %d waiting",
        workspace.id,
        cached + computed,
        cached,
        computed,
        seconds,
        speed,
        workspace.pending,
    )


def place_pending(
    services: Services, workspace: Workspace, limit: int, only: str | None = None
) -> int:
    """Embeds up to `limit` waiting items (or the one asked for) and places them. Returns how
    many it worked on. Raises `httpx.HTTPError` when the embedding model does not answer."""
    with workspace.db_lock:
        rows = pending_rows(workspace.db, limit, only)
    if not rows:
        return 0
    # The slow part, outside every lock.
    embedded = services.embedder.embed_counted([embedded_text(row.text) for row in rows])
    vectors = embedded.vectors
    probe_scores = services.probes.scores(vectors)
    to_review: list[str] = []
    with workspace.lock:
        fresh: list[np.ndarray] = []
        with workspace.db_lock, workspace.db:
            for row, vector, scores in zip(rows, vectors, probe_scores, strict=True):
                current = row_of(workspace.db, row.item_id)
                # Emptied or sent again with another text while it was being embedded.
                if (
                    current is None
                    or current.status != PENDING
                    or current.content_hash != row.content_hash
                ):
                    continue
                review = review_state(services, workspace, scores)
                if current.idx is None:
                    index = workspace.add_point(vector, float(row.created_at or 0), row.actor_id)
                    fresh.append(vector)
                else:
                    index = current.idx
                    workspace.replace_point(index, vector)
                    write_vector(workspace.folder, index, vector)
                    workspace.db.execute("DELETE FROM items_fts WHERE rowid = ?", (index,))
                workspace.db.execute(
                    "UPDATE items SET idx = ?, status = ?, review = ? WHERE item_id = ?",
                    (index, PLACED, review.model_dump_json() if review else None, row.item_id),
                )
                workspace.db.execute(
                    "INSERT INTO items_fts(rowid, text) VALUES (?, ?)", (index, row.text)
                )
                if review is not None and review.status == "queued":
                    to_review.append(row.item_id)
            finished = workspace.set_pending(count_pending(workspace.db))
        if fresh:
            append_vectors(workspace.folder, np.stack(fresh))
            workspace.settle_arrivals()
        # The model answered: whatever stopped the embedding before is over.
        workspace.ingest_error, workspace.ingest_failures = None, 0
        workspace.touch()
    _log_group(workspace, embedded.cached, embedded.computed, embedded.seconds)
    if finished:
        logger.info(
            "workspace %s: batch of %d posts placed in %.1fs",
            workspace.id,
            finished,
            time.monotonic() - workspace.batch_started,
        )
    if services.jobs is not None:
        for item_id in to_review:
            services.jobs.review.submit((workspace.id, item_id))
    services.changed(workspace)
    return len(rows)

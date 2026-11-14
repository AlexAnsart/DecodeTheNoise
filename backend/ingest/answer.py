"""Writes the answer about one item: what the probes read in it, and what surrounds it."""

import numpy as np
from pydantic import ValidationError

from backend.ingest.context import context_of
from backend.ingest.rows import embedded_text, is_long_enough, row_of
from backend.ingest.schema import ItemIn, ItemReading, ItemResult, Outcome
from backend.review.schema import NO_REVIEW, Review
from backend.services import Services, counts_of
from backend.workspace.files import PENDING, SHORT
from backend.workspace.state import Workspace

TOO_SHORT = "The text is too short to be placed: 20 characters at least, links left out."
WAITING = "The item waits to be embedded. Ask again in a moment."


def parse_review(stored: str | None) -> Review:
    if stored is None:
        return NO_REVIEW
    try:
        return Review.model_validate_json(stored)
    except ValidationError:
        return NO_REVIEW


def reading_of(
    services: Services, vector: np.ndarray, lang: str | None, review: Review
) -> ItemReading:
    scores = services.probes.scores(vector[None, :])[0]
    return ItemReading(
        lang=lang,
        probes=services.probes.readings(scores),
        scores=services.probes.score_map(scores),
        review=review,
    )


def _unplaced(
    workspace: Workspace, item_id: str, stored: bool, outcome: Outcome, reason: str
) -> ItemResult:
    return ItemResult(
        id=item_id,
        stored=stored,
        outcome=outcome,
        reason=reason,
        index=None,
        embedding_key=workspace.embedding_key,
        item=None,
        context=None,
        workspace=counts_of(workspace),
    )


def _as_list(vector: np.ndarray, wanted: bool) -> list[float] | None:
    return [round(float(value), 5) for value in vector] if wanted else None


def result_of(
    services: Services, workspace: Workspace, item_id: str, neighbours: int, vector: bool = False
) -> ItemResult | None:
    """The answer about a stored item, as the workspace is now. None when it is not stored."""
    with workspace.lock:
        with workspace.db_lock:
            row = row_of(workspace.db, item_id)
        if row is None:
            return None
        if row.status == SHORT:
            return _unplaced(workspace, item_id, True, "not enough evidence", TOO_SHORT)
        if row.status == PENDING or row.idx is None:
            return _unplaced(workspace, item_id, True, "queued", WAITING)
        embedding = workspace.vectors[row.idx]
        return ItemResult(
            id=item_id,
            stored=True,
            outcome="placed",
            reason=None,
            index=row.idx,
            embedding_key=workspace.embedding_key,
            item=reading_of(services, embedding, row.lang, parse_review(row.review)),
            context=context_of(workspace, embedding, row.text, row.idx, row.actor_id, neighbours),
            vector=_as_list(embedding, vector),
            workspace=counts_of(workspace),
        )


def analyse_only(
    services: Services, workspace: Workspace, item: ItemIn, neighbours: int, vector: bool = False
) -> ItemResult:
    """Reads an item against the workspace without keeping it."""
    text = item.text.strip()
    if not is_long_enough(text):
        return _unplaced(workspace, item.id, False, "not enough evidence", TOO_SHORT)
    embedding = services.embedder.embed([embedded_text(text)])[0]
    with workspace.lock:
        return ItemResult(
            id=item.id,
            stored=False,
            outcome="placed",
            reason=None,
            index=None,
            embedding_key=workspace.embedding_key,
            item=reading_of(services, embedding, item.lang, NO_REVIEW),
            context=context_of(workspace, embedding, text, None, item.actor_id, neighbours),
            vector=_as_list(embedding, vector),
            workspace=counts_of(workspace),
        )

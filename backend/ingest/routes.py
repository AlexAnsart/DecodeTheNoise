"""The public API: send one post and get its reading back, send a batch, ask about an item.

Expected cost of one post (to measure on the server after any change): one embedding, unless
the text was seen before; one product of the workspace's vectors by the new one; one small
product per probe; a few database writes. No LLM call: the review runs in the background.
"""

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from backend.accounts.deps import get_services, get_workspace, limit_batches, limit_items
from backend.ingest.answer import analyse_only, result_of
from backend.ingest.process import place_pending, store_items
from backend.ingest.schema import (
    DEFAULT_NEIGHBOURS,
    MAX_NEIGHBOURS,
    BatchAccepted,
    BatchIn,
    ItemIn,
    ItemResult,
    Rejected,
)
from backend.services import Services, counts_of
from backend.workspace.state import Workspace

logger = logging.getLogger(__name__)

router = APIRouter(tags=["items"])

Neighbours = Annotated[int, Query(ge=0, le=MAX_NEIGHBOURS)]
STALE = (
    "This workspace was built with another embedding model. Empty it "
    "(DELETE /api/v1/workspace/items) to start again with the current one."
)
MODEL_DOWN = "The embedding model did not answer. The item is stored and will be placed later."


def _usable(workspace: Workspace, services: Services) -> None:
    if workspace.embedding_key != services.embedder.key:
        raise HTTPException(status_code=409, detail=STALE)


@router.post("/items", dependencies=[Depends(limit_items)])
def send_item(
    body: ItemIn,
    workspace: Annotated[Workspace, Depends(get_workspace)],
    services: Annotated[Services, Depends(get_services)],
    store: bool = True,
    neighbours: Neighbours = DEFAULT_NEIGHBOURS,
    vector: bool = False,
) -> ItemResult:
    _usable(workspace, services)
    try:
        if not store:
            return analyse_only(services, workspace, body, neighbours, vector)
        stored = store_items(workspace, [body])
        if stored.rejected:
            raise HTTPException(status_code=409, detail=stored.rejected[0].reason)
        place_pending(services, workspace, 1, only=body.id)
    except httpx.HTTPError as error:
        # The item stays stored as pending: the background job places it when the model is back.
        if store and services.jobs is not None:
            services.jobs.ingest.submit(workspace.id)
        raise HTTPException(status_code=503, detail=MODEL_DOWN) from error
    result = result_of(services, workspace, body.id, neighbours, vector)
    if result is None:
        raise HTTPException(status_code=409, detail="The workspace was emptied meanwhile.")
    return result


def _first_error(error: ValidationError) -> str:
    first = error.errors()[0]
    where = ".".join(str(part) for part in first["loc"])
    return f"{where}: {first['msg']}" if where else str(first["msg"])


@router.post("/items/batch", status_code=202, dependencies=[Depends(limit_batches)])
def send_batch(
    body: BatchIn,
    workspace: Annotated[Workspace, Depends(get_workspace)],
    services: Annotated[Services, Depends(get_services)],
) -> BatchAccepted:
    _usable(workspace, services)
    items: list[ItemIn] = []
    rejected: list[Rejected] = []
    for raw in body.items:
        try:
            items.append(ItemIn.model_validate(raw))
        except ValidationError as error:
            given = raw.get("id")
            rejected.append(
                Rejected(id=given if isinstance(given, str) else None, reason=_first_error(error))
            )
    stored = store_items(workspace, items)
    logger.info(
        "workspace %s: batch of %d received: %d new, %d changed, %d unchanged, %d refused, "
        "%d waiting",
        workspace.id,
        len(body.items),
        stored.accepted,
        stored.updated,
        stored.unchanged,
        len(rejected) + len(stored.rejected),
        workspace.pending,
    )
    if services.jobs is not None and workspace.pending:
        services.jobs.ingest.submit(workspace.id)
    services.changed(workspace)
    return BatchAccepted(
        accepted=stored.accepted,
        updated=stored.updated,
        unchanged=stored.unchanged,
        rejected=[*rejected, *stored.rejected],
        workspace=counts_of(workspace),
    )


@router.get("/items/{item_id:path}")
def read_item(
    item_id: str,
    workspace: Annotated[Workspace, Depends(get_workspace)],
    services: Annotated[Services, Depends(get_services)],
    neighbours: Neighbours = DEFAULT_NEIGHBOURS,
    vector: bool = False,
) -> ItemResult:
    result = result_of(services, workspace, item_id, neighbours, vector)
    if result is None:
        raise HTTPException(status_code=404, detail="No item with this id in the workspace.")
    return result

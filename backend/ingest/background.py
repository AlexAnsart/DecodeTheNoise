"""Works through the items a workspace has waiting, a few at a time, so that several
workspaces sending batches take turns and the map grows while the batch is embedded.

When the embedding model does not answer, the posts stay stored, the workspace says so to
whoever watches it, and the job is tried again after a growing wait.
"""

import logging

import httpx

from backend.ingest.embedder import CHUNK
from backend.ingest.process import place_pending
from backend.services import Services
from backend.workspace.state import Workspace

logger = logging.getLogger(__name__)

# Seconds before each new try after a failure of the model; the last one repeats.
RETRY_SECONDS = (5, 15, 30, 60)
MODEL_SILENT = (
    "The embedding model did not answer. Your posts are kept; the server tries again in {wait} s."
)


def _failed(services: Services, workspace: Workspace, error: httpx.HTTPError) -> None:
    with workspace.lock:
        workspace.ingest_failures += 1
        failures = workspace.ingest_failures
        wait = RETRY_SECONDS[min(failures, len(RETRY_SECONDS)) - 1]
        workspace.ingest_error = MODEL_SILENT.format(wait=wait)
        waiting = workspace.pending
    logger.warning(
        "workspace %s: the embedding model failed (%s: %s), %d posts waiting, try %d in %ds",
        workspace.id,
        type(error).__name__,
        error,
        waiting,
        failures + 1,
        wait,
    )
    services.changed(workspace)
    if services.jobs is not None:
        services.jobs.ingest.submit_later(workspace.id, wait)


def embed_pending(services: Services, workspace_id: str) -> None:
    workspace = services.workspaces.get(workspace_id)
    if workspace is None or workspace.embedding_key != services.embedder.key:
        return
    try:
        place_pending(services, workspace, CHUNK)
    except httpx.HTTPError as error:
        _failed(services, workspace, error)
        return
    # Back to the end of the queue: the chunk of another workspace goes first.
    if workspace.pending and services.jobs is not None:
        services.jobs.ingest.submit(workspace_id)


def resume(services: Services, workspace: Workspace) -> None:
    """A workspace just read from disk takes up what a restart interrupted."""
    if services.jobs is None:
        return
    if workspace.pending:
        logger.info("workspace %s: %d posts were waiting, resumed", workspace.id, workspace.pending)
        services.jobs.ingest.submit(workspace.id)
    with workspace.lock:
        due = workspace.refresh_due() and not workspace.refresh_queued
        if due:
            workspace.refresh_queued = True
    if due:
        services.jobs.refresh.submit(workspace.id)

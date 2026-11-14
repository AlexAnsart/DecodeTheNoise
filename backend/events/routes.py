"""The live stream of a workspace: its state, sent again each time it changes."""

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.accounts.deps import get_services, get_workspace
from backend.services import Services
from backend.workspace.state import Workspace

router = APIRouter(tags=["events"])

# A comment line this often keeps proxies from closing a quiet stream.
HEARTBEAT_SECONDS = 15.0


def _event(payload: str) -> str:
    return f"event: workspace\ndata: {payload}\n\n"


@router.get("/events")
async def events(
    workspace: Annotated[Workspace, Depends(get_workspace)],
    services: Annotated[Services, Depends(get_services)],
) -> StreamingResponse:
    async def stream() -> AsyncIterator[str]:
        subscriber = services.hub.subscribe(workspace.id)
        try:
            # In a thread: the workspace's lock can be held by a job for a moment.
            info = await asyncio.to_thread(services.describe, workspace)
            yield _event(info.model_dump_json())
            while True:
                try:
                    await asyncio.wait_for(subscriber.event.wait(), HEARTBEAT_SECONDS)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                subscriber.event.clear()
                if subscriber.latest is not None:
                    yield _event(subscriber.latest)
        finally:
            services.hub.unsubscribe(workspace.id, subscriber)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

"""A workspace seen by its owner: its state, its settings, emptying it, changing its key."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.accounts.deps import get_services, get_workspace
from backend.accounts.schema import KeyRotated
from backend.services import Services
from backend.workspace.schema import SettingsPatch, WorkspaceInfo
from backend.workspace.state import Workspace

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("")
def workspace_info(
    workspace: Annotated[Workspace, Depends(get_workspace)],
    services: Annotated[Services, Depends(get_services)],
) -> WorkspaceInfo:
    return services.describe(workspace)


@router.patch("/settings")
def change_settings(
    body: SettingsPatch,
    workspace: Annotated[Workspace, Depends(get_workspace)],
    services: Annotated[Services, Depends(get_services)],
) -> WorkspaceInfo:
    with workspace.lock:
        changes = body.model_dump(exclude_none=True)
        workspace.settings = workspace.settings.model_copy(update=changes)
        services.accounts.save_settings(workspace.id, workspace.settings)
    # A shorter refresh interval can make a refresh due at once.
    services.changed(workspace)
    return services.describe(workspace)


@router.delete("/items")
def empty_workspace(
    workspace: Annotated[Workspace, Depends(get_workspace)],
    services: Annotated[Services, Depends(get_services)],
) -> WorkspaceInfo:
    workspace.clear()
    # The files now hold nothing from another embedding model: the current one applies.
    workspace.embedding_key = services.embedder.key
    with workspace.db_lock, workspace.db:
        workspace.db.execute(
            "INSERT OR REPLACE INTO meta VALUES ('embedding_key', ?)", (workspace.embedding_key,)
        )
    services.changed(workspace)
    return services.describe(workspace)


@router.post("/key")
def new_key(
    workspace: Annotated[Workspace, Depends(get_workspace)],
    services: Annotated[Services, Depends(get_services)],
) -> KeyRotated:
    return KeyRotated(api_key=services.accounts.rotate_key(workspace.id))

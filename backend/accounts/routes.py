"""Getting a workspace: one call, no account."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.accounts.deps import get_services
from backend.accounts.limits import CREATIONS_PER_DAY, LIMITS
from backend.accounts.schema import PublicConfig, WorkspaceCreated
from backend.analyze.rate_limit import RateLimiter, client_address
from backend.probes.schema import POSSIBLE_SCORE, PROBABLE_SCORE
from backend.services import Services

router = APIRouter(tags=["accounts"])


def limit_creations(request: Request) -> None:
    limiter: RateLimiter = request.app.state.creation_limiter
    if not limiter.allow(client_address(request)):
        raise HTTPException(
            status_code=429,
            detail=f"Too many workspaces created from this address: {CREATIONS_PER_DAY} a day "
            "at most. Use the key you already have.",
        )


@router.get("/config")
def public_config(services: Annotated[Services, Depends(get_services)]) -> PublicConfig:
    return PublicConfig(
        limits=LIMITS,
        llm=services.chat is not None,
        possible_score=POSSIBLE_SCORE,
        probable_score=PROBABLE_SCORE,
    )


@router.post("/workspaces", dependencies=[Depends(limit_creations)])
def create_workspace(services: Annotated[Services, Depends(get_services)]) -> WorkspaceCreated:
    account, key = services.accounts.create()
    workspace = services.workspaces.of(account)
    return WorkspaceCreated(api_key=key, workspace=services.describe(workspace))

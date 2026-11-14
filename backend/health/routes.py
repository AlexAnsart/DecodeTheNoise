"""Health route: proves which commit and which build are live."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.map.store import MapBuild
from backend.settings import get_settings

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    commit: str
    build: str | None
    points: int


@router.get("/health")
def health(request: Request) -> Health:
    build: MapBuild | None = request.app.state.build
    return Health(
        status="ok",
        commit=get_settings().git_commit,
        build=build.manifest.build if build else None,
        points=build.manifest.n if build else 0,
    )

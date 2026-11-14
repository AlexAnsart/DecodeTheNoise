"""Request dependency: the build loaded at start-up, or 503 while there is none."""

from fastapi import HTTPException, Request

from backend.map.store import MapBuild


def get_build(request: Request) -> MapBuild:
    build: MapBuild | None = request.app.state.build
    if build is None:
        raise HTTPException(status_code=503, detail="No map build is loaded on this server yet.")
    return build

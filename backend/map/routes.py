"""The map itself: a JSON manifest and one binary file of typed arrays."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from backend.map.deps import get_build
from backend.map.schema import MapManifest
from backend.map.store import MapBuild

router = APIRouter(prefix="/api/map", tags=["map"])


@router.get("")
def manifest(build: Annotated[MapBuild, Depends(get_build)]) -> MapManifest:
    return build.manifest


@router.get("/buffers")
def buffers(build: Annotated[MapBuild, Depends(get_build)]) -> FileResponse:
    # The front end adds the build name to the URL, so a URL never changes content.
    return FileResponse(
        build.buffers_path,
        media_type="application/octet-stream",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )

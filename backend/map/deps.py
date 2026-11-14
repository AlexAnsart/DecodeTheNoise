"""Request dependencies of the map routes: which map is asked for, and the probes read on it."""

from fastapi import HTTPException, Request

from backend.map.store import MapBuild
from backend.probes.pack import Probes
from backend.workspace.snapshot import build_of


def get_build(request: Request) -> MapBuild:
    """The caller's workspace when the route was reached with a key; the demo build otherwise,
    or 503 while there is none."""
    workspace = getattr(request.state, "workspace", None)
    if workspace is not None:
        return build_of(workspace)
    build: MapBuild | None = request.app.state.build
    if build is None:
        raise HTTPException(status_code=503, detail="No map build is loaded on this server yet.")
    return build


def get_probes(request: Request) -> Probes:
    probes: Probes = request.app.state.probes
    return probes

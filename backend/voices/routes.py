"""The one-voice check, asked for a selection of the map: the demo's or a workspace's."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.map.deps import get_build
from backend.map.store import MapBuild
from backend.voices.calibration import Calibration, load_calibration
from backend.voices.reading import read_selection
from backend.voices.schema import VoicesAnswer, VoicesRequest

router = APIRouter(tags=["voices"])


@lru_cache(maxsize=4)
def calibration_at(reports_dir: Path) -> Calibration | None:
    """The report is read once per reports folder: it changes with a deploy, not while serving."""
    return load_calibration(reports_dir)


def get_calibration(request: Request) -> Calibration | None:
    reports_dir: Path = request.app.state.reports_dir
    return calibration_at(reports_dir)


@router.post("/voices")
def voices(
    body: VoicesRequest,
    build: Annotated[MapBuild, Depends(get_build)],
    calibration: Annotated[Calibration | None, Depends(get_calibration)],
) -> VoicesAnswer:
    """Do the actors of these points speak with one voice? A level with its evidence and the
    measured reliability, or `not enough evidence`."""
    n = build.manifest.n
    if any(i < 0 or i >= n for i in body.indices):
        raise HTTPException(status_code=422, detail="indices: a point index is outside the map.")
    return read_selection(build, calibration, body.indices)

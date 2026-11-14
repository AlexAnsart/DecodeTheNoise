"""The swarm layer. It is served only with its evaluation report: no verdict without its
measured reliability."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.metrics.schema import DetectorMetrics
from backend.swarms.schema import DETECTOR, SWARMS_FILE, Swarm, SwarmFile, SwarmLayer, SwarmSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/swarms", tags=["swarms"])


def load_swarms(build_folder: Path) -> SwarmFile | None:
    """The swarms of a build, or None when the build was packed without that layer."""
    path = build_folder / SWARMS_FILE
    if not path.is_file():
        return None
    swarms = SwarmFile.model_validate_json(path.read_text(encoding="utf-8"))
    logger.info("loaded %d swarms, %d flagged actors", len(swarms.swarms), len(swarms.actors))
    return swarms


def get_layer(request: Request) -> tuple[SwarmFile, DetectorMetrics]:
    swarms: SwarmFile | None = request.app.state.swarms
    reliability: DetectorMetrics | None = request.app.state.metrics.get(DETECTOR)
    if swarms is None or reliability is None:
        raise HTTPException(status_code=404, detail="This map has no measured swarm layer.")
    return swarms, reliability


Layer = Annotated[tuple[SwarmFile, DetectorMetrics], Depends(get_layer)]


@router.get("")
def layer(found: Layer) -> SwarmLayer:
    swarms, reliability = found
    summaries = [SwarmSummary.model_validate(s, from_attributes=True) for s in swarms.swarms]
    return SwarmLayer(
        detector=swarms.detector,
        window_seconds=swarms.window_seconds,
        min_events=swarms.min_events,
        swarms=summaries,
        actors=swarms.actors,
        reliability=reliability,
    )


@router.get("/{swarm_id}")
def one(swarm_id: int, found: Layer) -> Swarm:
    swarms, _ = found
    for swarm in swarms.swarms:
        if swarm.id == swarm_id:
            return swarm
    raise HTTPException(status_code=404, detail="No swarm has this number.")

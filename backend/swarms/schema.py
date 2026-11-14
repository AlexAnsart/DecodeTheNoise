"""Swarms: sets of actors whose posting is coordinated beyond what chance explains.

`SwarmFile` is the contract of `swarms.json` in a map build, written by `pipelines.swarms`.
Actor identifiers are hashed before they reach that file.
"""

from typing import Literal

from pydantic import BaseModel

from backend.metrics.schema import DetectorMetrics

SWARMS_FILE = "swarms.json"
# Name of the detector in `reports/<detector>/metrics.json`.
DETECTOR = "swarms"

Confidence = Literal["probable", "possible"]


class SwarmActor(BaseModel):
    actor_id: str
    n_events: int
    n_partners: int


class SwarmEvent(BaseModel):
    """One piece of evidence: the same text posted by several actors inside the window."""

    at: int  # milliseconds since the epoch
    text: str
    actor_ids: list[str]
    spread_seconds: int


class SwarmWeek(BaseModel):
    start: int
    events: int


class SwarmSummary(BaseModel):
    id: int
    name: str
    confidence: Confidence
    n_actors: int
    n_events: int
    first_at: int
    last_at: int


class Swarm(SwarmSummary):
    """A swarm with its evidence: its most active actors and its most telling events."""

    actors: list[SwarmActor]
    events: list[SwarmEvent]
    weeks: list[SwarmWeek]


class ActorVerdict(BaseModel):
    swarm: int
    confidence: Confidence
    n_events: int
    n_partners: int


class SwarmFile(BaseModel):
    detector: str
    window_seconds: int
    min_events: int
    report: str
    swarms: list[Swarm]
    actors: dict[str, ActorVerdict]


class SwarmLayer(BaseModel):
    """What the map needs to show the layer: every swarm in short, the verdict of every
    flagged actor, and how reliable the detector measured to be."""

    detector: str
    window_seconds: int
    min_events: int
    swarms: list[SwarmSummary]
    actors: dict[str, ActorVerdict]
    reliability: DetectorMetrics

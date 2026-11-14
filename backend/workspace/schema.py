"""A workspace as the API shows it: its counts, its limits, its settings.

A workspace is the private map of one user: it starts empty and grows with every item sent.
"""

from typing import Literal

from pydantic import BaseModel, Field

from backend.probes.schema import PROBABLE_SCORE, ProbeInfo

# Which flagged items go to the LLM review: none, those a probe finds probable, those a probe
# finds possible or probable, or those at or above a score of your own.
ReviewMode = Literal["off", "probable", "possible", "score"]

MIN_REFRESH_EVERY = 50
MAX_REFRESH_EVERY = 2_000


class Limits(BaseModel):
    items: int
    batch_items: int
    requests_per_minute: int
    reviews_per_day: int
    text_chars: int


class Usage(BaseModel):
    reviews_today: int
    names_today: int


class RefreshState(BaseModel):
    """The layout, the zones and their names are computed again as the workspace grows."""

    # How many times they were computed.
    epoch: int
    # Points the last computation covered; the ones added since sit beside their neighbours.
    points_covered: int
    next_at: int | None
    running: bool


class IngestState(BaseModel):
    """Where the embedding of what was sent stands, so that a batch never looks stuck."""

    # Posts of the batch being embedded; 0 when nothing waits. Of them, `pending` still wait.
    batch: int
    # Posts of other workspaces that are embedded before this one is finished: the server
    # takes turns between the workspaces that wait.
    ahead: int
    # Posts a second the embedding model was measured at on this server; null until measured.
    rate: float | None
    # Estimated seconds until nothing waits: what is ahead, at the measured rate.
    eta_seconds: int | None
    # Why the embedding is not advancing, when it is not. The server tries again by itself.
    error: str | None


class WorkspaceSettings(BaseModel):
    review_mode: ReviewMode = "probable"
    review_min_score: float = Field(default=PROBABLE_SCORE, ge=0.0, le=1.0)
    refresh_every: int = Field(default=100, ge=MIN_REFRESH_EVERY, le=MAX_REFRESH_EVERY)


class SettingsPatch(BaseModel):
    review_mode: ReviewMode | None = None
    review_min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    refresh_every: int | None = Field(default=None, ge=MIN_REFRESH_EVERY, le=MAX_REFRESH_EVERY)


class WorkspaceInfo(BaseModel):
    id: str
    created_at: str
    # Changes whenever the map does: a new point, a new layout, a zone named, a review done.
    version: int
    items: int
    points: int
    pending: int
    actors: int
    zones: int
    limits: Limits
    usage: Usage
    ingest: IngestState
    refresh: RefreshState
    settings: WorkspaceSettings
    # Probes shown in the interface, with what each level measured.
    probes: list[ProbeInfo]
    embedding_key: str

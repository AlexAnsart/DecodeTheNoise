"""The one-voice check of a selection: what is asked and what is answered."""

from typing import Literal

from pydantic import BaseModel, Field

MAX_SELECTION = 5000

Outcome = Literal["one voice", "separate voices", "not enough evidence"]


class VoicesRequest(BaseModel):
    indices: list[int] = Field(min_length=1, max_length=MAX_SELECTION)


class Selection(BaseModel):
    """What the check could read: reposts and items without an actor are left out."""

    items: int
    actors: int


class GroupSize(BaseModel):
    actors: int
    posts_each: int


class Read(BaseModel):
    """The size the check ran at, and how many actors had enough posts to be drawn."""

    actors: int
    posts_each: int
    eligible_actors: int
    draws: int


class Authorship(BaseModel):
    """How often a post is given back to its own actor, and what chance gives."""

    found: float
    chance: float


class ReferenceRanges(BaseModel):
    """Where 90% of the measured groups score, at the size read."""

    independent: tuple[float, float]
    one_brief: tuple[float, float]


class Reliability(BaseModel):
    """Counts on held-out groups, from the evaluation report named by `report`."""

    false_alarms: int
    real_groups: int
    hard_false_alarms: int
    hard_real_groups: int
    caught: int
    one_brief_groups: int
    report: str


class PairSide(BaseModel):
    index: int
    actor: str  # a label for this answer ("Actor A"), never the identifier
    text: str


class Pair(BaseModel):
    """Two posts by different actors that say nearly the same thing."""

    similarity: float
    a: PairSide
    b: PairSide


class VoicesAnswer(BaseModel):
    outcome: Outcome
    # A flag is a level, never a fact: "possible" when the outcome is "one voice".
    confidence: Literal["possible"] | None = None
    reason: str | None = None
    selection: Selection
    needed: GroupSize
    read: Read | None = None
    score: float | None = None
    threshold: float | None = None
    authorship: Authorship | None = None
    reference: ReferenceRanges | None = None
    reliability: Reliability | None = None
    pairs: list[Pair] = []
    caveats: list[str] = []

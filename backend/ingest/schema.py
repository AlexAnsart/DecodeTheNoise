"""The public contract: what a client sends to store a post, and what it gets back.

The answer has two parts. `item` is read from the post alone (the probes, the review).
`context` is read from the rest of the workspace (where it lands, what resembles it, who
writes alike). Counts in `context` are measures, never a verdict on coordination.
"""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from backend.probes.schema import ProbeReading
from backend.review.schema import Review

MAX_ID_CHARS = 200
MAX_TEXT_CHARS = 20_000
MAX_URLS = 20
MAX_URL_CHARS = 2_048
MAX_META_KEYS = 16
MAX_META_VALUE_CHARS = 500
MAX_BATCH_ITEMS = 1_000
DEFAULT_NEIGHBOURS = 10
MAX_NEIGHBOURS = 20
EXCERPT_CHARS = 280
# Items at or above this cosine are counted as saying the same thing. A count, not a verdict.
SAME_STATEMENT_SIMILARITY = 0.9
SIMILAR_ACTORS = 5
# An actor under this many items has no stable mean: it is not compared to the others.
MIN_ACTOR_ITEMS = 3

Kind = Literal["original", "reply", "repost", "quote"]
Outcome = Literal["placed", "queued", "not enough evidence"]
MetaValue = str | int | float | bool | None


class ItemIn(BaseModel):
    """One post. Only `id` and `text` are required; every other field adds context."""

    model_config = ConfigDict(extra="forbid")

    # Your own identifier. Sending the same id again updates the item.
    id: str = Field(min_length=1, max_length=MAX_ID_CHARS)
    text: str = Field(max_length=MAX_TEXT_CHARS)
    # When the post was published, with its UTC offset. Absent: the item is undated.
    created_at: AwareDatetime | None = None
    actor_id: str | None = Field(default=None, min_length=1, max_length=MAX_ID_CHARS)
    actor_name: str | None = Field(default=None, max_length=MAX_ID_CHARS)
    kind: Kind | None = None
    # The item this one answers, reposts or quotes, and who wrote it.
    parent_id: str | None = Field(default=None, max_length=MAX_ID_CHARS)
    parent_actor_id: str | None = Field(default=None, max_length=MAX_ID_CHARS)
    urls: list[str] = Field(default_factory=list, max_length=MAX_URLS)
    lang: str | None = Field(default=None, max_length=35)
    # Where the post comes from: a platform, a feed, a campaign of yours.
    source: str | None = Field(default=None, max_length=80)
    meta: dict[str, MetaValue] = Field(default_factory=dict, max_length=MAX_META_KEYS)


class BatchIn(BaseModel):
    """Items are checked one by one: a malformed item is rejected alone, with its reason."""

    items: list[dict[str, object]] = Field(min_length=1, max_length=MAX_BATCH_ITEMS)


class ZoneRef(BaseModel):
    id: int
    name: str
    # False while the name is only the zone's distinctive words.
    named: bool
    words: list[str]
    # Share of the workspace's points in this zone.
    share: float


class NeighbourOut(BaseModel):
    id: str
    index: int
    actor_id: str | None
    created_at: AwareDatetime | None
    similarity: float
    # Share of character 5-grams the two texts have in common (Jaccard), links and mentions
    # left out. High similarity with a high overlap is a copy; with a low one, a rewording.
    word_overlap: float
    excerpt: str


class SameStatement(BaseModel):
    """Other items at or above `min_similarity`, and the distinct other actors behind them."""

    min_similarity: float
    items: int
    actors: int
    first: AwareDatetime | None
    last: AwareDatetime | None


class SimilarActor(BaseModel):
    id: str
    similarity: float
    items: int


class ActorContext(BaseModel):
    id: str
    items: int
    first_seen: AwareDatetime | None
    last_seen: AwareDatetime | None
    # Actors whose items mean the same on average. Empty, with `reason`, under the minimum.
    similar_actors: list[SimilarActor]
    reason: str | None


class ItemReading(BaseModel):
    """Read from the item alone."""

    lang: str | None
    # The probes that flagged the item, strongest first.
    probes: list[ProbeReading]
    # One score per probe, flagged or not: 0.5 is where `possible` starts, 0.8 `probable`.
    scores: dict[str, float]
    review: Review


class ItemContext(BaseModel):
    """Read from the rest of the workspace, as it is when the answer is written."""

    position: tuple[float, float, float]
    zone: ZoneRef | None
    neighbours: list[NeighbourOut]
    same_statement: SameStatement
    actor: ActorContext | None


class Counts(BaseModel):
    items: int
    # Items placed on the map. The others wait to be embedded or are too short.
    points: int
    pending: int
    limit: int
    # Number of points at which the layout, the zones and their names are computed again.
    next_refresh_at: int | None


class ItemResult(BaseModel):
    id: str
    stored: bool
    outcome: Outcome
    # Why the item is not placed. Null when it is.
    reason: str | None
    # The point of the map this item is. Null while it is not placed.
    index: int | None
    embedding_key: str
    item: ItemReading | None
    context: ItemContext | None
    # The embedding of the item (a unit vector under `embedding_key`), when asked for with
    # `?vector=true`: what its position, its neighbours and the probes are all read from.
    vector: list[float] | None = None
    workspace: Counts


class Rejected(BaseModel):
    id: str | None
    reason: str


class BatchAccepted(BaseModel):
    """Batches are embedded in the background. `GET /items/{id}` gives each item's answer."""

    accepted: int
    updated: int
    unchanged: int
    rejected: list[Rejected]
    workspace: Counts

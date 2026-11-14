"""What the paste box sends and gets back. The front end reads these names."""

from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_TEXT_CHARS = 20_000
MAX_URL_CHARS = 2_048
# Under this length a text says too little to be placed: the answer is an abstention.
MIN_TEXT_CHARS = 20
# What is embedded. The map is made of short posts, so a long text is read by its beginning:
# enough for any post in full, and for the title and lead of an article.
EMBED_BUDGET_CHARS = 1_200
MAX_RETURNED_CHARS = 2_000
NEIGHBOURS = 10

Outcome = Literal["placed", "not enough evidence"]


class AnalyzeRequest(BaseModel):
    text: str | None = Field(default=None, max_length=MAX_TEXT_CHARS)
    url: str | None = Field(default=None, max_length=MAX_URL_CHARS)

    @field_validator("url")
    @classmethod
    def _web_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        address = value.strip()
        parts = urlsplit(address)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ValueError("must be an http or https address")
        return address

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        if (self.text is None) == (self.url is None):
            raise ValueError("text, url: exactly one of the two must be set")
        return self


class Source(BaseModel):
    kind: Literal["text", "url"]
    url: str | None
    title: str | None
    # When the page was fetched from its site (UTC, ISO 8601). Null for a pasted text.
    read_at: str | None


class Neighbour(BaseModel):
    index: int
    score: float


class AnalyzeResponse(BaseModel):
    outcome: Outcome
    # Why nothing was placed. Null when the text was placed.
    reason: str | None
    source: Source
    # The text that was embedded, cut to MAX_RETURNED_CHARS.
    text: str
    # Length of the whole text read, of which `text` is the beginning.
    characters: int
    position3: tuple[float, float, float] | None
    position2: tuple[float, float] | None
    # The nearest points of the map by cosine, nearest first.
    neighbours: list[Neighbour]
    # Empty until a detector has an evaluation report: the verdict schema of the
    # specification (section 6) will type it.
    verdicts: list[dict[str, object]]

"""The LLM review of a flagged item: what it read, with the quote that backs each reading.

A probe flags; the review reads the item again with more context (its nearest items, the other
items of its actor). Until the review pass has its own evaluation report, `measured` is false
and the interface says so beside every finding.
"""

from typing import Literal

from pydantic import BaseModel

ReviewStatus = Literal["none", "queued", "done", "skipped", "failed"]
ReviewReading = Literal["supported", "not supported", "unclear"]


class Finding(BaseModel):
    """What the review says about one probe that flagged the item."""

    probe: str
    reading: ReviewReading
    explanation: str
    # A span copied from the item's text. A quote that is not in the text is dropped, and the
    # reading becomes `unclear`.
    quote: str | None


class Review(BaseModel):
    status: ReviewStatus
    # Why the review was skipped or failed.
    reason: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    findings: list[Finding] = []
    measured: bool = False


NO_REVIEW = Review(status="none")

"""The LLM review: what it reads in a flagged item or in a selection of items, with the span
of text that backs each reading.

A probe flags; the review reads again, with the annotation guide of each label and more
context (the nearest items, the other items of the actor). It answers the probes that flagged
the item, and it names the manipulation techniques the text uses, each with its quote. It
describes what a text does, never who is behind it or why.

Until the review has its own evaluation report (`reports/review/metrics.json`), `measured` is
false and the interface says so beside every reading.
"""

from typing import Literal

from pydantic import BaseModel

ReviewStatus = Literal["none", "queued", "done", "skipped", "failed"]
ReviewReading = Literal["supported", "not supported", "unclear"]
# Whose voice the text is in: the author's own, words reported or quoted, irony.
Voice = Literal["own", "reported", "ironic", "unclear"]


class ReviewMeasure(BaseModel):
    """How the review agreed with the annotation on held-out posts: for one label, or for
    every measurable technique taken together."""

    precision: float
    precision_low: float
    precision_high: float
    recall: float | None
    # Posts of the evaluation the review marked with this label (or with any technique).
    read: int
    # Folder under `reports/` that holds the evaluation.
    report: str


class Finding(BaseModel):
    """What the review says about one probe that flagged the item."""

    probe: str
    label: str = ""
    reading: ReviewReading
    explanation: str
    # A span copied from the text of the item. A quote that is not in the text is dropped,
    # and the reading becomes `unclear`.
    quote: str | None
    reliability: ReviewMeasure | None = None


class Technique(BaseModel):
    """A manipulation technique the review found in the text: named, explained, quoted."""

    key: str
    name: str
    explanation: str
    quote: str
    reliability: ReviewMeasure | None = None


class Review(BaseModel):
    status: ReviewStatus
    # Why the review was skipped or failed.
    reason: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    findings: list[Finding] = []
    # The techniques found, whether a probe flagged them or not.
    techniques: list[Technique] = []
    voice: Voice | None = None
    # What the text asks its reader to do, and whom it is aimed at: spans of the text, or null.
    asks: str | None = None
    target: str | None = None
    measured: bool = False
    # The technique screen over every measurable technique together. It stands in for a
    # technique marked too rarely in the evaluation to have a figure of its own.
    overall: ReviewMeasure | None = None


NO_REVIEW = Review(status="none")


class ProbeRate(BaseModel):
    """How often a probe flags the items of a selection, against the rest of the map.
    Measured by the probes alone: no LLM is involved."""

    key: str
    label: str
    flagged: int
    rate: float
    elsewhere: float
    # rate / elsewhere; null when the probe flags nothing elsewhere.
    lift: float | None


class QuotedPost(BaseModel):
    # The point of the map the quote comes from.
    index: int
    quote: str


class TechniqueInGroup(BaseModel):
    key: str
    name: str
    explanation: str
    # Posts of the selection that show it, each with its span.
    examples: list[QuotedPost]


class SelectionReview(BaseModel):
    """The review of a group of items (a lasso selection, a zone, a suspected swarm): what the
    probes measure on it, then what the LLM reads in a sample of its posts."""

    status: ReviewStatus
    reason: str | None = None
    posts: int
    actors: int
    rates: list[ProbeRate]
    # The points whose text the LLM read: a sample when the selection is large.
    read: list[int] = []
    # What the posts read have in common, in one or two sentences.
    statement: str | None = None
    techniques: list[TechniqueInGroup] = []
    asks: str | None = None
    targets: list[str] = []
    model: str | None = None
    prompt_version: str | None = None
    measured: bool = False

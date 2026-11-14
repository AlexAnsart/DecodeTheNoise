"""Reads a flagged item again with an LLM, and keeps only what the text of the item backs.

The answer is parsed into typed models. A quote must be a span of the item: one that is not
there is dropped, and its reading with it. An answer that cannot be parsed gives a failed
review, never a guess.
"""

import json
import logging
import re
from typing import Protocol

from pydantic import BaseModel, ValidationError

from backend.review.prompt import PROMPT_VERSION, SYSTEM, ReviewRequest, build_prompt, cache_key
from backend.review.schema import NO_REVIEW, Finding, Review, ReviewReading

__all__ = ["PROMPT_VERSION", "Completer", "ReviewRequest", "cache_key", "review_item"]

logger = logging.getLogger(__name__)

MAX_EXPLANATION_CHARS = 400
UNREAD = "The review gave no reading for this probe."
UNBACKED = "The review quoted words that are not in the item, so its reading is not kept."
UNREADABLE = "The answer of the review could not be read."
# Room for the JSON answer: a fixed part, then one finding per probe.
_BASE_TOKENS = 300
_TOKENS_PER_PROBE = 250


class Completer(Protocol):
    def complete(self, system: str, user: str, max_tokens: int = 400) -> str: ...


class _Answer(BaseModel):
    # Each finding is checked on its own: a malformed one does not cost the others.
    findings: list[dict[str, object]]


class _RawFinding(BaseModel):
    probe: str
    reading: ReviewReading
    explanation: str
    quote: str | None = None


def quoted_span(text: str, quote: str) -> str | None:
    """The span of `text` the quote copies, as the text writes it. Whitespace may differ."""
    words = quote.split()
    if not words:
        return None
    found = re.search(r"\s+".join(re.escape(word) for word in words), text)
    return found.group(0) if found else None


def _checked(raw: _RawFinding, text: str) -> Finding:
    explanation = " ".join(raw.explanation.split())[:MAX_EXPLANATION_CHARS]
    if raw.quote is None or not raw.quote.strip():
        return Finding(probe=raw.probe, reading=raw.reading, explanation=explanation, quote=None)
    span = quoted_span(text, raw.quote)
    if span is None:
        return Finding(probe=raw.probe, reading="unclear", explanation=UNBACKED, quote=None)
    return Finding(probe=raw.probe, reading=raw.reading, explanation=explanation, quote=span)


def parse_findings(raw: str, request: ReviewRequest) -> list[Finding] | None:
    """One finding per probe asked, in their order. None when the answer holds none of them."""
    try:
        answer = _Answer.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError):
        return None
    asked = {info.key for info in request.probes}
    by_probe: dict[str, Finding] = {}
    for entry in answer.findings:
        try:
            finding = _RawFinding.model_validate(entry)
        except ValidationError:
            continue
        # A probe nobody asked about is not reported, and the first answer for a probe stands.
        if finding.probe in asked and finding.probe not in by_probe:
            by_probe[finding.probe] = _checked(finding, request.text)
    if not by_probe:
        return None
    return [
        by_probe.get(info.key)
        or Finding(probe=info.key, reading="unclear", explanation=UNREAD, quote=None)
        for info in request.probes
    ]


def review_item(client: Completer, model: str, request: ReviewRequest) -> Review:
    """One LLM call. A network failure (`httpx.HTTPError`) is left to the caller."""
    if not request.probes:
        return NO_REVIEW
    budget = _BASE_TOKENS + _TOKENS_PER_PROBE * len(request.probes)
    raw = client.complete(SYSTEM, build_prompt(request), max_tokens=budget)
    findings = parse_findings(raw, request)
    if findings is None:
        logger.warning("review answer not readable (%s, %s)", model, PROMPT_VERSION)
        return Review(
            status="failed", reason=UNREADABLE, model=model, prompt_version=PROMPT_VERSION
        )
    return Review(
        status="done",
        model=model,
        prompt_version=PROMPT_VERSION,
        findings=findings,
        measured=False,
    )

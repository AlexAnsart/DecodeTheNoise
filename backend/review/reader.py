"""Reads an item again with an LLM, and keeps only what the text of the item backs.

The answer is parsed into typed models. Every quote, and what the item asks and whom it is
aimed at, must be a span of the item: one that is not there is dropped, and the reading it
backed with it. An answer that cannot be parsed gives a failed review, never a guess.
"""

import json
import logging
import re
from typing import Protocol, get_args

from pydantic import BaseModel, ValidationError

from backend.probes.schema import ProbeInfo
from backend.review.guides import NO_GUIDES, Guides
from backend.review.prompt import (
    MAX_PROBES,
    PROMPT_VERSION,
    ReviewRequest,
    build_prompt,
    cache_key,
    system_prompt,
)
from backend.review.schema import NO_REVIEW, Finding, Review, ReviewReading, Technique, Voice

__all__ = ["PROMPT_VERSION", "Completer", "ReviewRequest", "cache_key", "review_item"]

logger = logging.getLogger(__name__)

MAX_EXPLANATION_CHARS = 400
UNREAD = "The review gave no reading for this probe."
UNBACKED = "The review quoted words that are not in the item, so its reading is not kept."
UNQUOTED = "The review gave no span of the item for this reading, so it is not kept."
UNREADABLE = "The answer of the review could not be read."
# Room for the JSON answer: the voice, the techniques found and the aim, then one finding per
# probe. Set on real answers (docs/review.md): the longest seen stayed under half of it.
BASE_TOKENS = 1_200
TOKENS_PER_PROBE = 200


class Completer(Protocol):
    def complete(self, system: str, user: str, max_tokens: int = 400) -> str: ...


class _Answer(BaseModel):
    # Each entry is checked on its own: a malformed one does not cost the others.
    findings: list[object]
    techniques: list[object] = []
    voice: object = None
    asks: object = None
    target: object = None


class _RawFinding(BaseModel):
    probe: str
    reading: ReviewReading
    explanation: str
    quote: str | None = None


class _RawTechnique(BaseModel):
    key: str
    explanation: str
    quote: str


def quoted_span(text: str, quote: object) -> str | None:
    """The span of `text` the quote copies, as the text writes it. Whitespace may differ."""
    words = quote.split() if isinstance(quote, str) else []
    if not words:
        return None
    found = re.search(r"\s+".join(re.escape(word) for word in words), text)
    return found.group(0) if found else None


def plain(explanation: str) -> str:
    return " ".join(explanation.split())[:MAX_EXPLANATION_CHARS]


def _finding(raw: _RawFinding, info: ProbeInfo, text: str, guides: Guides) -> Finding:
    span = quoted_span(text, raw.quote)
    label = guides.label(raw.probe)
    reading, explanation = raw.reading, plain(raw.explanation)
    if raw.quote and raw.quote.strip() and span is None:
        reading, explanation = "unclear", UNBACKED
    elif reading == "supported" and span is None and label is not None and label.evidence:
        # The guide of this label throws away a `yes` that comes without its span.
        reading, explanation = "unclear", UNQUOTED
    return Finding(
        probe=raw.probe, label=info.label, reading=reading, explanation=explanation, quote=span
    )


def _findings(entries: list[object], request: ReviewRequest, guides: Guides) -> list[Finding]:
    """One finding per probe asked, in their order. A probe nobody asked about is not reported,
    and the first answer for a probe stands."""
    asked = {info.key: info for info in request.probes[:MAX_PROBES]}
    found: dict[str, Finding] = {}
    for entry in entries:
        try:
            raw = _RawFinding.model_validate(entry)
        except ValidationError:
            continue
        if raw.probe in asked and raw.probe not in found:
            found[raw.probe] = _finding(raw, asked[raw.probe], request.text, guides)
    if asked and not found:
        return []
    return [
        found.get(key)
        or Finding(probe=key, label=info.label, reading="unclear", explanation=UNREAD, quote=None)
        for key, info in asked.items()
    ]


def _techniques(
    entries: list[object], findings: list[Finding], text: str, guides: Guides
) -> list[Technique]:
    """The screened techniques whose span is in the item, in guide order. A technique a flagged
    probe asked about follows the finding of that probe: the two never disagree."""
    screened = {label.key: label for label in guides.screened()}
    found: dict[str, Technique] = {}
    for entry in entries:
        try:
            raw = _RawTechnique.model_validate(entry)
        except ValidationError:
            continue
        span = quoted_span(text, raw.quote)
        if raw.key in screened and raw.key not in found and span is not None:
            name = screened[raw.key].name
            found[raw.key] = Technique(
                key=raw.key, name=name, explanation=plain(raw.explanation), quote=span
            )
    for finding in findings:
        if finding.probe not in screened:
            continue
        if finding.reading != "supported" or finding.quote is None:
            found.pop(finding.probe, None)
        elif finding.probe not in found:
            found[finding.probe] = Technique(
                key=finding.probe,
                name=screened[finding.probe].name,
                explanation=finding.explanation,
                quote=finding.quote,
            )
    return [found[key] for key in screened if key in found]


def parse_review(raw: str, model: str, request: ReviewRequest, guides: Guides) -> Review | None:
    """The review the answer holds. None when it is not the JSON object asked for, or when it
    answers none of the probes asked."""
    try:
        answer = _Answer.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError):
        return None
    findings = _findings(answer.findings, request, guides)
    if request.probes and not findings:
        return None
    return Review(
        status="done",
        model=model,
        prompt_version=PROMPT_VERSION,
        findings=findings,
        techniques=_techniques(answer.techniques, findings, request.text, guides),
        voice=answer.voice if answer.voice in get_args(Voice) else None,
        asks=quoted_span(request.text, answer.asks),
        target=quoted_span(request.text, answer.target),
        measured=False,
    )


def review_item(
    client: Completer, model: str, request: ReviewRequest, guides: Guides = NO_GUIDES
) -> Review:
    """One LLM call. A network failure (`httpx.HTTPError`) is left to the caller. Without a
    probe and without technique guides there is nothing to ask: no call is made."""
    probes = request.probes[:MAX_PROBES]
    if not probes and not guides.screened():
        return NO_REVIEW
    budget = BASE_TOKENS + TOKENS_PER_PROBE * len(probes)
    raw = client.complete(system_prompt(guides), build_prompt(request, guides), max_tokens=budget)
    review = parse_review(raw, model, request, guides)
    if review is None:
        logger.warning("review answer not readable (%s, %s): %.200s", model, PROMPT_VERSION, raw)
        return Review(
            status="failed", reason=UNREADABLE, model=model, prompt_version=PROMPT_VERSION
        )
    return review

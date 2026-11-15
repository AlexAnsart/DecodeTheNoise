"""The review of a selection of items (a lasso selection, a zone, a suspected swarm): what the
probes measure on it, then what an LLM reads in a sample of its posts.

The measured part involves no LLM: how often each probe flags the selection, against the rest
of the map. The sample is drawn with no eye on a conclusion: the posts nearest to the mean
direction of the selection, a few per actor at most. Every span the LLM cites is checked
against the post it cites.
"""

import json
import logging

import numpy as np
from pydantic import BaseModel, Field, ValidationError

from backend.probes.scoring import Probes
from backend.review.guides import Guides
from backend.review.reader import Completer, plain, quoted_span
from backend.review.schema import ProbeRate, QuotedPost, TechniqueInGroup
from backend.review.selection_prompt import (
    MAX_POSTS,
    MAX_TARGETS,
    SELECTION_TOKENS,
    SelectionAsk,
    selection_prompt,
    selection_system,
)

logger = logging.getLogger(__name__)

MAX_INDICES = 5_000
# Posts of one actor in the sample: one prolific actor must not be the whole reading.
PER_ACTOR = 2
MAX_STATEMENT_CHARS = 500


class SelectionRequest(BaseModel):
    indices: list[int] = Field(min_length=1, max_length=MAX_INDICES)


class SelectionReading(BaseModel):
    """What the LLM read in the sample, after every span was checked."""

    statement: str
    techniques: list[TechniqueInGroup] = []
    asks: str | None = None
    targets: list[str] = []


class _Cited(BaseModel):
    post: int
    quote: str


class _GroupTechnique(BaseModel):
    key: str
    explanation: str
    examples: list[object] = []


class _Answer(BaseModel):
    statement: str
    techniques: list[object] = []
    asks: object = None
    targets: list[object] = []


def probe_rates(probes: Probes, scores: np.ndarray, chosen: np.ndarray) -> list[ProbeRate]:
    """For each shown probe: how many items of the selection it flags, and how that rate
    compares with the rest of the map. The most distinctive probes come first."""
    flags = probes.flags(scores)
    inside = flags[chosen].sum(axis=0)
    everywhere = flags.sum(axis=0)
    rest = len(scores) - len(chosen)
    rates = []
    for column, info in enumerate(probes.infos):
        if info.state != "shown":
            continue
        flagged = int(inside[column])
        rate = flagged / len(chosen)
        elsewhere = float(everywhere[column] - flagged) / rest if rest else 0.0
        rates.append(
            ProbeRate(
                key=info.key,
                label=info.label,
                flagged=flagged,
                rate=rate,
                elsewhere=elsewhere,
                lift=rate / elsewhere if elsewhere > 0 else None,
            )
        )
    # A probe that flags here and nowhere else has no lift to compute: it is the most distinctive.
    return sorted(
        rates,
        key=lambda r: (r.flagged == 0, -(r.lift if r.lift is not None else np.inf), -r.rate),
    )


def sample(vectors: np.ndarray, chosen: np.ndarray, actors: dict[int, str | None]) -> list[int]:
    """The points read by the LLM: the nearest to the mean direction of the selection, at most
    `PER_ACTOR` of one actor. An item without an actor counts for itself."""
    selected = vectors[chosen]
    centre = selected.mean(axis=0)
    order = np.argsort(-(selected @ centre), kind="stable")
    taken: dict[str, int] = {}
    read: list[int] = []
    for position in order.tolist():
        index = int(chosen[position])
        actor = actors.get(index)
        if actor and taken.get(actor, 0) >= PER_ACTOR:
            continue
        if actor:
            taken[actor] = taken.get(actor, 0) + 1
        read.append(index)
        if len(read) == MAX_POSTS:
            break
    return read


def _cited(entry: object, ask: SelectionAsk) -> QuotedPost | None:
    """The span as the cited post writes it, or None when the post does not hold it."""
    try:
        cited = _Cited.model_validate(entry)
    except ValidationError:
        return None
    if not 1 <= cited.post <= len(ask.posts):
        return None
    index, text = ask.posts[cited.post - 1]
    span = quoted_span(text, cited.quote)
    return QuotedPost(index=index, quote=span) if span is not None else None


def _techniques(entries: list[object], ask: SelectionAsk, guides: Guides) -> list[TechniqueInGroup]:
    """The screened techniques that several posts show, each example checked in its post."""
    screened = {label.key: label for label in guides.screened()}
    needed = min(2, len(ask.posts))
    found: dict[str, TechniqueInGroup] = {}
    for entry in entries:
        try:
            raw = _GroupTechnique.model_validate(entry)
        except ValidationError:
            continue
        examples: dict[int, QuotedPost] = {}
        for example in raw.examples:
            cited = _cited(example, ask)
            if cited is not None:
                examples.setdefault(cited.index, cited)
        if raw.key in screened and raw.key not in found and len(examples) >= needed:
            found[raw.key] = TechniqueInGroup(
                key=raw.key,
                name=screened[raw.key].name,
                explanation=plain(raw.explanation),
                examples=list(examples.values()),
            )
    return [found[key] for key in screened if key in found]


def parse_selection(raw: str, ask: SelectionAsk, guides: Guides) -> SelectionReading | None:
    """None when the answer is not the JSON object asked for."""
    try:
        answer = _Answer.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError):
        return None
    asks = _cited(answer.asks, ask)
    targets: dict[str, str] = {}
    for entry in answer.targets:
        cited = _cited(entry, ask)
        if cited is not None:
            targets.setdefault(cited.quote.lower(), cited.quote)
    return SelectionReading(
        statement=" ".join(answer.statement.split())[:MAX_STATEMENT_CHARS],
        techniques=_techniques(answer.techniques, ask, guides),
        asks=asks.quote if asks else None,
        targets=list(targets.values())[:MAX_TARGETS],
    )


def read_selection(
    client: Completer, model: str, ask: SelectionAsk, guides: Guides
) -> SelectionReading | None:
    """One LLM call. None when the answer cannot be read; a network failure is left to the
    caller."""
    raw = client.complete(
        selection_system(guides), selection_prompt(ask), max_tokens=SELECTION_TOKENS
    )
    reading = parse_selection(raw, ask, guides)
    if reading is None:
        logger.warning("selection answer not readable (%s): %.200s", model, raw)
    return reading

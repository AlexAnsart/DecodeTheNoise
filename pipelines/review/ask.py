"""Asks the review about posts, a few at a time, and pays for an answer once.

`review_item` is called as the product calls it. The answer of the model is kept as it came,
so a later run reads it again from the cache and counts without paying.
"""

import json
import logging
import threading
import time
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import httpx

from backend.review.guides import Guides
from backend.review.reader import Completer, ReviewRequest, cache_key, quoted_span, review_item
from backend.review.schema import Review
from pipelines.review.cache import Answers

log = logging.getLogger("review.ask")

WORKERS = 8
ATTEMPTS = 3
# Seconds before asking again after a failed call, times the number of failures so far.
PAUSE = 2.0


class BudgetSpent(Exception):
    """No call is left to make."""


class Budget:
    """The calls that may still be made, shared by the worker threads. A failed call counts."""

    def __init__(self, calls: int) -> None:
        self._left = calls
        self._lock = threading.Lock()

    def take(self) -> None:
        with self._lock:
            if self._left <= 0:
                raise BudgetSpent
            self._left -= 1


class _Replay:
    """Hands `review_item` the answer already kept, or asks the model and keeps what it says."""

    def __init__(self, client: Completer, budget: Budget, kept: str | None) -> None:
        self._client, self._budget = client, budget
        self.raw, self.fresh = kept, False

    def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        if self.raw is None:
            self._budget.take()
            self.raw, self.fresh = self._client.complete(system, user, max_tokens), True
        return self.raw


@dataclass(frozen=True)
class Reading:
    review: Review
    raw: str
    # Techniques the model reported with a quote that is not in the post: the reader drops them.
    rejected: tuple[str, ...]
    fresh: bool


def holds_json(raw: str) -> bool:
    """Whether an answer holds a JSON object once what surrounds its braces is dropped: an
    answer the reader could not read, and that a more tolerant reading would."""
    try:
        return isinstance(json.loads(raw[raw.find("{") : raw.rfind("}") + 1]), dict)
    except json.JSONDecodeError:
        return False


def rejected_techniques(raw: str, text: str, guides: Guides) -> tuple[str, ...]:
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError:
        return ()
    entries = answer.get("techniques") if isinstance(answer, dict) else None
    screened = {label.key for label in guides.screened()}
    return tuple(
        entry["key"]
        for entry in (entries if isinstance(entries, list) else [])
        if isinstance(entry, dict)
        and isinstance(entry.get("key"), str)
        and entry["key"] in screened
        and quoted_span(text, entry.get("quote")) is None
    )


def read_one(
    client: Completer,
    model: str,
    guides: Guides,
    budget: Budget,
    request: ReviewRequest,
    kept: str | None,
) -> Reading | None:
    """None when the model could not be reached, or when no call is left."""
    replay = _Replay(client, budget, kept)
    for failures in range(ATTEMPTS):
        try:
            review = review_item(replay, model, request, guides)
        except BudgetSpent:
            return None
        except httpx.HTTPError as error:
            log.warning("call failed (%d of %d): %s", failures + 1, ATTEMPTS, type(error).__name__)
            time.sleep(PAUSE * (failures + 1))
            continue
        if replay.raw is None:
            # `review_item` asked nothing: there is no guide to screen with.
            return None
        rejected = rejected_techniques(replay.raw, request.text, guides)
        return Reading(review=review, raw=replay.raw, rejected=rejected, fresh=replay.fresh)
    return None


def read_all(
    client: Completer,
    model: str,
    guides: Guides,
    answers: Answers,
    budget: Budget,
    requests: Mapping[str, ReviewRequest],
    run: int,
) -> dict[str, Reading]:
    """One reading per post that got an answer, now or in an earlier run."""
    keys = {post: cache_key(model, request, guides) for post, request in requests.items()}
    readings: dict[str, Reading] = {}
    with ThreadPoolExecutor(WORKERS) as pool:
        futures = {
            pool.submit(
                read_one, client, model, guides, budget, request, answers.get(keys[post], run)
            ): post
            for post, request in requests.items()
        }
        for done, future in enumerate(as_completed(futures), start=1):
            post, reading = futures[future], future.result()
            if reading is not None:
                if reading.fresh:
                    answers.keep(keys[post], run, post, reading.raw)
                readings[post] = reading
            if done % 100 == 0:
                log.info("run %d: %d of %d posts", run, done, len(futures))
    return readings

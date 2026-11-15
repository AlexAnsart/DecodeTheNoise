"""The review as the server runs it: the LLM, the guides it applies, what its readings measured
to be worth, and the reviews already paid for. Built once at start-up."""

from dataclasses import dataclass

from backend.review.cache import ReviewCache
from backend.review.guides import Guides
from backend.review.measures import Measures
from backend.review.prompt import ReviewRequest, cache_key
from backend.review.reader import Completer, review_item
from backend.review.schema import Review
from backend.review.selection import SelectionReading, read_selection
from backend.review.selection_prompt import SelectionAsk, selection_key


@dataclass
class Reviewer:
    # None when no LLM is configured: nothing is reviewed.
    chat: Completer | None
    model: str
    guides: Guides
    measures: Measures
    cache: ReviewCache

    def has_something_to_ask(self, request: ReviewRequest) -> bool:
        """A probe to answer, or the techniques to screen for."""
        return bool(request.probes) or bool(self.guides.screened())

    def known(self, request: ReviewRequest) -> Review | None:
        """The review of this very question, when it was already paid for."""
        kept = self.cache.get(cache_key(self.model, request, self.guides))
        return self.measures.attach(Review.model_validate_json(kept)) if kept else None

    def item(self, request: ReviewRequest) -> Review:
        """The review of one item, from the cache or asked now. Raises `httpx.HTTPError` when
        the LLM does not answer. Only a review that was read is kept: a failed one is asked
        again next time."""
        kept = self.known(request)
        if kept is not None:
            return kept
        if self.chat is None:
            return Review(status="skipped", reason="No LLM is configured on this server.")
        review = review_item(self.chat, self.model, request, self.guides)
        if review.status == "done":
            key = cache_key(self.model, request, self.guides)
            self.cache.put(key, review.model_dump_json())
        return self.measures.attach(review)

    def known_selection(self, ask: SelectionAsk) -> SelectionReading | None:
        kept = self.cache.get(selection_key(self.model, ask, self.guides))
        return SelectionReading.model_validate_json(kept) if kept else None

    def selection(self, ask: SelectionAsk) -> SelectionReading | None:
        """What the LLM reads in the sample, from the cache or asked now. None when its answer
        cannot be read, or when no LLM is configured."""
        kept = self.known_selection(ask)
        if kept is not None or self.chat is None:
            return kept
        reading = read_selection(self.chat, self.model, ask, self.guides)
        if reading is not None:
            key = selection_key(self.model, ask, self.guides)
            self.cache.put(key, reading.model_dump_json())
        return reading

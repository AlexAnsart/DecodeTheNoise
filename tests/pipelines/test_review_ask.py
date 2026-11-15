"""Asking the review about posts: one paid call per question, a budget, the answers kept.

No test calls a model: a scripted stand-in answers.
"""

import json
import threading
from pathlib import Path

import httpx
import pytest

from backend.review.guides import Guides, load_guides
from backend.review.prompt import ReviewRequest
from pipelines.review import ask
from pipelines.review.ask import Budget, read_all, rejected_techniques
from pipelines.review.cache import Answers
from pipelines.review.draw import draw, seeded_order

MODEL = "test-model"
GUIDE = """# Guide: rhetoric

Evidence for every label of this guide: required.

## `loaded_language`

**Question.** Does the post name something with a charged word where a neutral word exists?
"""
POSTS = {
    "a": ReviewRequest(text="These traitors sold the country.", probes=()),
    "b": ReviewRequest(text="The council meets on Monday.", probes=()),
}


def _answer(*quotes: str) -> str:
    techniques = [{"key": "loaded_language", "explanation": "x", "quote": q} for q in quotes]
    return json.dumps(
        {"voice": "own", "findings": [], "techniques": techniques, "asks": None, "target": None}
    )


class Scripted:
    """Answers every question the same way, and counts the calls. Fails the first `failures`."""

    def __init__(self, answer: str, failures: int = 0) -> None:
        self.answer, self.failures, self.calls = answer, failures, 0
        self._lock = threading.Lock()

    def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        with self._lock:
            self.calls += 1
            failing = self.calls <= self.failures
        if failing:
            raise httpx.ConnectError("no route")
        return self.answer


@pytest.fixture
def guides(tmp_path: Path) -> Guides:
    folder = tmp_path / "guides"
    folder.mkdir()
    (folder / "rhetoric.md").write_text(GUIDE, encoding="utf-8")
    return load_guides(folder)


def test_an_answer_is_paid_once_and_read_again_from_the_file(
    tmp_path: Path, guides: Guides
) -> None:
    path, chat = tmp_path / "answers.jsonl", Scripted(_answer("traitors"))

    first = read_all(chat, MODEL, guides, Answers(path), Budget(10), POSTS, 1)
    again = read_all(chat, MODEL, guides, Answers(path), Budget(10), POSTS, 1)

    assert chat.calls == 2
    assert [t.key for t in first["a"].review.techniques] == ["loaded_language"]
    assert again["a"].review == first["a"].review and again["a"].fresh is False
    assert len(Answers(path)) == 2


def test_a_second_run_asks_again_and_is_kept_apart(tmp_path: Path, guides: Guides) -> None:
    answers, chat = Answers(tmp_path / "answers.jsonl"), Scripted(_answer())

    read_all(chat, MODEL, guides, answers, Budget(10), POSTS, 1)
    read_all(chat, MODEL, guides, answers, Budget(10), POSTS, 2)

    assert chat.calls == 4 and len(answers) == 4


def test_no_call_is_made_beyond_the_budget(tmp_path: Path, guides: Guides) -> None:
    answers, chat = Answers(tmp_path / "answers.jsonl"), Scripted(_answer())

    readings = read_all(chat, MODEL, guides, answers, Budget(1), POSTS, 1)

    assert chat.calls == 1 and len(readings) == 1


def test_a_failed_call_is_asked_again_and_counts_in_the_budget(
    tmp_path: Path, guides: Guides, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ask.time, "sleep", lambda seconds: None)
    answers, chat = Answers(tmp_path / "answers.jsonl"), Scripted(_answer(), failures=1)
    one_post = {"a": POSTS["a"]}

    assert len(read_all(chat, MODEL, guides, answers, Budget(2), one_post, 1)) == 1
    assert chat.calls == 2
    # The budget is spent: a post nobody answered yet stays unanswered.
    spent = Budget(0)
    assert (
        read_all(chat, MODEL, guides, Answers(tmp_path / "other.jsonl"), spent, one_post, 1) == {}
    )


def test_a_technique_quoted_with_words_the_post_lacks_is_counted_as_rejected(
    tmp_path: Path, guides: Guides
) -> None:
    chat = Scripted(_answer("these cowards"))

    reading = read_all(chat, MODEL, guides, Answers(tmp_path / "a.jsonl"), Budget(5), POSTS, 1)["a"]

    assert reading.review.status == "done" and reading.review.techniques == []
    assert reading.rejected == ("loaded_language",)
    assert rejected_techniques("not json", "any text", guides) == ()


def test_an_unreadable_answer_is_a_failed_review_and_is_kept(
    tmp_path: Path, guides: Guides
) -> None:
    answers, chat = Answers(tmp_path / "answers.jsonl"), Scripted("I cannot answer that.")

    reading = read_all(chat, MODEL, guides, answers, Budget(5), {"a": POSTS["a"]}, 1)["a"]

    assert reading.review.status == "failed" and len(answers) == 1


def test_a_shorter_draw_is_the_beginning_of_a_longer_one() -> None:
    keys = [f"post-{number}" for number in range(50)]

    assert seeded_order(keys, 7) == seeded_order(reversed(keys), 7)
    assert seeded_order(keys, 7) != seeded_order(keys, 8)
    assert draw(keys, 10, 7) == draw(keys, 30, 7)[:10]
    assert sorted(draw(keys, 80, 7)) == sorted(keys)

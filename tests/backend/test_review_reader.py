import json
from dataclasses import dataclass, field

import httpx
import pytest

from backend.probes.schema import ProbeInfo
from backend.review.prompt import CONTEXT_CHARS, ITEM_CHARS, SYSTEM, build_prompt
from backend.review.reader import (
    PROMPT_VERSION,
    UNBACKED,
    UNREAD,
    UNREADABLE,
    ReviewRequest,
    cache_key,
    review_item,
)
from backend.review.schema import NO_REVIEW

MODEL = "test-model"
TEXT = "Share this NOW,\n  tag everyone you know!  They are all liars."
NEIGHBOUR = "Retweet before it gets deleted, they hide the truth"


def _info(key: str, description: str) -> ProbeInfo:
    return ProbeInfo(
        key=key,
        label=key.replace("_", " ").capitalize(),
        description=description,
        family="test",
        state="shown",
        possible=None,
        probable=None,
        report="probes",
    )


CALLS = _info("call_amplify", "Asks to share, repost, copy-paste, tag, push a hashtag")
ATTACK = _info("attack_political_group", "Demeans a camp, a party, a profession, an institution")
REQUEST = ReviewRequest(
    text=TEXT, probes=(CALLS, ATTACK), neighbours=(NEIGHBOUR,), actor_items=("Another post",)
)


@dataclass
class FakeCompleter:
    """Answers a fixed text and records what it was asked. No model is called."""

    answer: str
    asked: list[tuple[str, str, int]] = field(default_factory=list)

    def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        self.asked.append((system, user, max_tokens))
        return self.answer


def _answer(*findings: dict[str, object]) -> FakeCompleter:
    return FakeCompleter(json.dumps({"findings": list(findings)}))


def _finding(
    probe: str, reading: str, quote: str | None, why: str = "It says so."
) -> dict[str, object]:
    return {"probe": probe, "reading": reading, "explanation": why, "quote": quote}


def test_a_quote_of_the_item_is_kept_as_the_item_writes_it() -> None:
    client = _answer(
        _finding("call_amplify", "supported", "Share this NOW, tag everyone", "It  asks to tag."),
        _finding("attack_political_group", "not supported", None),
    )

    review = review_item(client, MODEL, REQUEST)

    assert review.status == "done" and review.reason is None
    assert (review.model, review.prompt_version, review.measured) == (MODEL, PROMPT_VERSION, False)
    calls, attack = review.findings
    assert (calls.probe, calls.reading) == ("call_amplify", "supported")
    # The model collapsed the line break; the span is given back as the item has it.
    assert calls.quote == "Share this NOW,\n  tag everyone"
    assert calls.quote in TEXT
    assert calls.explanation == "It asks to tag."
    assert (attack.reading, attack.quote) == ("not supported", None)
    assert client.asked[0][0] == SYSTEM


def test_a_quote_that_is_not_in_the_item_drops_the_reading() -> None:
    client = _answer(
        _finding("call_amplify", "supported", "Share this with everyone"),
        # Copied from the context, not from the item.
        _finding("attack_political_group", "supported", "they hide the truth"),
    )

    review = review_item(client, MODEL, REQUEST)

    assert review.status == "done"
    for finding in review.findings:
        assert (finding.reading, finding.quote, finding.explanation) == ("unclear", None, UNBACKED)


def test_findings_follow_the_probes_asked() -> None:
    client = _answer(
        _finding("made_up_probe", "supported", "They are all liars."),
        _finding("attack_political_group", "supported", "They are all liars."),
        _finding("attack_political_group", "not supported", None),
        {"probe": "call_amplify", "reading": "certain", "explanation": "x", "quote": None},
    )

    review = review_item(client, MODEL, REQUEST)

    assert [finding.probe for finding in review.findings] == [
        "call_amplify",
        "attack_political_group",
    ]
    calls, attack = review.findings
    # Its only finding was malformed: the probe is left unread, the other finding stands.
    assert (calls.reading, calls.explanation, calls.quote) == ("unclear", UNREAD, None)
    assert (attack.reading, attack.quote) == ("supported", "They are all liars.")


@pytest.mark.parametrize(
    "answer",
    [
        "",
        "Sure, here is my review.",
        "[1, 2]",
        '{"findings": "none"}',
        '{"verdict": "supported"}',
        json.dumps({"findings": [_finding("made_up_probe", "supported", None)]}),
        json.dumps({"findings": [{"probe": "call_amplify"}]}),
    ],
)
def test_an_answer_that_cannot_be_read_gives_a_failed_review(answer: str) -> None:
    review = review_item(FakeCompleter(answer), MODEL, REQUEST)

    assert (review.status, review.reason, review.findings) == ("failed", UNREADABLE, [])
    assert (review.model, review.prompt_version) == (MODEL, PROMPT_VERSION)


def test_the_prompt_gives_each_question_the_item_and_a_bounded_context() -> None:
    long_item = "word " * 2_000
    request = ReviewRequest(
        text=long_item,
        probes=(CALLS, ATTACK),
        neighbours=tuple(f"neighbour {i}\n " + "n" * 400 for i in range(12)),
        actor_items=tuple(f"own {i}" for i in range(9)),
    )

    prompt = build_prompt(request)

    for info in (CALLS, ATTACK):
        assert f"key: {info.key}" in prompt and f"question: {info.description}" in prompt
    assert long_item[:ITEM_CHARS] in prompt and long_item[: ITEM_CHARS + 5] not in prompt
    assert "neighbour 7" in prompt and "neighbour 8" not in prompt
    assert "own 4" in prompt and "own 5" not in prompt
    first = next(line for line in prompt.splitlines() if line.startswith("- neighbour 0"))
    assert len(first) == len("- ") + CONTEXT_CHARS and "\n" not in first
    assert build_prompt(ReviewRequest(TEXT, (CALLS,), (), ())).endswith("None.")


def test_the_answer_gets_room_for_every_probe() -> None:
    one = _answer(_finding("call_amplify", "not supported", None))
    two = _answer(_finding("call_amplify", "not supported", None))

    review_item(one, MODEL, ReviewRequest(TEXT, (CALLS,), (), ()))
    review_item(two, MODEL, REQUEST)

    assert one.asked[0][2] < two.asked[0][2]


def test_the_cache_key_changes_with_what_is_asked() -> None:
    same = ReviewRequest(TEXT, (CALLS, ATTACK), (NEIGHBOUR,), ("Another post",))

    assert cache_key(MODEL, REQUEST) == cache_key(MODEL, same)
    assert len(cache_key(MODEL, REQUEST)) == 64
    others = [
        cache_key("another-model", REQUEST),
        cache_key(
            MODEL, ReviewRequest(TEXT + "!", (CALLS, ATTACK), (NEIGHBOUR,), ("Another post",))
        ),
        cache_key(MODEL, ReviewRequest(TEXT, (CALLS,), (NEIGHBOUR,), ("Another post",))),
        cache_key(MODEL, ReviewRequest(TEXT, (CALLS, ATTACK), (), ("Another post",))),
    ]
    assert len({cache_key(MODEL, REQUEST), *others}) == 5


def test_without_a_probe_nothing_is_asked() -> None:
    client = _answer()

    assert review_item(client, MODEL, ReviewRequest(TEXT, (), (), ())) == NO_REVIEW
    assert client.asked == []


def test_a_network_failure_is_left_to_the_caller() -> None:
    class Down:
        def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
            raise httpx.ConnectError("no route to the router")

    with pytest.raises(httpx.HTTPError):
        review_item(Down(), MODEL, REQUEST)

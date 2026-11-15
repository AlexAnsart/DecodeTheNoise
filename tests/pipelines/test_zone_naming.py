import numpy as np

from pipelines.zones.naming import (
    PROMPT_VERSION,
    CachedName,
    build_prompt,
    name_zone,
    parse_name,
    representative,
    tell_apart,
)


class FakeClient:
    """Stands in for the AI Router: no test makes a paid call."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        return self.answer


def test_parse_name_reads_the_json_asked_for() -> None:
    assert parse_name('{"name": "Health and fitness tips"}') == "Health and fitness tips"


def test_parse_name_tidies_spaces_and_quotes() -> None:
    assert parse_name('{"name": "  Local   crime news. "}') == "Local crime news"


def test_parse_name_rejects_what_is_not_the_json_asked_for() -> None:
    assert parse_name("Health and fitness") is None
    assert parse_name('{"title": "Health and fitness"}') is None
    assert parse_name('["Health and fitness"]') is None


def test_parse_name_rejects_a_name_of_the_wrong_length() -> None:
    assert parse_name('{"name": "Fitness"}') is None
    assert parse_name('{"name": "A very long name that goes on and on"}') is None


def test_prompt_holds_the_words_and_cuts_long_posts() -> None:
    prompt = build_prompt(["workout", "diet"], ["x" * 1000, "two\nlines"])
    assert "workout, diet" in prompt
    assert "x" * 281 not in prompt
    assert "- two lines" in prompt


def test_representative_puts_the_most_central_member_first() -> None:
    vectors = np.array([[1.0, 0.0], [0.8, 0.6], [0.0, 1.0], [0.96, 0.28]], dtype=np.float32)
    members = np.array([0, 1, 3])
    assert representative(vectors, members, 2) == [3, 0]


def test_a_named_zone_is_asked_once_then_read_from_the_cache() -> None:
    client = FakeClient('{"name": "Health and fitness"}')
    cache: dict[str, CachedName] = {}
    first = name_zone(client, "model-a", cache, ["workout"], ["Leg day"])
    second = name_zone(client, "model-a", cache, ["workout"], ["Leg day"])
    assert first == second == "Health and fitness"
    assert client.calls == 1
    kept = next(iter(cache.values()))
    assert (kept.model, kept.prompt_version) == ("model-a", PROMPT_VERSION)


def test_another_model_is_another_question() -> None:
    client = FakeClient('{"name": "Health and fitness"}')
    cache: dict[str, CachedName] = {}
    name_zone(client, "model-a", cache, ["workout"], ["Leg day"])
    name_zone(client, "model-b", cache, ["workout"], ["Leg day"])
    assert client.calls == 2


def test_a_malformed_answer_gives_no_name() -> None:
    client = FakeClient("I think this is about sport.")
    assert name_zone(client, "model-a", {}, ["workout"], ["Leg day"]) is None
    assert client.calls == 2


class WordyThenShort:
    """Answers one word too many, then follows the rule once it is restated."""

    def __init__(self) -> None:
        self.asked: list[str] = []

    def complete(self, system: str, user: str) -> str:
        self.asked.append(user)
        if len(self.asked) == 1:
            return '{"name": "Reactions to Rude or Delusional Behavior"}'
        return '{"name": "Reactions to Rude Behavior"}'


def test_an_answer_that_breaks_the_format_is_asked_once_more() -> None:
    client = WordyThenShort()
    cache: dict[str, CachedName] = {}
    assert (
        name_zone(client, "model-a", cache, ["rude"], ["How rude"]) == "Reactions to Rude Behavior"
    )
    first, second = client.asked
    assert second.startswith(first) and "2 to 5" in second
    # Both answers are kept: the same zone costs nothing the next time.
    assert (
        name_zone(client, "model-a", cache, ["rude"], ["How rude"]) == "Reactions to Rude Behavior"
    )
    assert len(client.asked) == 2


def test_twin_names_are_told_apart_by_a_word_the_others_lack() -> None:
    names = ["Sports News", "Daily Workouts", "Sports News", "Sports News"]
    words = [["sports", "game", "lsu"], ["gym"], ["game", "nfl", "cubs"], ["nfl", "game", "golf"]]
    assert tell_apart(names, words) == [
        "Sports News",
        "Daily Workouts",
        "Sports News (nfl)",
        "Sports News (golf)",
    ]

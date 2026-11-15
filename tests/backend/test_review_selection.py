import json
from pathlib import Path

import numpy as np
import pytest
from probe_fakes import PACK_EMBEDDING_KEY, FakeProbe, write_pack
from review_fakes import write_guides

from backend.probes.pack import load_probes
from backend.review.guides import NO_GUIDES, Guides, load_guides
from backend.review.selection import PER_ACTOR, parse_selection, probe_rates, sample
from backend.review.selection_prompt import (
    MAX_POSTS,
    SelectionAsk,
    selection_key,
    selection_prompt,
    selection_system,
)

ASK = SelectionAsk(
    posts=((7, "They will come for your savings next"), (2, "They will come for your jobs next"))
)


@pytest.fixture
def guides(tmp_path: Path) -> Guides:
    return load_guides(write_guides(tmp_path))


def test_rates_compare_the_selection_with_the_rest_of_the_map(tmp_path: Path) -> None:
    listed = [
        FakeProbe("calls", possible_cut=-1.0, probable_cut=2.0),
        FakeProbe("rare", probable_cut=3.0),
        FakeProbe("quiet", possible_cut=0.0),
        FakeProbe("net", state="review-only", review_cut=1.0),
    ]
    write_pack(tmp_path, listed)
    probes = load_probes(tmp_path, PACK_EMBEDDING_KEY)
    scores = np.array(
        [
            [0.9, 0.9, 0.1, 0.9],
            [0.6, 0.7, 0.1, 0.9],
            [0.1, 0.1, 0.1, 0.9],
            [0.6, 0.1, 0.1, 0.1],
            [0.1, 0.1, 0.1, 0.1],
            [0.1, 0.1, 0.1, 0.1],
        ],
        dtype=np.float32,
    )

    rates = probe_rates(probes, scores, np.array([0, 1, 2]))

    # The review-only probe is not reported. A probe that flags here and nowhere else comes
    # first; one that flags nothing here comes last.
    assert [rate.key for rate in rates] == ["rare", "calls", "quiet"]
    rare, calls, quiet = rates
    # `rare` has no `possible` level: 0.7 is not a flag for it.
    assert (rare.flagged, rare.rate, rare.elsewhere, rare.lift) == (
        1,
        pytest.approx(1 / 3),
        0.0,
        None,
    )
    assert (calls.flagged, calls.rate, calls.elsewhere) == (
        2,
        pytest.approx(2 / 3),
        pytest.approx(1 / 3),
    )
    assert calls.lift == pytest.approx(2.0) and calls.label == "Calls"
    assert (quiet.flagged, quiet.rate, quiet.lift) == (0, 0.0, None)


def test_the_sample_is_the_centre_of_the_selection_a_few_posts_per_actor() -> None:
    axes = np.eye(4, dtype=np.float32)
    # Three pairs set symmetrically around the first axis, which is then their mean direction:
    # points 4 and 5 are the nearest to it, then 2 and 3, then 0 and 1.
    offsets = [(1, 0.6), (1, -0.6), (2, 0.3), (2, -0.3), (3, 0.1), (3, -0.1)]
    vectors = np.stack([axes[0] + shift * axes[axis] for axis, shift in offsets])
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    actors = {4: "a", 5: "a", 2: "a", 3: "b", 0: None, 1: None}

    read = sample(vectors, np.arange(6), actors)

    # Nearest first. The third post of actor `a` is left out; posts without an actor all count.
    assert read == [4, 5, 3, 0, 1]
    assert PER_ACTOR == 2

    many = np.tile(axes[0], (40, 1))
    assert len(sample(many, np.arange(40), {})) == MAX_POSTS


def test_every_span_is_checked_in_the_post_it_cites(guides: Guides) -> None:
    answer = {
        "statement": "The posts  warn of a loss\n to come.",
        "techniques": [
            {
                "key": "fear_appeal",
                "explanation": "Each post  warns of a harm to come.",
                "examples": [
                    {"post": 1, "quote": "come for your savings next"},
                    {"post": 2, "quote": "come for your jobs next"},
                    {"post": 2, "quote": "They will"},
                    {"post": 3, "quote": "They will"},
                ],
            },
            # Shown by one post only, cited in the wrong post, not a screened technique.
            {
                "key": "loaded_language",
                "explanation": "x",
                "examples": [{"post": 1, "quote": "savings"}],
            },
            {
                "key": "whataboutism",
                "explanation": "x",
                "examples": [
                    {"post": 1, "quote": "your jobs"},
                    {"post": 2, "quote": "your savings"},
                ],
            },
            {"key": "call_amplify", "explanation": "x", "examples": [{"post": 1, "quote": "They"}]},
        ],
        "asks": {"post": 2, "quote": "come for your savings"},
        "targets": [
            {"post": 1, "quote": "They"},
            {"post": 2, "quote": "they"},
            {"post": 2, "quote": "They"},
            {"post": 1, "quote": "your jobs"},
        ],
    }

    reading = parse_selection(json.dumps(answer), ASK, guides)

    assert reading is not None
    assert reading.statement == "The posts warn of a loss to come."
    assert [technique.key for technique in reading.techniques] == ["fear_appeal"]
    fear = reading.techniques[0]
    assert (fear.name, fear.explanation) == ("Fear appeal", "Each post warns of a harm to come.")
    # One example per post, each with the point of the map the post is.
    assert [(example.index, example.quote) for example in fear.examples] == [
        (7, "come for your savings next"),
        (2, "come for your jobs next"),
    ]
    # The span of `asks` is not in the post it cites; a target is kept once.
    assert reading.asks is None and reading.targets == ["They"]


def test_an_answer_without_its_statement_cannot_be_read(guides: Guides) -> None:
    assert parse_selection('{"techniques": []}', ASK, guides) is None
    assert parse_selection("not json", ASK, guides) is None
    alone = parse_selection('{"statement": "Nothing in common."}', ASK, NO_GUIDES)
    assert alone is not None and alone.techniques == [] and alone.targets == []


def test_the_selection_prompt_describes_what_is_shared_never_why(guides: Guides) -> None:
    system = selection_system(guides)

    assert "People who agree are not a campaign." in system
    assert "never why they share it and never who is behind them" in system
    assert "Never say that the posts are coordinated, a campaign, written by bots" in system
    assert "1. Read every post." in system and "3. Screen the posts for every technique" in system
    assert "# Guide: rhetoric" in system and "## 3. Own voice" in system
    assert "techniques" not in selection_system(NO_GUIDES)
    prompt = selection_prompt(ASK)
    assert "[1] They will come for your savings next\n[2] They will come for your jobs" in prompt
    assert selection_key("m", ASK, guides) != selection_key("m", ASK, NO_GUIDES)
    assert selection_key("m", ASK, guides) != selection_key("other", ASK, guides)

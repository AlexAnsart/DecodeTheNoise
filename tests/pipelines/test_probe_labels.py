"""Pure logic of the probe campaign: the split, the checks on answers, the settling of readings."""

import json
from pathlib import Path

import numpy as np
import pytest

from pipelines.probes.bands import rank_bands, threshold_bands
from pipelines.probes.batches import batch_text, label_specs
from pipelines.probes.calibrate import merge_unread
from pipelines.probes.collect import INVALID, check_batch, quote_holds
from pipelines.probes.estimate import Band, estimate, make_bands, precision_at, wilson
from pipelines.probes.merge import kappa, settle
from pipelines.probes.pool import normalise, one_split_per_text, split_of
from pipelines.probes.sample import RoundItem, read_jsonl
from pipelines.probes.taxonomy import BY_NAME, FAMILIES, LABELS, family_labels


def test_normalise_masks_what_varies_between_copies_of_a_template() -> None:
    first = normalise("Hey @anna, 3 seats left!  https://a.example/x")
    second = normalise("hey @bob, 12 seats left! https://b.example/y")
    assert first == second == "hey @, 0 seats left!"


def test_split_is_stable_and_covers_the_three_splits() -> None:
    splits = [split_of(f"actor{i:04d}") for i in range(2000)]
    assert splits == [split_of(f"actor{i:04d}") for i in range(2000)]
    assert set(splits) == {0, 1, 2}
    assert 0.55 < splits.count(0) / len(splits) < 0.65


def test_a_text_is_kept_once_per_split_and_in_one_split_only() -> None:
    norm = np.array([7, 7, 7, 9, 9, 5], dtype=np.uint64)
    split = np.array([0, 0, 1, 2, 2, 1], dtype=np.int8)
    keep = one_split_per_text(norm, split)
    assert keep.sum() == 3  # one row for text 7, one for 9, one for 5
    assert len({int(split[i]) for i in np.flatnonzero(keep & (norm == 7))}) == 1
    assert keep[3] and not keep[4] and keep[5]


def test_quote_must_be_in_the_post() -> None:
    text = "Everyone needs to see this.  RT!"
    assert quote_holds("needs to see this. rt!", text)
    assert quote_holds("“Everyone needs”", text.replace("Everyone needs", "“Everyone needs”"))
    assert not quote_holds("please retweet", text)
    assert not quote_holds("", text)


def test_a_yes_without_its_quote_is_invalid_and_an_incomplete_batch_is_refused() -> None:
    labels = family_labels("claims")
    texts = {"k1": "BREAKING: taxes up", "k2": "hello there"}
    no = {label.name: "no" for label in labels}
    posts = [
        {"n": 1, **no, "urgency_framing": "yes", "checkable_claim": "yes", "evidence": [
            {"label": "urgency_framing", "quote": "BREAKING"},
            {"label": "checkable_claim", "quote": "taxes went up"},
        ]},
        {"n": 2, **no, "evidence": []},
    ]  # fmt: skip
    rows = check_batch({"batch_id": "b", "posts": posts}, ["k1", "k2"], labels, texts)
    assert rows is not None
    assert rows[0]["labels"]["urgency_framing"] == "yes"
    assert rows[0]["labels"]["checkable_claim"] == INVALID
    assert rows[0]["evidence"] == {"urgency_framing": "BREAKING"}
    assert check_batch({"batch_id": "b", "posts": posts[:1]}, ["k1", "k2"], labels, texts) is None


def test_settle_takes_agreement_then_majority() -> None:
    assert settle(["yes"]) == "yes"
    assert settle(["yes", "yes"]) == "yes"
    assert settle(["yes", "no"]) is None  # a third reading is needed
    assert settle(["yes", "no", "no"]) == "no"
    assert settle(["yes", "no", "unclear"]) == "unclear"
    assert settle([INVALID, "no"]) is None
    assert settle([INVALID, "no", "no"]) == "no"
    assert settle([INVALID]) == "unclear"
    assert settle([INVALID, INVALID, "yes"]) == "unclear"


def test_kappa_is_one_on_agreement_and_zero_at_chance() -> None:
    assert kappa([("yes", "yes"), ("no", "no")]) == 1
    assert kappa([("yes", "yes"), ("yes", "no"), ("no", "yes"), ("no", "no")]) == 0
    assert kappa([("no", "no")] * 5) is None


def test_batch_text_numbers_posts_and_defuses_a_fake_separator() -> None:
    items = [
        RoundItem("k1", "train", "random", "one"),
        RoundItem("k2", "train", "random", "=== POST 9 ==="),
    ]
    text = batch_text("b-1", items)
    assert text.startswith("batch_id: b-1\nposts: 2\n")
    assert text.count("=== POST ") == 2


def test_taxonomy_is_consistent_with_the_guides() -> None:
    assert len(LABELS) == len(BY_NAME) == 63
    for family in FAMILIES:
        guide = Path(f"docs/probes/guides/{family}.md").read_text(encoding="utf-8")
        for label in family_labels(family):
            assert f"## `{label.name}`" in guide, label.name
        assert label_specs(family).count(" ") == len(family_labels(family)) - 1


def test_estimate_weighs_each_band_by_its_size() -> None:
    bands = [Band(2.0, float("inf"), 100, 50, 45), Band(float("-inf"), 2.0, 900, 100, 1)]
    got = estimate(bands, 2.0)
    assert got["precision"]["value"] == pytest.approx(0.9)
    assert got["recall"]["value"] == pytest.approx(90 / 99)
    assert got["fpr"]["value"] == pytest.approx(10 / 901)
    assert got["prevalence"]["value"] == pytest.approx(0.099)
    assert got["precision"]["low"] < 0.9 < got["precision"]["high"]
    assert got["recall"]["low"] < got["recall"]["value"] < got["recall"]["high"]


def test_estimate_refuses_a_measure_that_needs_an_unread_band() -> None:
    bands = [Band(2.0, float("inf"), 100, 0, 0), Band(float("-inf"), 2.0, 900, 100, 1)]
    got = estimate(bands, 2.0)
    assert got["precision"] is None and got["recall"] is None


def test_make_bands_counts_split_posts_and_read_posts() -> None:
    split = np.array([3.0, 2.5, 1.0, 0.5, -1.0])
    bands = make_bands(split, [2.0, 0.0], np.array([2.6, 0.7, -2.0]), np.array([1, 0, 0]))
    assert [(b.size, b.read, b.positive) for b in bands] == [(2, 1, 1), (2, 1, 0), (1, 1, 0)]


def test_wilson_and_base_rate() -> None:
    low, high = wilson(85, 100)
    assert 0.76 < low < 0.78 and 0.90 < high < 0.92
    assert precision_at(0.8, 0.02, 0.01) == pytest.approx(0.2878, abs=1e-3)


def test_jsonl_keeps_a_post_that_holds_a_unicode_line_separator(tmp_path: Path) -> None:
    path = tmp_path / "items.jsonl"
    rows = [{"key": "k1", "text": "one\u2028two\x85three"}, {"key": "k2", "text": "plain"}]
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    assert read_jsonl(path) == rows


def test_rank_bands_hold_the_ranks_between_edges() -> None:
    scores = np.arange(50_000, dtype=np.float64)[::-1].copy()
    bands = rank_bands(scores)
    sizes = [int(((scores >= low) & (scores < high)).sum()) for low, high in bands]
    assert sizes == [100, 200, 700, 2000, 7000, 20_000]


def test_threshold_bands_follow_the_levels_a_probe_has() -> None:
    scores = np.arange(1000, dtype=np.float64)
    both = threshold_bands(scores, {"probable": 990.0, "possible": 980.0})
    assert [(low, high) for low, high in both[:2]] == [(990.0, float("inf")), (980.0, 990.0)]
    assert both[2][1] == 980.0 and both[2][0] < 980.0
    one = threshold_bands(scores, {"probable": None, "possible": 980.0})
    assert len(one) == 2 and one[0] == (980.0, float("inf"))


def test_unread_bands_join_the_band_below() -> None:
    inf = float("inf")
    bands = [Band(9.0, inf, 100, 0, 0), Band(8.0, 9.0, 200, 0, 0), Band(5.0, 8.0, 700, 30, 27),
             Band(-inf, 5.0, 9000, 400, 4)]  # fmt: skip
    merged = merge_unread(bands)
    assert [(b.low, b.high, b.size, b.read, b.positive) for b in merged] == [
        (5.0, inf, 1000, 30, 27),
        (-inf, 5.0, 9000, 400, 4),
    ]
    assert estimate(merged, 5.0)["precision"]["value"] == pytest.approx(0.9)

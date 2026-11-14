import math
from pathlib import Path

import numpy as np
import pytest
from probe_fakes import (
    PACK_DIMS,
    PACK_EMBEDDING_KEY,
    POSSIBLE_MEASURE,
    PROBABLE_MEASURE,
    FakeProbe,
    raw_logits,
    vector_with_logits,
    write_pack,
)

from backend.probes.pack import EMPTY, load_probes
from backend.probes.schema import POSSIBLE_SCORE, PROBABLE_SCORE, WEIGHTS_FILE
from backend.probes.uniform import BELOW_PROBABLE
from backend.workspace.schema import ReviewMode

TWO_LEVELS = [
    FakeProbe("calls", possible_cut=-1.0, probable_cut=2.0),
    FakeProbe("attacks", possible_cut=0.5, probable_cut=1.5),
]


def _row(*scores: float) -> np.ndarray:
    return np.array(scores, dtype=np.float32)


def test_the_two_cuts_land_on_the_same_scores_for_every_probe(tmp_path: Path) -> None:
    arrays = write_pack(tmp_path, TWO_LEVELS)
    probes = load_probes(tmp_path, PACK_EMBEDDING_KEY)
    at_possible = vector_with_logits(arrays, [-1.0, 0.5])
    at_probable = vector_with_logits(arrays, [2.0, 1.5])

    scores = probes.scores(np.stack([at_possible, at_probable]))

    assert scores.shape == (2, 2) and scores.dtype == np.float32
    assert scores[0] == pytest.approx([POSSIBLE_SCORE, POSSIBLE_SCORE], abs=1e-4)
    assert scores[1] == pytest.approx([PROBABLE_SCORE, PROBABLE_SCORE], abs=1e-4)


def test_only_possible_keeps_its_slope_and_never_reaches_probable(tmp_path: Path) -> None:
    arrays = write_pack(tmp_path, [FakeProbe("spam", possible_cut=1.0)])
    probes = load_probes(tmp_path, PACK_EMBEDDING_KEY)
    vectors = np.stack([vector_with_logits(arrays, [logit]) for logit in (1.0, 2.0, 60.0)])

    at_cut, one_above, far_above = probes.scores(vectors)[:, 0].tolist()

    assert at_cut == pytest.approx(POSSIBLE_SCORE, abs=1e-4)
    assert one_above == pytest.approx(1 / (1 + math.exp(-1.0)), abs=1e-4)
    assert far_above == BELOW_PROBABLE < PROBABLE_SCORE
    info = probes.infos[0]
    assert info.possible == POSSIBLE_MEASURE and info.probable is None
    assert [reading.level for reading in probes.readings(_row(far_above))] == ["possible"]


@pytest.mark.parametrize(
    "probe",
    [
        FakeProbe("rare", probable_cut=3.0),
        FakeProbe("rare", possible_cut=3.0, probable_cut=3.0),
        FakeProbe("rare", possible_cut=4.0, probable_cut=3.0),
    ],
)
def test_one_usable_cut_is_the_probable_level_alone(tmp_path: Path, probe: FakeProbe) -> None:
    arrays = write_pack(tmp_path, [probe])
    probes = load_probes(tmp_path, PACK_EMBEDDING_KEY)

    at_cut, below = probes.scores(
        np.stack([vector_with_logits(arrays, [3.0]), vector_with_logits(arrays, [2.0])])
    )[:, 0].tolist()

    assert at_cut == pytest.approx(PROBABLE_SCORE, abs=1e-4)
    info = probes.infos[0]
    assert info.possible is None and info.probable == PROBABLE_MEASURE
    # Between 0.5 and 0.8 there is no level for this probe: nothing is flagged.
    assert POSSIBLE_SCORE < below < PROBABLE_SCORE
    assert probes.readings(_row(below)) == []
    assert [reading.level for reading in probes.readings(_row(0.9))] == ["probable"]


def test_folded_scores_match_the_formula_step_by_step(tmp_path: Path) -> None:
    listed = [*TWO_LEVELS, FakeProbe("spam", possible_cut=1.0), FakeProbe("rare", probable_cut=3.0)]
    arrays = write_pack(tmp_path, listed)
    probes = load_probes(tmp_path, PACK_EMBEDDING_KEY)
    vectors = np.random.default_rng(3).normal(size=(200, PACK_DIMS)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)

    logits = raw_logits(arrays, vectors)
    slope = np.array([math.log(4) / 3.0, math.log(4) / 1.0, 1.0, 1.0])
    shift = np.array([slope[0] * 1.0, -slope[1] * 0.5, -1.0, math.log(4) - 3.0])
    expected = 1 / (1 + np.exp(-(slope * logits + shift)))
    expected[:, 2] = np.minimum(expected[:, 2], BELOW_PROBABLE)

    assert probes.scores(vectors) == pytest.approx(expected, abs=1e-5)


def test_a_pack_of_another_embedding_model_gives_no_probe(tmp_path: Path) -> None:
    write_pack(tmp_path, TWO_LEVELS, embedding_key="another-model@1|prefix=''|dims=4")

    probes = load_probes(tmp_path, PACK_EMBEDDING_KEY)

    assert probes is EMPTY
    assert probes.scores(np.ones((3, PACK_DIMS), dtype=np.float32)).shape == (3, 0)
    assert probes.shown() == () and probes.readings(_row()) == []
    assert probes.score_map(_row()) == {} and probes.triggers(_row(), "possible", 0.0) == []


def test_no_pack_or_unusable_weights_give_no_probe(tmp_path: Path) -> None:
    assert load_probes(tmp_path / "absent", PACK_EMBEDDING_KEY) is EMPTY

    write_pack(tmp_path / "no-weights", TWO_LEVELS)
    (tmp_path / "no-weights" / WEIGHTS_FILE).unlink()
    assert load_probes(tmp_path / "no-weights", PACK_EMBEDDING_KEY) is EMPTY

    arrays = write_pack(tmp_path / "lacks-a-name", TWO_LEVELS)
    arrays["names"] = np.array(["calls", "something_else"])
    np.savez(tmp_path / "lacks-a-name" / WEIGHTS_FILE, **arrays)
    assert load_probes(tmp_path / "lacks-a-name", PACK_EMBEDDING_KEY) is EMPTY

    arrays = write_pack(tmp_path / "wrong-shape", TWO_LEVELS)
    arrays["mean"] = arrays["mean"][:-1]
    np.savez(tmp_path / "wrong-shape" / WEIGHTS_FILE, **arrays)
    assert load_probes(tmp_path / "wrong-shape", PACK_EMBEDDING_KEY) is EMPTY


def test_a_cut_without_its_measure_is_not_applied(tmp_path: Path) -> None:
    listed = [
        FakeProbe("calls", possible_cut=-1.0, probable_cut=2.0, measured_probable=False),
        FakeProbe("unmeasured", possible_cut=0.0, measured_possible=False),
    ]
    write_pack(tmp_path, listed)

    probes = load_probes(tmp_path, PACK_EMBEDDING_KEY)

    assert [info.key for info in probes.infos] == ["calls"]
    assert probes.infos[0].possible is not None and probes.infos[0].probable is None
    assert [reading.level for reading in probes.readings(_row(0.79))] == ["possible"]


def test_readings_are_the_shown_probes_that_flag_strongest_first(tmp_path: Path) -> None:
    listed = [
        *TWO_LEVELS,
        FakeProbe("hidden", possible_cut=0.0, probable_cut=1.0, state="review-only"),
        FakeProbe("quiet", possible_cut=0.0, probable_cut=1.0),
    ]
    write_pack(tmp_path, listed)
    probes = load_probes(tmp_path, PACK_EMBEDDING_KEY)

    readings = probes.readings(_row(0.62, 0.93, 0.99, 0.2))

    assert [(r.key, r.level) for r in readings] == [("attacks", "probable"), ("calls", "possible")]
    assert readings[0].reliability == PROBABLE_MEASURE
    assert readings[1].reliability == POSSIBLE_MEASURE
    assert readings[0].label == "Attacks" and readings[0].report == "probes"
    assert readings[0].score == pytest.approx(0.93, abs=1e-4)
    assert [info.key for info in probes.shown()] == ["calls", "attacks", "quiet"]


def test_triggers_follow_the_review_mode(tmp_path: Path) -> None:
    listed = [
        *TWO_LEVELS,
        FakeProbe("hidden", possible_cut=0.0, probable_cut=1.0, state="review-only"),
        FakeProbe("spam", possible_cut=1.0),
    ]
    write_pack(tmp_path, listed)
    probes = load_probes(tmp_path, PACK_EMBEDDING_KEY)
    row = _row(0.62, 0.93, 0.85, 0.7)

    def keys(mode: ReviewMode, min_score: float = 0.0) -> list[str]:
        return [info.key for info in probes.triggers(row, mode, min_score)]

    assert keys("off") == []
    assert keys("probable") == ["attacks", "hidden"]
    assert keys("possible") == ["attacks", "hidden", "spam", "calls"]
    assert keys("score", 0.69) == ["attacks", "hidden", "spam"]
    assert keys("score", 0.95) == []


def test_score_map_cuts_to_four_decimals_and_keeps_shown_probes_only(tmp_path: Path) -> None:
    listed = [
        *TWO_LEVELS,
        FakeProbe("hidden", possible_cut=0.0, probable_cut=1.0, state="review-only"),
        FakeProbe("quiet", possible_cut=0.0, probable_cut=1.0),
    ]
    write_pack(tmp_path, listed)
    probes = load_probes(tmp_path, PACK_EMBEDDING_KEY)

    scores = probes.score_map(_row(BELOW_PROBABLE, PROBABLE_SCORE, 0.5, math.nan))

    # A score just under a level is never written as the level itself.
    assert scores == {"calls": 0.7999, "attacks": 0.8}


def test_column_gives_the_place_of_a_probe_in_the_scores(tmp_path: Path) -> None:
    write_pack(tmp_path, TWO_LEVELS)
    probes = load_probes(tmp_path, PACK_EMBEDDING_KEY)

    assert probes.column("attacks") == 1
    with pytest.raises(KeyError):
        probes.column("unknown")


def test_one_vector_is_scored_as_one_row(tmp_path: Path) -> None:
    arrays = write_pack(tmp_path, TWO_LEVELS)
    probes = load_probes(tmp_path, PACK_EMBEDDING_KEY)

    scores = probes.scores(vector_with_logits(arrays, [2.0, 0.5]))

    assert scores.shape == (1, 2)
    assert scores[0] == pytest.approx([PROBABLE_SCORE, POSSIBLE_SCORE], abs=1e-4)

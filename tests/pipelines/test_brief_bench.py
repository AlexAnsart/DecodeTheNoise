import random

import numpy as np
import pytest

from pipelines.briefs.design import balanced
from pipelines.briefs.fields import LEVELS
from pipelines.briefs.interchange_detector import CALIBRATION_ARM, detector, precision
from pipelines.briefs.loop import energy_distance
from pipelines.briefs.ncurve import interval, pooled_accuracy


def test_balanced_gives_each_level_as_often_as_the_others() -> None:
    values = balanced(LEVELS["persona"], 10, offset=3, rng=random.Random(0))
    assert sorted(values.count(level) for level in LEVELS["persona"]) == [2, 2, 2, 2, 2]
    tones = balanced(LEVELS["tone"], 10, offset=1, rng=random.Random(0))
    assert sorted(tones.count(level) for level in LEVELS["tone"]) == [2, 2, 3, 3]


def test_energy_distance_is_near_zero_within_one_distribution() -> None:
    rng = np.random.default_rng(0)
    a, b = rng.normal(size=(200, 8)), rng.normal(size=(200, 8))
    apart = rng.normal(size=(200, 8)) + 2.0
    assert abs(energy_distance(a, b)) < 0.05
    assert energy_distance(a, apart) > 1.0


def test_reading_more_posts_of_a_group_reads_it_better() -> None:
    rng = np.random.default_rng(0)
    groups = np.repeat(np.arange(40), 16)
    truth = np.repeat(rng.integers(0, 2, size=40), 16)
    # Each post leans weakly toward the truth: one post is a coin toss, sixteen are not.
    scores = rng.normal(size=(640, 2))
    scores[np.arange(640), truth] += 0.5
    one = pooled_accuracy(scores, groups, truth, 1, rng).mean()
    many = pooled_accuracy(scores, groups, truth, 16, rng).mean()
    assert 0.5 < one < 0.75 < many
    mean, low, high = interval(pooled_accuracy(scores, groups, truth, 16, rng), rng)
    assert low <= mean <= high


def test_groups_smaller_than_the_size_read_are_left_out() -> None:
    rng = np.random.default_rng(0)
    groups = np.array([0, 0, 0, 1])
    shares = pooled_accuracy(np.zeros((4, 2)), groups, np.zeros(4, dtype=int), 2, rng)
    assert len(shares) == 1


def test_precision_at_a_base_rate_matches_the_worked_example() -> None:
    # 80% recall and a 2% false-positive rate give 29% precision when 1% of groups are positive.
    assert precision(0.8, 0.02, 0.01) == pytest.approx(0.288, abs=0.001)


def test_detector_flags_what_scores_below_the_real_groups() -> None:
    rng = np.random.default_rng(0)
    real = {f"pool-{i}": rng.normal(10, 1, size=20) for i in range(60)}
    result = detector(
        {
            "organic": real,
            CALIBRATION_ARM: real,
            "shared": {f"twin-{i}": rng.normal(0, 1, size=20) for i in range(10)},
        },
        rng,
    )
    assert result["flagged"]["shared"]["rate"][0] == 1.0
    # The threshold is set to let about 5% of the real draws through, on the other half.
    assert result["flagged"][CALIBRATION_ARM]["rate"][0] < 0.15
    assert result["flagged"][CALIBRATION_ARM]["groups"] < 60
    assert result["precision_at_base_rate"]["shared"]["0.05"]["worst_case"] <= 1.0

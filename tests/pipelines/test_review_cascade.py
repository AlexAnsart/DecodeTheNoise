"""The cascade of the evaluation: which probes send a post to the review, and what is counted."""

import numpy as np
import pytest

from backend.probes.pack import Probes
from backend.probes.schema import LevelMeasure, ProbeInfo
from pipelines.review.cascade import cascade_measure, flagging

MEASURE = LevelMeasure(
    precision=0.7,
    precision_low=0.6,
    precision_high=0.8,
    false_positive_rate=0.03,
    recall=0.5,
    read=60,
    flag_rate=0.05,
)


def _probes(*keys: str) -> Probes:
    """One probe per key, each reading one coordinate of the vector as its raw output."""
    infos = tuple(
        ProbeInfo(
            key=key,
            label=key,
            description="",
            family="test",
            state="shown",
            possible=MEASURE,
            probable=None,
            report="probes",
        )
        for key in keys
    )
    size = len(keys)
    return Probes(
        infos=infos,
        weights=np.eye(size, dtype=np.float32),
        bias=np.zeros(size, dtype=np.float32),
        caps=np.ones(size, dtype=np.float32),
    )


def test_a_post_lists_the_technique_probes_that_flag_it_strongest_first() -> None:
    probes = _probes("doubt", "slogan", "profanity")
    vectors = np.array([[1.0, 3.0, 5.0], [-3.0, -1.0, 5.0], [2.0, -2.0, -2.0]], dtype=np.float32)

    found = flagging(probes, vectors, ["a", "b", "c"], {"doubt", "slogan"})

    assert {post: [info.key for info in infos] for post, infos in found.items()} == {
        "a": ["slogan", "doubt"],
        "c": ["doubt"],
    }


def test_the_cascade_counts_the_probe_alone_then_what_the_review_keeps() -> None:
    # Six posts flagged by the probe, three of them annotated yes.
    flagged = {"a": True, "b": True, "c": True, "d": False, "e": False, "f": False}
    # The review read four of them and kept two: one annotated yes, one annotated no.
    supported = {"a": True, "b": False, "d": True, "e": False}
    # Asked without the probe listed, the screen named the technique on one post only.
    screened = {"a": False, "b": False, "d": True, "e": False}

    measure = cascade_measure(flagged, supported, screened)

    assert (measure.flagged, measure.flagged_yes) == (6, 3)
    assert measure.after_probe is not None and measure.after_probe.value == 0.5
    assert (measure.read, measure.read_yes, measure.kept, measure.kept_yes) == (4, 2, 2, 1)
    assert measure.after_review is not None and measure.after_review.value == 0.5
    assert measure.true_positives_kept is not None
    assert measure.true_positives_kept.value == pytest.approx(0.5)
    # The post the screen named is annotated no: it names none of the two true positives.
    assert measure.true_positives_screen_names is not None
    assert (measure.screen_kept_yes, measure.true_positives_screen_names.value) == (0, 0.0)


def test_a_probe_the_review_read_nothing_of_has_no_rate_after_the_review() -> None:
    measure = cascade_measure({"a": True, "b": False}, {}, {})

    assert measure.after_probe is not None
    assert (measure.read, measure.after_review, measure.true_positives_kept) == (0, None, None)

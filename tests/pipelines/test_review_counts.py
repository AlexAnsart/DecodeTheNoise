"""The counts of the review against the annotation, and the rates read on them."""

import pytest

from backend.review.schema import Review, Technique
from pipelines.review.counts import (
    Confusion,
    cohen_kappa,
    confusion,
    measure_label,
    precision_at,
    wilson,
)
from pipelines.review.metrics import label_measures, marked_techniques, pool, runs_agreement


def test_a_share_comes_with_its_wilson_interval() -> None:
    rate = wilson(8, 10)

    assert rate is not None
    assert (rate.value, round(rate.low, 3), round(rate.high, 3)) == (0.8, 0.490, 0.943)


def test_an_interval_stays_between_zero_and_one_and_needs_something_to_count() -> None:
    none_of_twenty = wilson(0, 20)

    assert none_of_twenty is not None
    assert none_of_twenty.low == 0.0 and 0.0 < none_of_twenty.high < 0.2
    assert wilson(0, 0) is None


def test_each_post_falls_in_one_cell() -> None:
    pairs = [(True, True), (True, False), (False, True), (False, False), (False, False)]

    assert confusion(pairs) == Confusion(tp=1, fp=1, fn=1, tn=2)


def test_a_label_with_enough_positives_and_a_fair_reference_gets_its_rates() -> None:
    measure = measure_label(Confusion(tp=6, fp=2, fn=4, tn=88), reference_kappa=0.8)

    assert measure.measurable is True
    assert (measure.marked, measure.positives, measure.n) == (8, 10, 100)
    assert measure.precision is not None and measure.precision.value == 0.75
    assert measure.recall is not None and measure.recall.value == 0.6
    assert measure.fpr is not None and measure.fpr.value == pytest.approx(2 / 90)
    assert measure.f1 == pytest.approx(12 / 18)


def test_a_label_the_annotators_disagree_on_keeps_its_counts_and_gets_no_rate() -> None:
    weak = measure_label(Confusion(tp=6, fp=2, fn=4, tn=88), reference_kappa=0.4)
    unknown = measure_label(Confusion(tp=6, fp=2, fn=4, tn=88), reference_kappa=None)

    for measure in (weak, unknown):
        assert measure.measurable is False
        assert (measure.precision, measure.recall, measure.fpr, measure.f1) == (None,) * 4
        assert (measure.tp, measure.fp, measure.fn, measure.tn) == (6, 2, 4, 88)


def test_a_label_with_too_few_positives_gets_no_rate() -> None:
    measure = measure_label(Confusion(tp=3, fp=1, fn=1, tn=95), reference_kappa=0.9)

    assert measure.measurable is True
    assert (measure.precision, measure.recall, measure.fpr, measure.f1) == (None,) * 4


def test_kappa_is_zero_for_a_review_that_marks_nothing() -> None:
    assert cohen_kappa(Confusion(tp=5, tn=95)) == 1.0
    assert cohen_kappa(Confusion(fn=5, tn=95)) == 0.0
    # Nothing to find and nothing marked: chance explains every agreement.
    assert cohen_kappa(Confusion(tn=100)) is None


def test_precision_falls_where_positives_are_rare() -> None:
    assert precision_at(recall=0.8, fpr=0.02, prevalence=0.01) == pytest.approx(0.288, abs=1e-3)
    assert precision_at(recall=0.0, fpr=0.0, prevalence=0.05) is None


def _review(*keys: str, status: str = "done") -> Review:
    techniques = [Technique(key=key, name=key, explanation="x", quote="y") for key in keys]
    return Review(status=status, techniques=techniques)


def test_only_a_readable_review_marks_techniques() -> None:
    marked = marked_techniques(
        {"a": _review("doubt", "slogan"), "b": _review(), "c": _review(status="failed")}
    )

    assert marked == {"a": frozenset({"doubt", "slogan"}), "b": frozenset()}


def test_a_post_without_a_settled_answer_on_a_label_is_not_counted_for_it() -> None:
    answers = {"a": {"doubt": True}, "b": {"doubt": False, "slogan": True}, "c": {}}
    marked = {"a": frozenset({"doubt"}), "b": frozenset({"doubt"}), "c": frozenset({"doubt"})}

    measures = label_measures(answers, marked, {"doubt": 0.7, "slogan": 0.8})

    assert (measures["doubt"].tp, measures["doubt"].fp, measures["doubt"].n) == (1, 1, 2)
    assert (measures["slogan"].fn, measures["slogan"].n) == (1, 1)


def test_the_pooled_measure_leaves_out_the_labels_that_are_not_measurable() -> None:
    measures = {
        "doubt": measure_label(Confusion(tp=6, fp=2, fn=4, tn=88), reference_kappa=0.7),
        "slogan": measure_label(Confusion(tp=5, fp=0, fn=5, tn=90), reference_kappa=0.8),
        "whataboutism": measure_label(Confusion(tp=1, fp=9, fn=2, tn=88), reference_kappa=0.2),
    }

    pooled = pool(measures)

    assert pooled.labels == ["doubt", "slogan"]
    assert (pooled.tp, pooled.fp, pooled.fn, pooled.tn) == (11, 2, 9, 178)
    assert pooled.precision is not None and pooled.precision.value == pytest.approx(11 / 13)
    # Saying "no technique" everywhere is right on every pair annotated no.
    assert pooled.agreement_without_review is not None
    assert pooled.agreement_without_review.value == pytest.approx(180 / 200)


def test_two_runs_are_compared_on_the_posts_both_answered() -> None:
    first = {"a": frozenset({"doubt"}), "b": frozenset(), "c": frozenset({"slogan"})}
    second = {"a": frozenset({"doubt"}), "b": frozenset({"doubt"}), "d": frozenset()}

    agreement = runs_agreement(first, second, ["doubt", "slogan"], asked=3)

    assert (agreement.asked, agreement.posts, agreement.decisions) == (3, 2, 4)
    assert agreement.same_posts is not None and agreement.same_posts.value == 0.5
    assert agreement.same_decisions is not None and agreement.same_decisions.value == 0.75
    assert agreement.changed == {"doubt": 1, "slogan": 0}

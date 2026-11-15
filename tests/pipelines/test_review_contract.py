"""The metrics the evaluation writes are the ones the server reads."""

from pathlib import Path

from backend.review.measures import load_measures
from pipelines.review.counts import Confusion, LabelMeasure, measure_label
from pipelines.review.metrics import METRICS_FILE, Metrics, RunsAgreement, pool


def _write(reports: Path, labels: dict[str, LabelMeasure]) -> None:
    metrics = Metrics(
        model="test-model",
        prompt_version="review-v2",
        prompt_sha256="0" * 64,
        temperature=0.0,
        reference="A hand-made annotation.",
        split="test",
        round="m1",
        seed=1,
        commit="abc1234",
        generated_at="2026-11-15T01:00:00+01:00",
        asked=100,
        accounts=97,
        posts_with_technique=12,
        posts=100,
        unanswered=0,
        failed=0,
        failed_with_json_inside=0,
        rejected_quotes=0,
        rejected_quotes_on_yes=0,
        rejected_quotes_on_no=0,
        rejected_quotes_by_label={},
        labels=labels,
        pooled=pool(labels),
        cascade="untested",
        runs_agreement=RunsAgreement(
            asked=0, posts=0, same_posts=None, decisions=0, same_decisions=None, changed={}
        ),
        calls=100,
    )
    (reports / "review").mkdir(parents=True)
    (reports / "review" / METRICS_FILE).write_text(metrics.model_dump_json(), encoding="utf-8")


# Marked on enough posts for the server to show the label's own figure.
MEASURED = Confusion(tp=120, fp=30, fn=80, tn=770)


def test_the_server_reads_what_the_evaluation_measured_for_a_label(tmp_path: Path) -> None:
    _write(tmp_path, {"doubt": measure_label(MEASURED, 0.7)})

    measures = load_measures(tmp_path)

    assert measures.covers("test-model", "review-v2")
    measure = measures.of("doubt")
    assert measure is not None
    assert (measure.precision, measure.recall, measure.read) == (0.8, 0.6, 150)


def test_a_label_with_counts_only_does_not_hide_the_measured_ones(tmp_path: Path) -> None:
    labels = {
        "doubt": measure_label(MEASURED, 0.7),
        # The annotators agree too little on this one: it has counts and no rate.
        "whataboutism": measure_label(Confusion(tp=60, fp=40, fn=40, tn=860), 0.2),
    }
    _write(tmp_path, labels)

    measures = load_measures(tmp_path)

    assert measures.of("doubt") is not None
    assert measures.of("whataboutism") is None

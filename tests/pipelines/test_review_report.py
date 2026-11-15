"""The evaluation report of the review: written from the metrics, with nothing left blank."""

import re
from pathlib import Path

import pytest

from pipelines.review import report
from pipelines.review.audit import Audit, Mode, ReadCase
from pipelines.review.cascade import cascade_measure
from pipelines.review.counts import Confusion, measure_label, wilson
from pipelines.review.metrics import METRICS_FILE, Cascade, Metrics, RunsAgreement, pool
from pipelines.review.report import render


def _metrics(cascade: Cascade | str) -> Metrics:
    labels = {
        "doubt": measure_label(Confusion(tp=6, fp=2, fn=4, tn=88), reference_kappa=0.7),
        "whataboutism": measure_label(Confusion(tp=1, fp=3, fn=2, tn=94), reference_kappa=0.2),
    }
    return Metrics(
        model="test-model",
        prompt_version="review-v2",
        prompt_sha256="0123456789abcdef" * 4,
        temperature=0.0,
        reference="A hand-made annotation.",
        split="test",
        round="m1",
        seed=1,
        commit="abc1234",
        generated_at="2026-11-15T01:00:00+01:00",
        asked=101,
        accounts=97,
        posts_with_technique=12,
        posts=100,
        unanswered=0,
        failed=1,
        failed_with_json_inside=1,
        rejected_quotes=3,
        rejected_quotes_on_yes=1,
        rejected_quotes_on_no=2,
        rejected_quotes_by_label={"doubt": 3},
        labels=labels,
        pooled=pool(labels),
        cascade=cascade,
        runs_agreement=RunsAgreement(
            asked=20,
            posts=20,
            same_posts=wilson(19, 20),
            decisions=40,
            same_decisions=wilson(39, 40),
            changed={"doubt": 1, "whataboutism": 0},
        ),
        calls=121,
    )


def test_the_report_holds_every_section_and_no_empty_placeholder() -> None:
    cascade = Cascade(
        pack_run="v1",
        pack_exported_at="2026-11-15T00:00:00+00:00",
        posts=100,
        posts_flagged=9,
        posts_read=4,
        probes={"doubt": cascade_measure({"a": True, "b": False}, {"a": True}, {"a": False})},
        same_as_screen=wilson(3, 4),
    )

    report = render(_metrics(cascade))

    assert report.startswith("# LLM review of one item: evaluation 2026-11-15\n")
    for section in (
        "What is decided",
        "Data",
        "Results on test",
        "Precision at realistic base rates",
        "Baselines",
        "Cascade: a probe flags, the review reads",
        "Agreement between two runs",
        "False-positive audit: the disagreements read",
        "Off-distribution",
        "Limits",
    ):
        assert f"\n## {section}\n" in report
    assert not re.search(r"\{\w+\}", report)
    # A measurable label has its rates with their n; the other one says why it has none.
    assert "| `doubt` | 75.0% (40.9 to 92.9), n=8 | 60.0% (31.3 to 83.2), n=10 |" in report
    assert "| `whataboutism` | counts only: annotators' kappa 0.20, under 0.5 |" in report
    assert "Counts only, no rate: `whataboutism`." in report
    assert "Probe pack: run `v1`, exported 2026-11-15T00:00:00+00:00." in report
    assert "Read: 0 disagreements. Not read yet." in report


def test_a_run_without_a_probe_pack_says_the_cascade_is_untested() -> None:
    assert "Untested: no probe pack" in render(_metrics("untested"))


def test_the_audit_table_counts_the_modes_that_were_tagged(tmp_path: Path) -> None:
    def mode(name: str) -> Mode:
        return Mode(name=name, example=f"An example of {name}.", product="Softer wording.")

    cases = [("a", "irony"), ("b", "irony"), ("c", "quoted"), ("d", "short"), ("e", "other")]
    metrics = _metrics("untested")
    audit = Audit(
        prompt_sha256=metrics.prompt_sha256,
        read=[
            ReadCase(post=post, label="doubt", kind="false positive", mode=tag)
            for post, tag in cases
        ],
        modes={tag: mode(tag) for tag in ("irony", "quoted", "short", "other")},
    )
    path = tmp_path / "audit.json"
    path.write_text(audit.model_dump_json(), encoding="utf-8")

    report = render(metrics, path)

    assert "Read: 5 disagreements on measurable techniques" in report
    assert "5 false positives and 0 misses" in report
    assert "| irony | 2 | An example of irony. | Softer wording. |" in report
    assert "Other modes: other (1)." in report

    # The same record says nothing of the answers of another prompt.
    other_prompt = metrics.model_copy(update={"prompt_sha256": "f" * 64})
    assert "The record on disk is about another prompt." in render(other_prompt, path)


def test_the_report_is_written_beside_the_metrics_it_was_made_from(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    metrics = _metrics("untested")
    (tmp_path / METRICS_FILE).write_text(metrics.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(report, "REPORTS", tmp_path)

    report.main()

    written = tmp_path / "2026-11-15-review-v2.md"
    assert written.read_text(encoding="utf-8") == render(metrics)

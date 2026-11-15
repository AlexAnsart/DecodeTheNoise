"""Writes the evaluation report of the review from the metrics on disk and the audit record.

No figure is typed: the text is in `report_text`, the figures come from `metrics.json`. Run it
again after the audit record changes; it calls no model.

Run: uv run --group pipelines python -m pipelines.review.report
"""

import logging
from pathlib import Path

from pipelines.review.audit import AUDIT_FILE, Audit
from pipelines.review.counts import MIN_POSITIVES, MIN_REFERENCE_KAPPA
from pipelines.review.metrics import METRICS_FILE, REPORTS, Cascade, Metrics
from pipelines.review.report_tables import (
    audit_table,
    base_rates_table,
    baseline_table,
    cascade_table,
    counts_table,
    rates_table,
    share,
)
from pipelines.review.report_text import TEMPLATE

log = logging.getLogger("review.report")


def _cascade(metrics: Metrics) -> str:
    cascade = metrics.cascade
    if not isinstance(cascade, Cascade):
        return "Untested: no probe pack that fits the vectors of the test posts."
    return "\n\n".join(
        [
            f"Probe pack: run `{cascade.pack_run}`, exported {cascade.pack_exported_at}. "
            f"{cascade.posts_flagged} of the "
            f"{cascade.posts:,} test posts are flagged by at least one technique probe at its "
            "lowest level (`possible`, or the review cut of a probe that is not shown). The "
            f"review read {cascade.posts_read} of them, a uniform seeded draw, as the product "
            'sends them: the flagging probes listed, text alone. "Kept" means the review '
            "answered `supported` for the probe.",
            cascade_table(cascade),
            "Precision after the probe is counted on the flagged posts of the random test "
            "sample; the report of the probes estimates it on more posts. The columns after it "
            "are measured on the posts the review read.",
            "Listing the probe or not: the last column is what the screen of the results above "
            "names on the same posts, asked without the probe. The answer given for the probe "
            f"and the screen agree on {share(cascade.same_as_screen)} of the post-probe pairs.",
        ]
    )


def _audit(path: Path | None, metrics: Metrics) -> str:
    if path is None or not path.is_file():
        return "Read: 0 disagreements. Not read yet."
    audit = Audit.model_validate_json(path.read_text(encoding="utf-8"))
    if audit.prompt_sha256 != metrics.prompt_sha256:
        # The record is about the answers of another prompt: it says nothing of these.
        return "Read: 0 disagreements of this run. The record on disk is about another prompt."
    wrong = sum(case.kind == "false positive" for case in audit.read)
    return (
        f"Read: {len(audit.read)} disagreements on measurable techniques, a uniform seeded "
        f"draw: {wrong} false positives and {len(audit.read) - wrong} misses. Each one is "
        f"tagged in `reports/review/{AUDIT_FILE}`.\n\n{audit_table(audit)}"
    )


def render(metrics: Metrics, audit: Path | None = None) -> str:
    pooled, runs = metrics.pooled, metrics.runs_agreement
    changed = ", ".join(f"`{name}` ({count})" for name, count in runs.changed.items() if count)
    bare = ", ".join(f"`{name}`" for name, label in metrics.labels.items() if label.recall is None)
    text = TEMPLATE.format(
        date=metrics.generated_at[:10],
        prompt_version=metrics.prompt_version,
        prompt_sha=metrics.prompt_sha256[:12],
        model=metrics.model,
        temperature=f"{metrics.temperature:g}",
        reference=metrics.reference,
        commit=metrics.commit,
        round=metrics.round,
        asked=f"{metrics.asked:,}",
        posts_with_technique=f"{metrics.posts_with_technique:,}",
        accounts=f"{metrics.accounts:,}",
        posts=f"{metrics.posts:,}",
        failed=metrics.failed,
        failed_with_json=metrics.failed_with_json_inside,
        unanswered=metrics.unanswered,
        counts_table=counts_table(metrics),
        min_kappa=MIN_REFERENCE_KAPPA,
        min_positives=MIN_POSITIVES,
        rates_table=rates_table(metrics),
        pooled_labels=len(pooled.labels),
        pooled_pairs=f"{pooled.tp + pooled.fp + pooled.fn + pooled.tn:,}",
        pooled_precision=share(pooled.precision, pooled.tp + pooled.fp),
        pooled_recall=share(pooled.recall, pooled.tp + pooled.fn),
        pooled_fpr=share(pooled.fpr, pooled.fp + pooled.tn),
        rejected_quotes=metrics.rejected_quotes,
        rejected_on_yes=metrics.rejected_quotes_on_yes,
        rejected_on_no=metrics.rejected_quotes_on_no,
        base_rates_table=base_rates_table(metrics),
        baseline_table=baseline_table(metrics),
        cascade=_cascade(metrics),
        runs_asked=runs.asked,
        runs_posts=runs.posts,
        runs_same_posts=share(runs.same_posts, runs.posts),
        runs_same_decisions=share(runs.same_decisions, runs.decisions),
        runs_changed=changed or "none",
        audit=_audit(audit, metrics),
        counts_only=bare or "none",
    )
    return text + "\n"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    metrics = Metrics.model_validate_json((REPORTS / METRICS_FILE).read_text(encoding="utf-8"))
    path = REPORTS / f"{metrics.generated_at[:10]}-{metrics.prompt_version}.md"
    path.write_text(render(metrics, REPORTS / AUDIT_FILE), encoding="utf-8")
    log.info("wrote %s", path)


if __name__ == "__main__":
    main()

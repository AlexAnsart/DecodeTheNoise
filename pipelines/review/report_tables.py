"""The tables of the evaluation report of the review, as markdown. Pure.

Every figure is formatted from the metrics; nothing is typed by hand.
"""

from collections import Counter
from collections.abc import Sequence

from pipelines.review.audit import Audit
from pipelines.review.counts import (
    MIN_POSITIVES,
    MIN_REFERENCE_KAPPA,
    LabelMeasure,
    Rate,
    precision_at,
)
from pipelines.review.metrics import Cascade, Metrics

PREVALENCES = (0.01, 0.05, 0.20)
MODES_SHOWN = 3
# What a cell shows when nothing was counted.
NONE = "-"


def share(rate: Rate | None, n: int | None = None) -> str:
    """`71.4% (64.6 to 77.3), n=148`; a dash when nothing was counted."""
    if rate is None:
        return NONE
    text = f"{rate.value:.1%} ({100 * rate.low:.1f} to {100 * rate.high:.1f})"
    return text if n is None else f"{text}, n={n:,}"


def number(value: float | None) -> str:
    # Adding zero turns a rounded -0.0 into 0.0.
    return NONE if value is None else f"{round(value, 2) + 0:.2f}"


def _at(recall: float, fpr: float, prevalence: float) -> str:
    found = precision_at(recall, fpr, prevalence)
    return NONE if found is None else f"{found:.0%}"


def _cell(value: object) -> str:
    return f"{value:,}" if isinstance(value, int) else str(value)


def table(header: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    lines = [header, ["---"] * len(header), *rows]
    return "\n".join("| " + " | ".join(_cell(cell) for cell in line) + " |" for line in lines)


def why_no_rate(measure: LabelMeasure) -> str:
    if not measure.measurable:
        return f"annotators' kappa {number(measure.reference_kappa)}, under {MIN_REFERENCE_KAPPA}"
    return f"fewer than {MIN_POSITIVES} positives"


def counts_table(metrics: Metrics) -> str:
    counts = ["Posts (n)", "Annotated yes", "Marked", "TP", "FP", "FN", "TN"]
    dropped = metrics.rejected_quotes_by_label
    rows = [
        [f"`{name}`", m.n, m.positives, m.marked, m.tp, m.fp, m.fn, m.tn, dropped.get(name, 0)]
        for name, m in metrics.labels.items()
    ]
    return table(["Technique", *counts, "Quotes rejected"], rows)


def rates_table(metrics: Metrics) -> str:
    header = [
        "Technique",
        "Precision (95% interval, n)",
        "Recall (95% interval, n)",
        "False-positive rate (95% interval, n)",
        "F1",
        "Kappa, review with annotation",
        "Kappa, two annotators",
    ]
    rows = []
    for name, m in metrics.labels.items():
        kappas = [number(m.kappa), number(m.reference_kappa)]
        if m.recall is None:
            rows.append([f"`{name}`", f"counts only: {why_no_rate(m)}", NONE, NONE, NONE, *kappas])
            continue
        rates = [share(m.precision, m.marked), share(m.recall, m.positives)]
        rows.append([f"`{name}`", *rates, share(m.fpr, m.fp + m.tn), number(m.f1), *kappas])
    return table(header, rows)


def base_rates_table(metrics: Metrics) -> str:
    """Per prevalence: the precision from the two rates measured, then, in brackets, from the
    unfavourable ends of their intervals (low recall, high false-positive rate) and from the
    favourable ones."""
    header = ["Technique", "Share of positives here", *(f"{p:.0%}" for p in PREVALENCES)]
    rows = []
    for name, m in metrics.labels.items():
        if m.recall is None or m.fpr is None:
            continue
        shown = [
            f"{_at(m.recall.value, m.fpr.value, p)} ({_at(m.recall.low, m.fpr.high, p)} to "
            f"{_at(m.recall.high, m.fpr.low, p)})"
            for p in PREVALENCES
        ]
        rows.append([f"`{name}`", f"{m.positives / m.n:.1%}", *shown])
    return table(header, rows)


def baseline_table(metrics: Metrics) -> str:
    pooled = metrics.pooled
    header = [
        "Detector",
        "Precision",
        "Recall",
        "False-positive rate",
        "Pairs answered like the annotation",
    ]
    marked, positives = pooled.tp + pooled.fp, pooled.tp + pooled.fn
    negatives = pooled.fp + pooled.tn
    nothing = ["No technique for any post", "none: it marks nothing", "0%", "0%"]
    review = [
        "This review",
        share(pooled.precision, marked),
        share(pooled.recall, positives),
        share(pooled.fpr, negatives),
    ]
    return table(
        header,
        [
            [*nothing, share(pooled.agreement_without_review, positives + negatives)],
            [*review, share(pooled.agreement, positives + negatives)],
        ],
    )


def cascade_table(cascade: Cascade) -> str:
    header = [
        "Probe",
        "Flagged test posts",
        "Precision after the probe",
        "Read by the review",
        "Kept",
        "Precision after the review",
        "True positives kept",
        "True positives the screen names, same posts",
    ]
    rows = [
        [
            f"`{name}`",
            m.flagged,
            share(m.after_probe, m.flagged),
            m.read,
            m.kept,
            share(m.after_review, m.kept),
            share(m.true_positives_kept, m.read_yes),
            share(m.true_positives_screen_names, m.read_yes),
        ]
        for name, m in cascade.probes.items()
    ]
    return table(header, rows)


def audit_table(audit: Audit) -> str:
    """The most common modes, then the others in one line."""
    counts = Counter(case.mode for case in audit.read).most_common()
    header = ["Failure mode", "Count", "Example (paraphrased)", "What the product does"]
    rows = [
        [audit.modes[mode].name, count, audit.modes[mode].example, audit.modes[mode].product]
        for mode, count in counts[:MODES_SHOWN]
    ]
    rest = [f"{audit.modes[mode].name} ({count})" for mode, count in counts[MODES_SHOWN:]]
    return table(header, rows) + (f"\n\nOther modes: {', '.join(rest)}." if rest else "")

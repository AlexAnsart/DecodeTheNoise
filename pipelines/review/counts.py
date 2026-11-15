"""Counts of the review against the annotation, and the rates read on them. Pure.

A rate is a share of posts with its 95% Wilson interval. A label with too few positives, or
whose annotators disagree too much with each other, keeps its counts and gets no rate.
"""

import math
from collections.abc import Iterable

from pydantic import BaseModel

Z95 = 1.959963984540054
# Under this many positives a rate would say nothing: the counts are reported alone.
MIN_POSITIVES = 5
# Under this agreement between two annotators, agreeing with the annotation means little.
MIN_REFERENCE_KAPPA = 0.5


class Rate(BaseModel):
    value: float
    low: float
    high: float


class Confusion(BaseModel):
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0


class LabelMeasure(Confusion):
    """One label of `metrics.json`. The review reads `precision`, `recall` and `marked`."""

    precision: Rate | None
    recall: Rate | None
    fpr: Rate | None
    f1: float | None
    # Cohen's kappa of the review with the annotation, on the scale of `reference_kappa`.
    kappa: float | None
    marked: int
    positives: int
    n: int
    # Agreement between two annotators on this label, and whether it is enough to measure on.
    reference_kappa: float | None
    measurable: bool


def wilson(hits: int, n: int) -> Rate | None:
    """`hits / n` with its 95% Wilson interval. None when there is nothing to count."""
    if n == 0:
        return None
    share = hits / n
    centre = share + Z95**2 / (2 * n)
    spread = Z95 * math.sqrt(share * (1 - share) / n + Z95**2 / (4 * n**2))
    width = 1 + Z95**2 / n
    return Rate(
        value=share,
        low=max(0.0, (centre - spread) / width),
        high=min(1.0, (centre + spread) / width),
    )


def confusion(pairs: Iterable[tuple[bool, bool]]) -> Confusion:
    """`pairs` holds one (annotated yes, marked by the review) per post."""
    cells = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for actual, marked in pairs:
        cells[("t" if actual == marked else "f") + ("p" if marked else "n")] += 1
    return Confusion(**cells)


def cohen_kappa(counts: Confusion) -> float | None:
    """None when chance alone explains every agreement: one side never varies."""
    n = counts.tp + counts.fp + counts.fn + counts.tn
    if n == 0:
        return None
    observed = (counts.tp + counts.tn) / n
    marked, actual = (counts.tp + counts.fp) / n, (counts.tp + counts.fn) / n
    by_chance = marked * actual + (1 - marked) * (1 - actual)
    return None if by_chance == 1 else (observed - by_chance) / (1 - by_chance)


def measure_label(counts: Confusion, reference_kappa: float | None) -> LabelMeasure:
    marked, positives = counts.tp + counts.fp, counts.tp + counts.fn
    measurable = reference_kappa is not None and reference_kappa >= MIN_REFERENCE_KAPPA
    rated = measurable and positives >= MIN_POSITIVES
    errors = counts.fp + counts.fn
    return LabelMeasure(
        **counts.model_dump(),
        precision=wilson(counts.tp, marked) if rated else None,
        recall=wilson(counts.tp, positives) if rated else None,
        fpr=wilson(counts.fp, counts.fp + counts.tn) if rated else None,
        f1=2 * counts.tp / (2 * counts.tp + errors) if rated else None,
        kappa=cohen_kappa(counts),
        marked=marked,
        positives=positives,
        n=marked + counts.fn + counts.tn,
        reference_kappa=reference_kappa,
        measurable=measurable,
    )


def precision_at(recall: float, fpr: float, prevalence: float) -> float | None:
    """What precision becomes when `prevalence` of the posts are positive. None when the
    detector marks nothing."""
    marked = recall * prevalence + fpr * (1 - prevalence)
    return recall * prevalence / marked if marked else None

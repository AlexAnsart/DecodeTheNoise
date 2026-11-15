"""How far a reading of the review can be trusted: read from its evaluation report.

`reports/review/metrics.json` is written by the evaluation of the review against the annotated
posts, label by label. Its numbers apply to one model and one prompt version: a review made
with another model or prompt is not measured, and says so.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from backend.review.schema import Review, ReviewMeasure

logger = logging.getLogger(__name__)

REPORT = "review"
METRICS_FILE = "metrics.json"
# Under this many posts marked by the review, a precision rests on a handful of posts: the
# label shows no figure of its own, and the measure of all techniques together stands in.
MIN_MARKED = 20


class _Interval(BaseModel):
    value: float
    low: float
    high: float


class LabelMeasure(BaseModel):
    # None when the evaluation gives the label no rate: too few posts, or see `measurable`.
    precision: _Interval | None = None
    recall: _Interval | None = None
    # Posts the review marked with the label, posts annotated with it, posts evaluated.
    marked: int
    positives: int
    n: int
    # False when two annotators agree too little on the label: agreeing with them means little.
    measurable: bool = True


class PooledMeasure(BaseModel):
    """Every (post, technique) pair of the measurable techniques, counted together."""

    precision: _Interval | None = None
    recall: _Interval | None = None
    tp: int
    fp: int


class ReviewReport(BaseModel):
    model: str
    prompt_version: str
    # What the review was compared with.
    reference: str
    labels: dict[str, LabelMeasure]
    pooled: PooledMeasure | None = None


def _measure(
    precision: _Interval | None, recall: _Interval | None, read: int
) -> ReviewMeasure | None:
    if precision is None:
        return None
    return ReviewMeasure(
        precision=precision.value,
        precision_low=precision.low,
        precision_high=precision.high,
        recall=recall.value if recall else None,
        read=read,
        report=REPORT,
    )


@dataclass(frozen=True)
class Measures:
    report: ReviewReport | None = None

    def covers(self, model: str | None, prompt_version: str | None) -> bool:
        report = self.report
        return report is not None and (report.model, report.prompt_version) == (
            model,
            prompt_version,
        )

    def of(self, key: str) -> ReviewMeasure | None:
        """The measure of a label; of its label, for one answer of a label (`theme:sport`)."""
        if self.report is None:
            return None
        found = self.report.labels.get(key) or self.report.labels.get(key.partition(":")[0])
        if found is None or not found.measurable or found.marked < MIN_MARKED:
            return None
        return _measure(found.precision, found.recall, found.marked)

    def overall(self) -> ReviewMeasure | None:
        """The technique screen over every measurable technique, taken together."""
        pooled = self.report.pooled if self.report else None
        return _measure(pooled.precision, pooled.recall, pooled.tp + pooled.fp) if pooled else None

    def attach(self, review: Review) -> Review:
        """The review with the measure of each reading, when the report is about the model and
        the prompt that made it. Otherwise the review says it is not measured."""
        measured = review.status == "done" and self.covers(review.model, review.prompt_version)
        # The precision of a label is what a `supported` reading is worth. It says nothing of
        # a reading that does not support the probe: that one carries no figure.
        findings = [
            finding.model_copy(
                update={
                    "reliability": self.of(finding.probe)
                    if measured and finding.reading == "supported"
                    else None
                }
            )
            for finding in review.findings
        ]
        techniques = [
            found.model_copy(update={"reliability": self.of(found.key) if measured else None})
            for found in review.techniques
        ]
        return review.model_copy(
            update={
                "findings": findings,
                "techniques": techniques,
                "measured": measured,
                "overall": self.overall() if measured else None,
            }
        )


NO_MEASURES = Measures()


def load_measures(reports_dir: Path) -> Measures:
    """Nothing is measured when the report is absent or cannot be read."""
    path = reports_dir / REPORT / METRICS_FILE
    if not path.is_file():
        return NO_MEASURES
    try:
        report = ReviewReport.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        logger.warning("the report of the review cannot be read: %s", error)
        return NO_MEASURES
    logger.info(
        "review measured on %d labels (%s, %s)",
        len(report.labels),
        report.model,
        report.prompt_version,
    )
    return Measures(report)

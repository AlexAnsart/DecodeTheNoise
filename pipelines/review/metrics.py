"""What the evaluation of the review writes to `reports/review/metrics.json`, and how the
readings of the review become those numbers. Pure.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from backend.review.schema import Review
from pipelines.review.cascade import CascadeMeasure
from pipelines.review.counts import Confusion, LabelMeasure, Rate, confusion, measure_label, wilson

REPORTS = Path("reports") / "review"
METRICS_FILE = "metrics.json"
UNTESTED = "untested"


class PooledMeasure(Confusion):
    """Every (post, technique) pair of the measurable techniques, counted together. The pairs
    of one post are not independent, so these intervals are a little too narrow."""

    labels: list[str]
    precision: Rate | None
    recall: Rate | None
    fpr: Rate | None
    # Share of the pairs answered like the annotation, by the review and by "no technique".
    agreement: Rate | None
    agreement_without_review: Rate | None


class RunsAgreement(BaseModel):
    """The same posts asked twice, the second time without the cache."""

    # Posts asked a second time, and those with a readable answer in both runs.
    asked: int
    posts: int
    # Posts whose list of techniques is the same in both runs.
    same_posts: Rate | None
    # (post, technique) pairs answered the same way.
    decisions: int
    same_decisions: Rate | None
    # Per technique, the posts on which the two runs differ.
    changed: dict[str, int]


class Cascade(BaseModel):
    # The pack the probes come from: a run is exported again when its cuts change.
    pack_run: str
    pack_exported_at: str
    # Test posts the probes were applied to, those a technique probe flags, and those of the
    # flagged posts the review read with the probe listed.
    posts: int
    posts_flagged: int
    posts_read: int
    probes: dict[str, CascadeMeasure]
    # (post, probe) pairs where the screen, asked without the probe, answers like the finding.
    same_as_screen: Rate | None


class Metrics(BaseModel):
    model: str
    prompt_version: str
    prompt_sha256: str
    temperature: float
    reference: str
    split: str
    round: str
    seed: int
    commit: str
    generated_at: str
    # Posts of the test sample, the accounts that wrote them (the split is by account), and
    # the posts the annotation finds at least one technique in.
    asked: int
    accounts: int
    posts_with_technique: int
    # Posts the review gave a readable answer for, posts it gave none for, unreadable answers.
    posts: int
    unanswered: int
    failed: int
    # Unreadable answers that hold the JSON object asked for, among other characters.
    failed_with_json_inside: int
    # Techniques the review reported with a quote that is not in the post, so not kept; those
    # of them on a post the annotation says yes for (a hit lost), and no for (an error avoided).
    rejected_quotes: int
    rejected_quotes_on_yes: int
    rejected_quotes_on_no: int
    rejected_quotes_by_label: dict[str, int]
    labels: dict[str, LabelMeasure]
    pooled: PooledMeasure
    cascade: Cascade | Literal["untested"]
    runs_agreement: RunsAgreement
    # Answers paid for and stored, over every run of the evaluation.
    calls: int


def marked_techniques(reviews: Mapping[str, Review]) -> dict[str, frozenset[str]]:
    """Per post with a readable review, the techniques it names."""
    return {
        post: frozenset(technique.key for technique in review.techniques)
        for post, review in reviews.items()
        if review.status == "done"
    }


def label_measures(
    answers: Mapping[str, Mapping[str, bool]],
    marked: Mapping[str, frozenset[str]],
    kappas: Mapping[str, float | None],
) -> dict[str, LabelMeasure]:
    """`answers`: per post, the settled answer on each technique it has one for."""
    return {
        name: measure_label(
            confusion(
                (answers[post][name], name in found)
                for post, found in marked.items()
                if name in answers[post]
            ),
            kappa,
        )
        for name, kappa in kappas.items()
    }


def pool(measures: Mapping[str, LabelMeasure]) -> PooledMeasure:
    kept = {name: measure for name, measure in measures.items() if measure.measurable}
    tp, fp, fn, tn = (
        sum(getattr(measure, cell) for measure in kept.values())
        for cell in ("tp", "fp", "fn", "tn")
    )
    pairs = tp + fp + fn + tn
    return PooledMeasure(
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        labels=list(kept),
        precision=wilson(tp, tp + fp),
        recall=wilson(tp, tp + fn),
        fpr=wilson(fp, fp + tn),
        agreement=wilson(tp + tn, pairs),
        agreement_without_review=wilson(fp + tn, pairs),
    )


def runs_agreement(
    first: Mapping[str, frozenset[str]],
    second: Mapping[str, frozenset[str]],
    techniques: Sequence[str],
    asked: int,
) -> RunsAgreement:
    posts = [post for post in second if post in first]
    changed = {
        name: sum((name in first[post]) != (name in second[post]) for post in posts)
        for name in techniques
    }
    decisions = len(posts) * len(techniques)
    return RunsAgreement(
        asked=asked,
        posts=len(posts),
        same_posts=wilson(sum(first[post] == second[post] for post in posts), len(posts)),
        decisions=decisions,
        same_decisions=wilson(decisions - sum(changed.values()), decisions),
        changed=changed,
    )

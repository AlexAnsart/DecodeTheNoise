"""Writes out the disagreements between the review and the annotation, to be read.

The file holds the text of posts, so it stays under `data/`. What a reader concludes goes to
the audit record (`pipelines.review.audit`).
"""

import json
from collections.abc import Mapping

from backend.review.guides import SCREENED_FAMILIES
from pipelines.paths import DATA
from pipelines.review.ask import Reading
from pipelines.review.counts import LabelMeasure
from pipelines.review.draw import seeded_order
from pipelines.review.testset import Post, annotator_quotes

DISAGREEMENTS_FILE = DATA / "llm" / "review-eval-disagreements.jsonl"


def write_disagreements(
    posts: Mapping[str, Post],
    screen: Mapping[str, Reading],
    labels: Mapping[str, LabelMeasure],
    seed: int,
) -> None:
    """One line per (post, technique) the review and the annotation answer differently, in a
    seeded random order: the first lines are a uniform draw of the disagreements."""
    quotes = annotator_quotes(SCREENED_FAMILIES)
    cases: dict[str, dict[str, object]] = {}
    for key, reading in screen.items():
        if reading.review.status != "done":
            continue
        found = {technique.key: technique for technique in reading.review.techniques}
        for label, yes in posts[key].answers.items():
            if yes == (label in found):
                continue
            technique = found.get(label)
            cases[f"{key}|{label}"] = {
                "post": key,
                "label": label,
                "kind": "miss" if yes else "false positive",
                "measurable": labels[label].measurable,
                "text": posts[key].text,
                "review_explanation": technique.explanation if technique else None,
                "review_quote": technique.quote if technique else None,
                "annotator_quotes": quotes.get((key, label), []),
                # The review reported the technique, and its quote was not in the post.
                "quote_rejected": label in reading.rejected,
            }
    DISAGREEMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = (json.dumps(cases[name], ensure_ascii=False) for name in seeded_order(cases, seed))
    DISAGREEMENTS_FILE.write_text("".join(line + "\n" for line in lines), encoding="utf-8")

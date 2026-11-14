"""Splits a measure by the language of the post, as the language probes themselves read it.

The corpus has no language column. The annotators name the language of the posts they read in
the `format` pass; the probes `lang:en` and `lang:de` learnt from those answers give the language
of every other post.
"""

import numpy as np

from pipelines.probes.dataset import Labelled
from pipelines.probes.pool import SPLITS
from pipelines.probes.sample import RANDOM
from pipelines.probes.score import Probes

GROUPS = ("en", "de", "other")
LEVELS = ("probable", "possible")


def language_groups(probes: Probes, logits: np.ndarray) -> np.ndarray | None:
    """`en`, `de` or `other` for each row: the language probe that fires, the stronger one first."""
    if "lang:en" not in probes.names or "lang:de" not in probes.names:
        return None
    en = logits[:, probes.names.index("lang:en")]
    de = logits[:, probes.names.index("lang:de")]
    out = np.full(len(logits), "other", dtype="U5")
    out[(de > 0) & (de >= en)] = "de"
    out[(en > 0) & (en > de)] = "en"
    return out


def accuracy(labelled: Labelled, groups: np.ndarray, split: str) -> dict[str, object]:
    """How often the probes give the language the annotators named, on random posts of `split`."""
    answers = labelled.answers.get("lang")
    if answers is None:
        return {}
    random = np.array([stratum == RANDOM for stratum in labelled.stratum])
    rows = np.flatnonzero((labelled.split == SPLITS.index(split)) & random & (answers != ""))
    named = np.where(np.isin(answers[rows], GROUPS[:2]), answers[rows], "other")
    out: dict[str, object] = {"n": len(rows), "accuracy": float((named == groups[rows]).mean())}
    for group in GROUPS:
        said = groups[rows] == group
        out[group] = {
            "n": int((named == group).sum()),
            "recall": float((said & (named == group)).sum() / max((named == group).sum(), 1)),
            "precision": float((said & (named == group)).sum() / max(said.sum(), 1)),
        }
    return out


def by_language(
    scores: np.ndarray, y: np.ndarray, groups: np.ndarray, levels: dict[str, float | None]
) -> dict[str, dict[str, list[int]]]:
    """Yes and read counts per language in the band of each level (above it, under the next)."""
    out: dict[str, dict[str, list[int]]] = {}
    upper = float("inf")
    for name in LEVELS:
        low = levels.get(name)
        if low is None:
            continue
        inside = (scores >= low) & (scores < upper)
        out[name] = {
            group: [
                int(y[inside & (groups == group)].sum()),
                int((inside & (groups == group)).sum()),
            ]
            for group in GROUPS
        }
        upper = low
    return out

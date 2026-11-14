"""How well a group is read as a function of how many of its posts are read. Pure."""

import numpy as np

DRAWS = 200
RESAMPLES = 2000


def pooled_accuracy(
    log_proba: np.ndarray,
    groups: np.ndarray,
    truth: np.ndarray,
    size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Per group: the share of random draws of `size` posts whose summed scores name the truth.

    `truth` holds one class index per post, constant inside a group. Groups with fewer posts
    than `size` are left out.
    """
    shares: list[float] = []
    for group in np.unique(groups):
        rows = np.flatnonzero(groups == group)
        if len(rows) < size:
            continue
        picks = rng.permuted(np.tile(rows, (DRAWS, 1)), axis=1)[:, :size]
        guesses = log_proba[picks].sum(axis=1).argmax(axis=1)
        shares.append(float((guesses == truth[rows[0]]).mean()))
    return np.array(shares)


def interval(per_group: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    """Mean over groups with its 95% interval, groups resampled with replacement."""
    if len(per_group) == 0:
        return float("nan"), float("nan"), float("nan")
    picks = rng.integers(0, len(per_group), size=(RESAMPLES, len(per_group)))
    means = per_group[picks].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(per_group.mean()), float(low), float(high)


def rounded(values: tuple[float, float, float]) -> list[float]:
    return [round(v, 3) for v in values]

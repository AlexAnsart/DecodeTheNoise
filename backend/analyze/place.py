"""Places a new text on the map: its nearest points by meaning, and a position among them.

The position is a display, not a measure: the layout was fitted on the corpus, and a new text
is only set down beside the points it resembles most.
"""

import numpy as np


def strongest(scores: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Indices and values of the `k` highest scores, highest first. A score of minus infinity
    marks a point to leave out (the point itself), and is never returned."""
    k = min(k, scores.size)
    if k == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float32)
    top = np.argpartition(-scores, k - 1)[:k]
    order = top[np.argsort(-scores[top], kind="stable")]
    order = order[np.isfinite(scores[order])]
    return order, scores[order]


def nearest(vectors: np.ndarray, vector: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Indices and cosines of the `k` points nearest to `vector`, nearest first."""
    return strongest(vectors @ vector, k)


def neighbour_weights(scores: np.ndarray) -> np.ndarray:
    """Weights of the neighbours for the position, summing to 1. `scores` is nearest first.

    Cosines of the ten nearest sit close together, so weighting by the cosine itself would be
    an almost plain average, often in the empty space between clusters. The weight falls off
    with the gap to the nearest neighbour instead, measured in units of the mean gap: the
    nearest weighs 1, a neighbour at the mean gap 1/e. Equal scores give equal weights.
    """
    gaps = scores[0] - scores
    scale = max(float(gaps.mean()), 1e-6)
    weights = np.exp(-gaps / scale)
    return weights / weights.sum()


def weighted_position(
    coordinates: np.ndarray, indices: np.ndarray, weights: np.ndarray
) -> list[float]:
    return [float(value) for value in weights @ coordinates[indices]]


def beginning(text: str, budget: int) -> str:
    """The start of `text` within `budget` characters, cut between two words when it can be."""
    if len(text) <= budget:
        return text
    cut = max(text.rfind(" ", 0, budget + 1), text.rfind("\n", 0, budget + 1))
    return text[: cut if cut > budget // 2 else budget].rstrip()


def with_title(title: str | None, text: str) -> str:
    """The title, then the text, unless the text already opens with it."""
    if not title or text.startswith(title):
        return text
    return f"{title}\n{text}"

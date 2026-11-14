"""Measures of a probe from posts read by score band.

A split is cut into bands by score. In each band some posts were read, and they are a uniform
sample of the band. The positive rate of a band times its size gives its positives; summing the
bands gives precision, recall, false-positive rate and prevalence at a threshold placed on a band
edge. Intervals come from the Jeffreys posterior of each band's rate, propagated by simulation,
so a band where no positive was read still carries its uncertainty.
"""

from dataclasses import dataclass

import numpy as np

DRAWS = 4000
SEED = 20261114


@dataclass(frozen=True)
class Band:
    low: float  # posts with low <= score < high
    high: float
    size: int  # posts of the split in the band
    read: int  # posts of the band that were read
    positive: int  # of those, how many were answered yes


def make_bands(
    split_scores: np.ndarray, edges: list[float], read_scores: np.ndarray, read_y: np.ndarray
) -> list[Band]:
    """Bands between consecutive `edges` (given from the highest down), then everything below."""
    cuts = [float("inf"), *edges, float("-inf")]
    bands = []
    for high, low in zip(cuts[:-1], cuts[1:], strict=True):
        inside = (read_scores >= low) & (read_scores < high)
        size = int(((split_scores >= low) & (split_scores < high)).sum())
        bands.append(Band(low, high, size, int(inside.sum()), int(read_y[inside].sum())))
    return bands


def _measures(rates: np.ndarray, sizes: np.ndarray, flagged: np.ndarray) -> dict[str, np.ndarray]:
    """`rates` has one row per draw and one column per band."""
    positives = rates * sizes
    negatives = (1 - rates) * sizes
    tp, fp = positives[:, flagged].sum(axis=1), negatives[:, flagged].sum(axis=1)
    fn, tn = positives[:, ~flagged].sum(axis=1), negatives[:, ~flagged].sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return {
            "precision": tp / (tp + fp),
            "recall": tp / (tp + fn),
            "fpr": fp / (fp + tn),
            "prevalence": (tp + fn) / sizes.sum(),
        }


def estimate(bands: list[Band], threshold: float) -> dict[str, object]:
    """Point values and 95% intervals at `threshold`, which must be the low edge of a band.

    A measure that needs a band where nothing was read is None: it cannot be estimated.
    """
    sizes = np.array([band.size for band in bands], dtype=np.float64)
    read = np.array([band.read for band in bands])
    hits = np.array([band.positive for band in bands])
    flagged = np.array([band.low >= threshold for band in bands])
    occupied = sizes > 0
    blind_flagged = bool((occupied & flagged & (read == 0)).any())
    blind_rest = bool((occupied & ~flagged & (read == 0)).any())
    safe = np.maximum(read, 1)
    point = _measures((hits / safe)[None, :], sizes, flagged)
    rng = np.random.default_rng(SEED)
    draws = rng.beta(hits + 0.5, read - hits + 0.5, size=(DRAWS, len(bands)))
    spread = _measures(draws, sizes, flagged)
    out: dict[str, object] = {
        "flagged": int(sizes[flagged].sum()),
        "flag_rate": float(sizes[flagged].sum() / sizes.sum()),
        "read_flagged": int(read[flagged].sum()),
        "positive_flagged": int(hits[flagged].sum()),
        "read_rest": int(read[~flagged].sum()),
        "positive_rest": int(hits[~flagged].sum()),
    }
    needs = {"precision": blind_flagged, "recall": blind_flagged or blind_rest}
    needs.update(fpr=needs["recall"], prevalence=needs["recall"])
    for name, blind in needs.items():
        if blind or not np.isfinite(point[name][0]):
            out[name] = None
        else:
            low, high = np.nanpercentile(spread[name], [2.5, 97.5])
            out[name] = {"value": float(point[name][0]), "low": float(low), "high": float(high)}
    return out


def wilson(positive: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson interval of a proportion."""
    if n == 0:
        return 0.0, 1.0
    p = positive / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))


def precision_at(recall: float, fpr: float, base_rate: float) -> float:
    """What precision becomes when positives are `base_rate` of the posts."""
    hit = recall * base_rate
    return hit / (hit + fpr * (1 - base_rate)) if hit else 0.0

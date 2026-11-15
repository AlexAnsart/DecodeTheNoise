"""The cascade from posts read by score band: each band counts for the posts it holds. Pure.

A read post is kept by the review or not, and annotated yes or not: four outcomes. Their shares
in a band, times the size of the band, give the posts of the whole split in each outcome;
summing the flagged bands gives the precision after the probe, the precision after the review
and the share of the true positives the review keeps. Intervals come from the Jeffreys
posterior of the four shares of each band, propagated by simulation, so a band where an
outcome was never seen still carries its uncertainty.
"""

from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np

DRAWS = 4000
SEED = 20261115
# Under this many posts read, a band says too little of the posts it holds to be counted.
MIN_BAND_READ = 20
MEASURES = ("after_probe", "after_review", "true_positives_kept", "kept_share")


@dataclass(frozen=True)
class BandCounts:
    low: float
    # Posts of the split whose score is in the band.
    size: int
    # Posts of the band read by the annotators and by the review, by outcome.
    kept_yes: int
    kept_no: int
    left_yes: int
    left_no: int

    @property
    def outcomes(self) -> tuple[int, int, int, int]:
        return self.kept_yes, self.kept_no, self.left_yes, self.left_no

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def read_enough(bands: Sequence[BandCounts]) -> list[BandCounts]:
    """The bands from the highest scores down, as long as each was read enough. A probe whose
    lower bands were hardly read is measured on its highest scores only, and says so."""
    kept = []
    for band in bands:
        if band.size > 0 and sum(band.outcomes) < MIN_BAND_READ:
            break
        kept.append(band)
    return kept


def _measures(shares: np.ndarray, sizes: np.ndarray) -> dict[str, np.ndarray]:
    """`shares` has one row per draw, one column per band and one entry per outcome."""
    posts = (shares * sizes[None, :, None]).sum(axis=1)
    kept_yes, kept_no, left_yes, left_no = posts.T
    with np.errstate(divide="ignore", invalid="ignore"):
        return {
            "after_probe": (kept_yes + left_yes) / posts.sum(axis=1),
            "after_review": kept_yes / (kept_yes + kept_no),
            "true_positives_kept": kept_yes / (kept_yes + left_yes),
            "kept_share": (kept_yes + kept_no) / posts.sum(axis=1),
        }


def estimate_cascade(bands: Sequence[BandCounts]) -> dict[str, object]:
    """Counts of the posts read, then each measure with its 95% interval.

    A measure is None when a band that holds posts had none read: nothing says what is in it.
    """
    held = [band for band in bands if band.size > 0]
    counts = np.array([band.outcomes for band in held], dtype=np.float64).reshape(len(held), 4)
    sizes = np.array([band.size for band in held], dtype=np.float64)
    read = counts.sum(axis=1)
    totals = counts.sum(axis=0) if len(held) else np.zeros(4)
    out: dict[str, object] = {
        "read": int(read.sum()),
        "read_yes": int(totals[0] + totals[2]),
        "kept": int(totals[0] + totals[1]),
        "kept_yes": int(totals[0]),
    }
    if not len(held) or (read == 0).any():
        return out | dict.fromkeys(MEASURES)
    point = _measures((counts / read[:, None])[None], sizes)
    rng = np.random.default_rng(SEED)
    draws = np.stack([rng.dirichlet(row + 0.5, size=DRAWS) for row in counts], axis=1)
    spread = _measures(draws, sizes)
    for name in MEASURES:
        value = float(point[name][0])
        if not np.isfinite(value):
            out[name] = None
            continue
        low, high = np.nanpercentile(spread[name], [2.5, 97.5])
        out[name] = {"value": value, "low": float(low), "high": float(high)}
    return out

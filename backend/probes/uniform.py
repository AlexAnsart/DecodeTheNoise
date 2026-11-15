"""Puts the two levels of every probe at the same score. Pure.

A probe's raw output is a logit, and its levels are cuts on that logit, different for each
probe. The score shown is `sigmoid(slope * logit + shift)` with the slope and the shift chosen
so that the `possible` cut lands on 0.5 and the `probable` cut on 0.8. The order of the items
is kept: no decision changes, only the scale they are read on.
"""

import math
from dataclasses import dataclass

import numpy as np

from backend.probes.schema import POSSIBLE_SCORE, PROBABLE_SCORE

# The largest score under `probable`, as the float32 the scores are stored in.
BELOW_PROBABLE = float(np.nextafter(np.float32(PROBABLE_SCORE), np.float32(0.0)))
# Beyond this the sigmoid is 0 or 1 in float32; clipping keeps `exp` from overflowing.
_LOGIT_BOUND = 30.0


def _logit(score: float) -> float:
    return math.log(score / (1.0 - score))


@dataclass(frozen=True)
class Rescale:
    slope: float
    shift: float
    # Ceiling of the score: under `probable` for a probe that has no such level.
    cap: float
    has_possible: bool
    has_probable: bool


def rescale(possible_cut: float | None, probable_cut: float | None) -> Rescale | None:
    """How a probe's logit becomes its score. None without any cut: nothing anchors the score.

    With one level only, the logit keeps its own slope and the level lands on its score. Two
    cuts that are equal or in the wrong order leave one usable level: `probable`.
    """
    if possible_cut is not None and probable_cut is not None and probable_cut > possible_cut:
        slope = (_logit(PROBABLE_SCORE) - _logit(POSSIBLE_SCORE)) / (probable_cut - possible_cut)
        shift = _logit(POSSIBLE_SCORE) - slope * possible_cut
        return Rescale(slope, shift, cap=1.0, has_possible=True, has_probable=True)
    if probable_cut is not None:
        shift = _logit(PROBABLE_SCORE) - probable_cut
        return Rescale(1.0, shift, cap=1.0, has_possible=False, has_probable=True)
    if possible_cut is not None:
        shift = _logit(POSSIBLE_SCORE) - possible_cut
        return Rescale(1.0, shift, cap=BELOW_PROBABLE, has_possible=True, has_probable=False)
    return None


def review_rescale(review_cut: float) -> Rescale:
    """A review-only probe shows no level: its score is 0.5 at the cut that sends an item to
    the review, with the slope of its own logit and no ceiling, since nobody reads it as a level."""
    shift = _logit(POSSIBLE_SCORE) - review_cut
    return Rescale(1.0, shift, cap=1.0, has_possible=False, has_probable=False)


def sigmoid(logits: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(logits, -_LOGIT_BOUND, _LOGIT_BOUND)))

"""Reads vectors with the loaded probes: the scores, the flags they amount to, the review calls."""

import math
from dataclasses import dataclass

import numpy as np

from backend.probes.schema import (
    POSSIBLE_SCORE,
    PROBABLE_SCORE,
    FlagLevel,
    LevelMeasure,
    ProbeInfo,
    ProbeReading,
)
from backend.probes.uniform import sigmoid
from backend.workspace.schema import ReviewMode

_DECIMALS = 10_000
# Rows scored at once. In one piece, the temporaries of a large map are hundreds of megabytes
# each: measured on the server, 500,000 rows by 50 probes took 4 s and more that way, and
# 0.5 s in blocks of this size.
_BLOCK = 50_000


def _cut_to_decimals(score: float) -> float:
    """Four decimals, cut and never rounded up: a score written under a level is under it."""
    return math.floor(score * _DECIMALS) / _DECIMALS


def _flag(info: ProbeInfo, score: float) -> tuple[FlagLevel, LevelMeasure] | None:
    """The level the score reaches among the levels this probe has, with that level's measure."""
    if info.probable is not None and score >= PROBABLE_SCORE:
        return "probable", info.probable
    if info.possible is not None and score >= POSSIBLE_SCORE:
        return "possible", info.possible
    return None


def _at_review_cut(info: ProbeInfo) -> bool:
    """A review-only probe without a level: it is read at its review cut, which scores 0.5."""
    return info.state == "review-only" and info.possible is None and info.probable is None


@dataclass(frozen=True, eq=False)
class Probes:
    """Every probe of the pack, shown or review-only, in pack order.

    The arrays are folded once at load, so scoring is one matrix product:
    `score = min(sigmoid(vectors @ weights.T + bias), caps)`.
    """

    infos: tuple[ProbeInfo, ...]
    weights: np.ndarray  # (len(infos), dims) float32
    bias: np.ndarray  # (len(infos),) float32
    caps: np.ndarray  # (len(infos),) float32
    # Which probes may send an item to the review, one per probe. Empty: all of them.
    reviewable: tuple[bool, ...] = ()

    def shown(self) -> tuple[ProbeInfo, ...]:
        return tuple(info for info in self.infos if info.state == "shown")

    def scores(self, vectors: np.ndarray) -> np.ndarray:
        """One row per vector and one column per probe, float32 in [0, 1]."""
        rows = np.atleast_2d(vectors)
        scores = np.zeros((len(rows), len(self.infos)), dtype=np.float32)
        if not self.infos:
            return scores
        for start in range(0, len(rows), _BLOCK):
            block = rows[start : start + _BLOCK].astype(np.float32, copy=False)
            logits = block @ self.weights.T + self.bias
            scores[start : start + _BLOCK] = np.minimum(sigmoid(logits), self.caps)
        return scores

    def column(self, key: str) -> int:
        for column, info in enumerate(self.infos):
            if info.key == key:
                return column
        raise KeyError(key)

    def _flags(self, row: np.ndarray) -> list[tuple[ProbeInfo, float, FlagLevel, LevelMeasure]]:
        """The probes whose score reaches one of their levels, strongest first."""
        found = []
        for info, score in zip(self.infos, row.tolist(), strict=True):
            flag = _flag(info, score)
            if flag is not None:
                found.append((info, score, *flag))
        return sorted(found, key=lambda entry: -entry[1])

    def readings(self, row: np.ndarray) -> list[ProbeReading]:
        """The shown probes that flag this row of scores, strongest first."""
        return [
            ProbeReading(
                key=info.key,
                label=info.label,
                score=_cut_to_decimals(score),
                level=level,
                reliability=measure,
                report=info.report,
            )
            for info, score, level, measure in self._flags(row)
            if info.state == "shown"
        ]

    def score_map(self, row: np.ndarray) -> dict[str, float]:
        """The score of every shown probe, flagged or not. A point a probe did not read (NaN)
        has no entry."""
        return {
            info.key: _cut_to_decimals(score)
            for info, score in zip(self.infos, row.tolist(), strict=True)
            if info.state == "shown" and not math.isnan(score)
        }

    def triggers(self, row: np.ndarray, mode: ReviewMode, min_score: float) -> list[ProbeInfo]:
        """The probes, shown or review-only, that send this item to the review, strongest first.
        A review-only probe read at its review cut sends it from 0.5, whatever level is asked.
        A probe that only describes a post (its theme, its language) never sends it."""
        if mode == "off":
            return []
        hits = []
        allowed = self.reviewable or (True,) * len(self.infos)
        for info, score, may in zip(self.infos, row.tolist(), allowed, strict=True):
            if not may:
                continue
            if mode == "score":
                hit = score >= min_score
            elif _at_review_cut(info):
                hit = score >= POSSIBLE_SCORE
            else:
                flag = _flag(info, score)
                hit = flag is not None and (mode == "possible" or flag[0] == "probable")
            if hit:
                hits.append((info, score))
        return [info for info, _ in sorted(hits, key=lambda hit: -hit[1])]

    def flags(self, scores: np.ndarray) -> np.ndarray:
        """Where each probe flags: one row per item, one column per probe, true from the lowest
        level the probe has (or from its review cut)."""
        floors = [
            POSSIBLE_SCORE if info.possible is not None or _at_review_cut(info) else PROBABLE_SCORE
            for info in self.infos
        ]
        return scores >= np.asarray(floors, dtype=np.float32)


EMPTY = Probes(
    infos=(),
    weights=np.zeros((0, 0), dtype=np.float32),
    bias=np.zeros(0, dtype=np.float32),
    caps=np.zeros(0, dtype=np.float32),
)

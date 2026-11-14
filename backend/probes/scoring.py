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

    def shown(self) -> tuple[ProbeInfo, ...]:
        return tuple(info for info in self.infos if info.state == "shown")

    def scores(self, vectors: np.ndarray) -> np.ndarray:
        """One row per vector and one column per probe, float32 in [0, 1]."""
        rows = np.atleast_2d(vectors)
        if not self.infos:
            return np.zeros((len(rows), 0), dtype=np.float32)
        logits = rows.astype(np.float32, copy=False) @ self.weights.T + self.bias
        return np.minimum(sigmoid(logits), self.caps)

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
        """The probes, shown or review-only, that send this item to the review, strongest first."""
        if mode == "off":
            return []
        if mode == "score":
            scored = zip(self.infos, row.tolist(), strict=True)
            hits = [(info, score) for info, score in scored if score >= min_score]
            return [info for info, _ in sorted(hits, key=lambda hit: -hit[1])]
        return [
            info
            for info, _, level, _ in self._flags(row)
            if mode == "possible" or level == "probable"
        ]


EMPTY = Probes(
    infos=(),
    weights=np.zeros((0, 0), dtype=np.float32),
    bias=np.zeros(0, dtype=np.float32),
    caps=np.zeros(0, dtype=np.float32),
)

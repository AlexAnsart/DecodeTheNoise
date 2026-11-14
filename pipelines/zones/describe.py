"""Turns cluster labels into zones: ranked by size, each with its distinctive words. Pure."""

import numpy as np

from backend.map.schema import ZoneInfo
from pipelines.zones.words import distinctive_words

NAME_WORDS = 3


def by_size(labels: np.ndarray) -> np.ndarray:
    """Relabels so that zone 0 is the largest: the id is the rank the legend shows."""
    sizes = np.bincount(labels)
    order = np.lexsort((np.arange(len(sizes)), -sizes))
    rank = np.empty(len(sizes), dtype=np.int64)
    rank[order] = np.arange(len(sizes))
    return rank[labels]


def describe(zone_of_point: np.ndarray, texts: list[str]) -> list[ZoneInfo]:
    count = int(zone_of_point.max()) + 1
    grouped: list[list[str]] = [[] for _ in range(count)]
    for zone, text in zip(zone_of_point.tolist(), texts, strict=True):
        grouped[zone].append(text)
    words = distinctive_words(grouped)
    return [
        ZoneInfo(
            id=zone,
            # Its words stand in for a name until the LLM pass gives it one.
            name=" · ".join(words[zone][:NAME_WORDS]),
            words=words[zone],
            size=len(grouped[zone]),
            named=False,
        )
        for zone in range(count)
    ]

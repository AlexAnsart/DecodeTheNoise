"""Clusters a workspace into zones, and carries the names of the zones that are still there.

The clustering is the offline one (spherical k-means, distinctive words). A zone whose centre
barely moved since the last refresh keeps its name, so only new subjects are named again.
"""

import math
from dataclasses import dataclass

import numpy as np

from backend.map.schema import ZoneInfo
from pipelines.zones.describe import by_size, describe
from pipelines.zones.kmeans import spherical_kmeans

SEED = 42
MIN_ZONES = 3
MAX_ZONES = 24
# Cosine between the old centre and the new one above which a zone is the same subject.
SAME_ZONE = 0.9


@dataclass(frozen=True)
class Zoning:
    zone: np.ndarray  # uint16 per point
    centres: np.ndarray  # one unit vector per zone
    zones: tuple[ZoneInfo, ...]


def zone_count(n: int) -> int:
    """About sqrt(n) / 2: a handful of zones on a hundred posts, two dozen on thousands."""
    return max(MIN_ZONES, min(MAX_ZONES, round(math.sqrt(n) / 2)))


def _centres(vectors: np.ndarray, labels: np.ndarray, count: int) -> np.ndarray:
    centres = np.stack([vectors[labels == zone].mean(axis=0) for zone in range(count)])
    return centres / np.maximum(np.linalg.norm(centres, axis=1, keepdims=True), 1e-12)


def carry_names(
    zones: list[ZoneInfo],
    centres: np.ndarray,
    previous: tuple[ZoneInfo, ...],
    previous_centres: np.ndarray | None,
) -> list[ZoneInfo]:
    """Each new zone takes the name of the previous zone it continues, one to one, best
    matches first."""
    if previous_centres is None or not previous:
        return zones
    likeness = centres @ previous_centres.T
    taken_new: set[int] = set()
    taken_old: set[int] = set()
    out = list(zones)
    for flat in np.argsort(-likeness, axis=None):
        new, old = divmod(int(flat), likeness.shape[1])
        if likeness[new, old] < SAME_ZONE:
            break
        if new in taken_new or old in taken_old or not previous[old].named:
            continue
        taken_new.add(new)
        taken_old.add(old)
        out[new] = out[new].model_copy(update={"name": previous[old].name, "named": True})
    return out


def make_zones(
    vectors: np.ndarray,
    texts: list[str],
    previous: tuple[ZoneInfo, ...],
    previous_centres: np.ndarray | None,
) -> Zoning:
    try:
        labels = by_size(spherical_kmeans(vectors, zone_count(len(vectors)), SEED))
    except ValueError:
        # Fewer distinct texts than zones asked for: one zone holds everything.
        labels = np.zeros(len(vectors), dtype=np.int64)
    zones = describe(labels, texts)
    centres = _centres(vectors, labels, len(zones))
    named = carry_names(zones, centres, previous, previous_centres)
    return Zoning(labels.astype(np.uint16), centres, tuple(named))

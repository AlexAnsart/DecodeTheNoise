"""Spherical k-means: clusters unit vectors by cosine. Pure and seeded."""

import math

import numpy as np

MIN_ZONES = 12
MAX_ZONES = 48
MAX_ITERATIONS = 50


def zone_count(n: int) -> int:
    """About sqrt(n) / 4: enough zones to name subjects, few enough to read in a legend."""
    return max(MIN_ZONES, min(MAX_ZONES, round(math.sqrt(n) / 4)))


def _seed_centres(vectors: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """k-means++ on cosine distance: each new centre is drawn far from the ones chosen."""
    centres = [vectors[rng.integers(len(vectors))]]
    distance = 1.0 - vectors @ centres[0]
    for _ in range(1, k):
        weights = np.maximum(distance, 0.0) ** 2
        chosen = vectors[rng.choice(len(vectors), p=weights / weights.sum())]
        centres.append(chosen)
        distance = np.minimum(distance, 1.0 - vectors @ chosen)
    return np.stack(centres)


def spherical_kmeans(vectors: np.ndarray, k: int, seed: int) -> np.ndarray:
    """One label in [0, k) per row. Rows of `vectors` are unit length."""
    rng = np.random.default_rng(seed)
    centres = _seed_centres(vectors, k, rng)
    labels = np.full(len(vectors), -1, dtype=np.int64)
    for _ in range(MAX_ITERATIONS):
        scores = vectors @ centres.T
        assigned = scores.argmax(axis=1)
        if np.array_equal(assigned, labels):
            break
        labels = assigned
        for zone in range(k):
            members = vectors[labels == zone]
            if len(members) == 0:
                # An emptied cluster restarts on the point its own centre explains worst.
                members = vectors[[scores.max(axis=1).argmin()]]
            mean = members.mean(axis=0)
            centres[zone] = mean / max(float(np.linalg.norm(mean)), 1e-12)
    return labels

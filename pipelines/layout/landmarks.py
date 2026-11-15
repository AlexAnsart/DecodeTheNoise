"""Lays out a large build from a layout of some of its points, the landmarks.

UMAP is run on the landmarks only. Every other point is set down among the landmarks it
resembles most in the full vector space, with the weights the paste box uses for a new text.
The picture has the shape UMAP gave the landmarks, with the other points filling it in.
"""

from concurrent.futures import ThreadPoolExecutor

import numpy as np

from backend.analyze.place import neighbour_weights

NEAREST = 10
# Rows scored at once, and how many groups of rows at a time: bounds the memory at
# WORKERS * BLOCK * landmarks scores, whatever the size of the build.
BLOCK = 256
WORKERS = 4


def _place_block(rows: np.ndarray, anchors: np.ndarray, layout: np.ndarray) -> np.ndarray:
    scores = rows @ anchors.T
    count = min(NEAREST, scores.shape[1])
    top = np.argpartition(-scores, count - 1, axis=1)[:, :count]
    best = np.take_along_axis(scores, top, axis=1)
    order = np.argsort(-best, axis=1)
    top, best = np.take_along_axis(top, order, axis=1), np.take_along_axis(best, order, axis=1)
    weights = neighbour_weights(best)
    return np.einsum("ij,ijk->ik", weights, layout[top])


def place_from_landmarks(
    vectors: np.ndarray, landmarks: np.ndarray, layout: np.ndarray
) -> np.ndarray:
    """Coordinates of every point. `landmarks` are the indices of the points `layout` places,
    one row each; they keep the place the layout gave them."""
    anchors = vectors[landmarks]
    starts = range(0, len(vectors), BLOCK)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        blocks = pool.map(
            lambda start: _place_block(vectors[start : start + BLOCK], anchors, layout), starts
        )
        placed = np.concatenate(list(blocks)).astype(np.float32)
    placed[landmarks] = layout
    return placed

"""The nearest neighbours of every point, kept exact while points arrive one by one. Pure."""

import numpy as np

from backend.map.schema import NO_NEIGHBOUR

K = 10
# Rows scored at once when every list is computed again.
_BLOCK = 2048


class NeighbourLists:
    """For each point, its `k` most similar points, most similar first."""

    def __init__(self, capacity: int, k: int = K) -> None:
        self.k = k
        self.index = np.full((capacity, k), NO_NEIGHBOUR, dtype=np.uint32)
        self.score = np.full((capacity, k), -np.inf, dtype=np.float32)

    def grow(self, capacity: int) -> None:
        index = np.full((capacity, self.k), NO_NEIGHBOUR, dtype=np.uint32)
        score = np.full((capacity, self.k), -np.inf, dtype=np.float32)
        index[: len(self.index)] = self.index
        score[: len(self.score)] = self.score
        self.index, self.score = index, score

    def add(self, point: int, scores: np.ndarray) -> None:
        """Adds point number `point`; `scores[j]` is its cosine to each earlier point j."""
        count = min(self.k, point)
        if count:
            top = np.argpartition(-scores, count - 1)[:count]
            order = top[np.argsort(-scores[top], kind="stable")]
            self.index[point, :count] = order
            self.score[point, :count] = scores[order]
        # It also enters the list of every point it is closer to than their last neighbour.
        for other in np.flatnonzero(scores > self.score[:point, -1]):
            held, ids = self.score[other], self.index[other]
            at = int(np.searchsorted(-held, -scores[other]))
            held[at + 1 :] = held[at:-1].copy()
            ids[at + 1 :] = ids[at:-1].copy()
            held[at], ids[at] = scores[other], point

    def rebuild(self, vectors: np.ndarray) -> None:
        """Every list again from the vectors: needed when a point's vector was replaced."""
        n = len(vectors)
        count = min(self.k, n - 1)
        self.index[:n] = NO_NEIGHBOUR
        self.score[:n] = -np.inf
        if count < 1:
            return
        for start in range(0, n, _BLOCK):
            scores = vectors[start : start + _BLOCK] @ vectors.T
            rows = np.arange(len(scores))
            scores[rows, start + rows] = -np.inf
            top = np.argpartition(-scores, count - 1, axis=1)[:, :count]
            order = np.argsort(-np.take_along_axis(scores, top, axis=1), axis=1)
            chosen = np.take_along_axis(top, order, axis=1)
            self.index[start : start + len(scores), :count] = chosen
            self.score[start : start + len(scores), :count] = np.take_along_axis(
                scores, chosen, axis=1
            )

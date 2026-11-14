"""Similarity by meaning: the cosine of every point to a text, or to a set of points."""

from collections import OrderedDict
from threading import Lock

import numpy as np

from backend.map.store import MapBuild
from backend.model_client.embedding import EmbeddingClient

_CACHE_SIZE = 256


class QueryEmbedder:
    """Embeds short query texts with the build's model, cached on the text."""

    def __init__(self, client: EmbeddingClient) -> None:
        self._client = client
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._lock = Lock()

    @property
    def key(self) -> str:
        return str(self._client.key)

    def embed(self, text: str) -> np.ndarray:
        with self._lock:
            hit = self._cache.get(text)
            if hit is not None:
                self._cache.move_to_end(text)
                return hit
        vector = self._client.embed([text])[0]
        with self._lock:
            self._cache[text] = vector
            if len(self._cache) > _CACHE_SIZE:
                self._cache.popitem(last=False)
        return vector


def scores_to_vector(build: MapBuild, vector: np.ndarray) -> np.ndarray:
    return (build.vectors @ vector).astype(np.float32)


def scores_to_items(build: MapBuild, indices: list[int]) -> np.ndarray:
    """Cosine to the mean direction of the given points."""
    mean = build.vectors[np.asarray(indices, dtype=np.int64)].mean(axis=0)
    norm = float(np.linalg.norm(mean))
    return scores_to_vector(build, mean / max(norm, 1e-12))

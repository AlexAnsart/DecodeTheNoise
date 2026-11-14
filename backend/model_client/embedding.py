"""The one embedding client: an OpenAI-compatible `/embeddings` route, local or hosted.

The same weights embed the corpus offline and a pasted text online, so the key below travels
with every vector and every probe.
"""

from dataclasses import dataclass

import httpx
import numpy as np
from pydantic import BaseModel


@dataclass(frozen=True)
class EmbeddingKey:
    """What makes two vectors comparable. Change one field and the corpus is embedded again."""

    model: str
    revision: str
    prefix: str
    dims: int

    def __str__(self) -> str:
        return f"{self.model}@{self.revision}|prefix={self.prefix!r}|dims={self.dims}"


class _EmbeddingRow(BaseModel):
    index: int
    embedding: list[float]


class _EmbeddingResponse(BaseModel):
    data: list[_EmbeddingRow]


def fit_vectors(raw: np.ndarray, dims: int) -> np.ndarray:
    """Keeps the first `dims` values of each row and renormalises to unit length."""
    cut = raw[:, :dims].astype(np.float32)
    norms = np.linalg.norm(cut, axis=1, keepdims=True)
    return cut / np.maximum(norms, 1e-12)


class EmbeddingClient:
    def __init__(
        self, base_url: str, api_key: str, key: EmbeddingKey, timeout: float = 120.0
    ) -> None:
        self.key = key
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def embed(self, texts: list[str]) -> np.ndarray:
        """One unit vector of `key.dims` values per text, in order."""
        response = self._http.post(
            "/embeddings",
            json={"model": self.key.model, "input": [self.key.prefix + text for text in texts]},
        )
        response.raise_for_status()
        rows = sorted(
            _EmbeddingResponse.model_validate(response.json()).data, key=lambda r: r.index
        )
        return fit_vectors(
            np.asarray([row.embedding for row in rows], dtype=np.float32), self.key.dims
        )

    def close(self) -> None:
        self._http.close()

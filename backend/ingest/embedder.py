"""Embeds the texts of items with the model of the server, each distinct text only once.

One model call per chunk of texts that are not in the cache. The cache is on a hash of the
embedding key and the text, kept in a file, so a text sent twice, by anyone, costs one lookup.
The speed of the model is measured on every call: it is what the time left of a batch is
estimated from.
"""

import hashlib
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

# Texts per model call. The model takes one call at a time: a search or a single post sent
# meanwhile waits for the chunk in flight, so a chunk is kept to about a second of work.
CHUNK = 8
# Weight of the latest call in the measured speed: a slow moment shows, one odd call does not.
_FRESH = 0.3


class EmbeddingModel(Protocol):
    @property
    def key(self) -> object: ...

    def embed(self, texts: list[str]) -> np.ndarray: ...


@dataclass(frozen=True)
class Embedded:
    """Vectors in the order asked, and what they cost."""

    vectors: np.ndarray
    # Texts answered by the cache, or by another copy of the same text in the request.
    cached: int
    # Texts sent to the model, and the seconds it took for them.
    computed: int
    seconds: float


class ItemEmbedder:
    def __init__(self, model: EmbeddingModel, cache_path: Path | None) -> None:
        self._model = model
        self.key = str(model.key)
        # Texts a second the model gave on this server lately; None until it was called.
        self.rate: float | None = None
        self._model_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        self._cache: sqlite3.Connection | None = None
        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache = sqlite3.connect(cache_path, check_same_thread=False)
            with self._cache:
                self._cache.execute(
                    "CREATE TABLE IF NOT EXISTS vectors("
                    "hash TEXT PRIMARY KEY, vector BLOB NOT NULL)"
                )

    def _hash(self, text: str) -> str:
        return hashlib.sha256(f"{self.key}\n{text}".encode()).hexdigest()

    def _cached(self, hashes: list[str]) -> dict[str, np.ndarray]:
        if self._cache is None or not hashes:
            return {}
        found: dict[str, np.ndarray] = {}
        with self._cache_lock:
            for start in range(0, len(hashes), 500):
                part = hashes[start : start + 500]
                marks = ",".join("?" * len(part))
                rows = self._cache.execute(
                    f"SELECT hash, vector FROM vectors WHERE hash IN ({marks})", part
                ).fetchall()
                for digest, blob in rows:
                    found[digest] = np.frombuffer(blob, dtype=np.float16).astype(np.float32)
        return found

    def _remember(self, hashes: list[str], vectors: np.ndarray) -> None:
        if self._cache is None:
            return
        rows = [
            (digest, vector.astype(np.float16).tobytes())
            for digest, vector in zip(hashes, vectors, strict=True)
        ]
        with self._cache_lock, self._cache:
            self._cache.executemany("INSERT OR REPLACE INTO vectors VALUES (?, ?)", rows)

    def _compute(self, texts: list[str]) -> tuple[np.ndarray, float]:
        """One model call, timed without the wait for the call before it."""
        with self._model_lock:
            started = time.monotonic()
            vectors = self._model.embed(texts)
            seconds = max(time.monotonic() - started, 1e-6)
            speed = len(texts) / seconds
            self.rate = speed if self.rate is None else (1 - _FRESH) * self.rate + _FRESH * speed
        return vectors, seconds

    def embed_counted(self, texts: list[str]) -> Embedded:
        """One unit vector per text, in order. Raises `httpx.HTTPError` when the model fails."""
        hashes = [self._hash(text) for text in texts]
        known = self._cached(hashes)
        missing = [i for i, digest in enumerate(hashes) if digest not in known]
        # A text repeated inside the request is sent to the model once.
        first = {hashes[i]: i for i in reversed(missing)}
        todo = sorted(first.values())
        spent = 0.0
        for start in range(0, len(todo), CHUNK):
            part = todo[start : start + CHUNK]
            vectors, seconds = self._compute([texts[i] for i in part])
            spent += seconds
            part_hashes = [hashes[i] for i in part]
            self._remember(part_hashes, vectors)
            known.update(zip(part_hashes, vectors, strict=True))
        stacked = np.stack([known[digest] for digest in hashes]) if texts else np.zeros((0, 0))
        return Embedded(stacked, cached=len(texts) - len(todo), computed=len(todo), seconds=spent)

    def embed(self, texts: list[str]) -> np.ndarray:
        return self.embed_counted(texts).vectors

    def close(self) -> None:
        if self._cache is not None:
            self._cache.close()

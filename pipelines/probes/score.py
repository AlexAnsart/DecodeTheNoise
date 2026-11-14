"""Scores posts of the pool with the probes of a run: standardise, one dot product, a bias."""

from dataclasses import dataclass

import numpy as np

from pipelines.probes.dataset import build_vectors
from pipelines.probes.pool import SPLITS, Pool
from pipelines.probes.train import RUNS

CHUNK = 100_000


@dataclass(frozen=True)
class Probes:
    names: tuple[str, ...]
    weights: np.ndarray  # one row per probe
    bias: np.ndarray
    mean: np.ndarray
    scale: np.ndarray

    def logits(self, vectors: np.ndarray) -> np.ndarray:
        """One column per probe."""
        z = (vectors.astype(np.float32) - self.mean) / self.scale
        return z @ self.weights.T + self.bias


def load_probes(run: str) -> Probes:
    with np.load(RUNS / run / "probes.npz") as data:
        names = tuple(str(name) for name in data["names"])
        return Probes(names, data["weights"], data["bias"], data["mean"], data["scale"])


def pool_vectors(pool: Pool, rows: np.ndarray) -> np.ndarray:
    """Vectors of the given pool rows, in that order."""
    out = np.empty((len(rows), build_vectors(pool.builds[0])[0].shape[1]), dtype=np.float32)
    for number, build in enumerate(pool.builds):
        here = np.flatnonzero(pool.shard[rows] == number)
        if len(here):
            # Sorted reads keep the memory map sequential.
            order = np.argsort(pool.idx[rows[here]])
            table = build_vectors(build)[0]
            out[here[order]] = table[pool.idx[rows[here[order]]]]
    return out


def split_rows(pool: Pool, split: str) -> np.ndarray:
    return np.flatnonzero(pool.keep & (pool.split == SPLITS.index(split)))


def score_rows(probes: Probes, pool: Pool, rows: np.ndarray) -> np.ndarray:
    """Logits of every probe for the given pool rows, computed chunk by chunk."""
    out = np.empty((len(rows), len(probes.names)), dtype=np.float32)
    for start in range(0, len(rows), CHUNK):
        chunk = rows[start : start + CHUNK]
        out[start : start + CHUNK] = probes.logits(pool_vectors(pool, chunk))
    return out

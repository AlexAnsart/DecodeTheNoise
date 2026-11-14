"""Reads the served vectors of one build (written by the embed step)."""

import json
from pathlib import Path

import numpy as np

from pipelines.paths import VECTORS_FILE, VECTORS_META


def write_vectors(work: Path, vectors: np.ndarray, key: str, native_dims: int) -> None:
    """Stores unit vectors as float16, with the key and sizes needed to read them back."""
    vectors.astype(np.float16).tofile(work / VECTORS_FILE)
    meta = {
        "key": key,
        "dims": int(vectors.shape[1]),
        "native_dims": native_dims,
        "n": len(vectors),
    }
    (work / VECTORS_META).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def read_vectors(work: Path) -> tuple[np.ndarray, str]:
    """Unit vectors as float32, one row per point, and the embedding key they were made with."""
    meta = json.loads((work / VECTORS_META).read_text(encoding="utf-8"))
    raw = np.fromfile(work / VECTORS_FILE, dtype=np.float16)
    return raw.reshape(int(meta["n"]), int(meta["dims"])).astype(np.float32), str(meta["key"])

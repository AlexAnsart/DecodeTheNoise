"""Loads a map build once at start-up: manifest, vectors in memory, item database handle."""

import logging
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backend.map.schema import BUFFERS_FILE, ITEMS_FILE, MANIFEST_FILE, VECTORS_FILE, MapManifest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MapBuild:
    folder: Path
    manifest: MapManifest
    vectors: np.ndarray  # (n, dims) float32, unit rows
    items: sqlite3.Connection
    items_lock: threading.Lock

    @property
    def buffers_path(self) -> Path:
        return self.folder / BUFFERS_FILE


def load_build(folder: Path) -> MapBuild | None:
    """Returns None when no build is there yet, so the server can start before the first data."""
    manifest_path = folder / MANIFEST_FILE
    if not manifest_path.is_file():
        logger.warning("no map build at %s", folder)
        return None
    manifest = MapManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    stored = np.fromfile(folder / VECTORS_FILE, dtype=np.float16)
    vectors = stored.reshape(manifest.n, manifest.dims).astype(np.float32)
    # Read-only and shared by the worker threads; the lock serialises the queries.
    items = sqlite3.connect(
        f"file:{(folder / ITEMS_FILE).as_posix()}?mode=ro", uri=True, check_same_thread=False
    )
    logger.info("loaded build %s: %d points, %d dims", manifest.build, manifest.n, manifest.dims)
    return MapBuild(
        folder=folder,
        manifest=manifest,
        vectors=vectors,
        items=items,
        items_lock=threading.Lock(),
    )

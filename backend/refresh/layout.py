"""Lays a workspace out in 3D and in 2D: the same method as the offline build (UMAP on the
cosine), started from the previous layout so that the picture a user knows does not flip.

Measured on the laptop, one layout: 0.6 s for 200 points, 3.5 s for 1,000, 11 s for 3,000.
The functions here run in the computing process (`backend/refresh/computing.py`), never in
the API process.
"""

import logging
import time

import numpy as np

from pipelines.layout.pca import principal_axes
from pipelines.layout.scale import EXTENT, scale_layout

logger = logging.getLogger(__name__)

SEED = 42
N_NEIGHBORS = 15
MIN_DIST = 0.1
# UMAP works in a frame of about ten units; the stored layout spans a hundred.
_UMAP_EXTENT = 10.0
# With a layout to start from, far fewer passes are needed than from scratch.
_EPOCHS_FROM_PREVIOUS = 200
# What UMAP and the libraries under it raise on degenerate input (identical points, a graph in
# pieces): the layout then falls back on the principal axes.
_UMAP_ERRORS = (ValueError, TypeError, ArithmeticError, RuntimeError, np.linalg.LinAlgError)


def on_axes(vectors: np.ndarray, components: int) -> np.ndarray:
    """The vectors on their principal axes: no compilation, a fraction of a second."""
    with np.errstate(invalid="ignore", divide="ignore"):
        coordinates, _ = principal_axes(vectors, 3)
    return scale_layout(coordinates[:, :components])


def _umap(vectors: np.ndarray, components: int, previous: np.ndarray | None) -> np.ndarray:
    # Imported when first needed: numba compiles on import.
    import umap

    start = "spectral" if previous is None else previous * (_UMAP_EXTENT / EXTENT)
    reducer = umap.UMAP(
        n_components=components,
        n_neighbors=min(N_NEIGHBORS, len(vectors) - 1),
        min_dist=MIN_DIST,
        metric="cosine",
        random_state=SEED,
        # A fixed seed runs on one core; said here so the library does not warn about it.
        n_jobs=1,
        # The pipeline the offline build was laid out with, kept when the library's default moves.
        compatibility_layout=True,
        init=start,
        n_epochs=None if previous is None else _EPOCHS_FROM_PREVIOUS,
    )
    return scale_layout(reducer.fit_transform(vectors))


def lay_out(vectors: np.ndarray, components: int, previous: np.ndarray | None) -> np.ndarray:
    """Coordinates of every vector in `components` dimensions. `previous` holds the current
    place of each point, when the workspace was laid out before."""
    try:
        return _umap(vectors, components, previous)
    except _UMAP_ERRORS:
        logger.exception("UMAP failed on %d points: laid out on the principal axes", len(vectors))
        return on_axes(vectors, components)


def warm_up() -> float:
    """Compiles the layout code once, on made-up points. Returns the seconds it took."""
    started = time.monotonic()
    rng = np.random.default_rng(SEED)
    points = rng.normal(size=(64, 16)).astype(np.float32)
    points /= np.linalg.norm(points, axis=1, keepdims=True)
    for components in (3, 2):
        lay_out(points, components, None)
    return time.monotonic() - started

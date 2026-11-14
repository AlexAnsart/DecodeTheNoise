"""Lays the vectors out in 3D and in 2D, with UMAP or on their principal axes (PCA).

Run: uv run --group pipelines python -m pipelines.layout --name ira-3k [--method pca]
"""

import argparse
import logging

import numpy as np
import umap

from pipelines import runlog
from pipelines.layout.pca import principal_axes
from pipelines.layout.scale import scale_layout
from pipelines.paths import LAYOUT_FILE, work_dir
from pipelines.vectors import read_vectors

log = logging.getLogger("layout")

SEED = 42
N_NEIGHBORS = 15
MIN_DIST = 0.1


def lay_out(vectors: np.ndarray, components: int) -> np.ndarray:
    # The 3D layout is its own optimisation, not the 2D one with an axis added.
    reducer = umap.UMAP(
        n_components=components,
        n_neighbors=N_NEIGHBORS,
        min_dist=MIN_DIST,
        metric="cosine",
        random_state=SEED,
    )
    return scale_layout(reducer.fit_transform(vectors))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--method", choices=("umap", "pca"), default="umap")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    work = work_dir(args.name)
    vectors, _ = read_vectors(work)
    with runlog.timed() as elapsed:
        if args.method == "pca":
            coordinates, kept = principal_axes(vectors, 3)
            pos3, pos2 = scale_layout(coordinates), scale_layout(coordinates[:, :2])
            shares = ", ".join(f"{share:.4f}" for share in kept)
            note = f"pca, share of the variance kept by each axis: {shares}"
        else:
            pos3, pos2 = lay_out(vectors, 3), lay_out(vectors, 2)
            note = "umap"
    np.savez(work / LAYOUT_FILE, pos3=pos3, pos2=pos2)
    runlog.record("layout", args.name, len(vectors), elapsed[0], note=note)
    log.info("laid out %d points in %.1fs (%s)", len(vectors), elapsed[0], note)


if __name__ == "__main__":
    main()

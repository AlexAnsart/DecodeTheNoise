"""Lays the vectors out in 3D and in 2D with UMAP.

Run: uv run --group pipelines python -m pipelines.layout --name ira-3k
"""

import argparse
import logging

import numpy as np
import umap

from pipelines import runlog
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
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    work = work_dir(args.name)
    vectors, _ = read_vectors(work)
    with runlog.timed() as elapsed:
        pos3 = lay_out(vectors, 3)
        pos2 = lay_out(vectors, 2)
    np.savez(work / LAYOUT_FILE, pos3=pos3, pos2=pos2)
    runlog.record("layout", args.name, len(vectors), elapsed[0])
    log.info("laid out %d points in %.1fs", len(vectors), elapsed[0])


if __name__ == "__main__":
    main()

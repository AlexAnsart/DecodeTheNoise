"""Finds the nearest neighbours of every point by cosine, exactly, in the full vector space.

Run: uv run python -m pipelines.neighbours --name ira-3k
"""

import argparse
import logging

import numpy as np

from pipelines import runlog
from pipelines.paths import NEIGHBOURS_FILE, work_dir
from pipelines.vectors import read_vectors

log = logging.getLogger("neighbours")

K = 10
# Rows scored at once: bounds memory at BLOCK * n floats whatever the corpus size.
BLOCK = 2048


def nearest(vectors: np.ndarray, k: int, block: int = BLOCK) -> np.ndarray:
    """Indices of the `k` most similar other points, most similar first. Vectors are unit length."""
    n = len(vectors)
    k = min(k, n - 1)
    out = np.empty((n, k), dtype=np.uint32)
    for start in range(0, n, block):
        scores = vectors[start : start + block] @ vectors.T
        rows = np.arange(len(scores))
        # A point is not its own neighbour.
        scores[rows, start + rows] = -np.inf
        top = np.argpartition(-scores, k - 1, axis=1)[:, :k]
        order = np.argsort(-np.take_along_axis(scores, top, axis=1), axis=1)
        out[start : start + block] = np.take_along_axis(top, order, axis=1)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    work = work_dir(args.name)
    vectors, _ = read_vectors(work)
    with runlog.timed() as elapsed:
        found = nearest(vectors, K)
    np.save(work / NEIGHBOURS_FILE, found)
    runlog.record("neighbours", args.name, len(vectors), elapsed[0])
    log.info(
        "%d neighbours for each of %d points in %.1fs", found.shape[1], len(vectors), elapsed[0]
    )


if __name__ == "__main__":
    main()

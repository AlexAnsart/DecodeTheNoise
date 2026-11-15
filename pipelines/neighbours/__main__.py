"""Finds the nearest neighbours of every point by cosine, exactly, in the full vector space.

Run: uv run python -m pipelines.neighbours --name ira-3k
"""

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from pipelines import runlog
from pipelines.paths import NEIGHBOURS_FILE, work_dir
from pipelines.vectors import read_vectors

log = logging.getLogger("neighbours")

K = 10
# Rows scored at once: bounds memory at BLOCK * n floats whatever the corpus size.
BLOCK = 2048
# A block of scores costs 16 bytes per pair of points (the scores, their opposite, the
# indices of the partial sort). On a large build the blocks are cut to fit this many bytes in
# all, and several are worked on at once: the partial sort is the slow part, and it runs on
# one core per block.
MEMORY = 2 * 1024**3
WORKERS = 6


def _block(vectors: np.ndarray, start: int, block: int, k: int) -> np.ndarray:
    scores = vectors[start : start + block] @ vectors.T
    rows = np.arange(len(scores))
    # A point is not its own neighbour.
    scores[rows, start + rows] = -np.inf
    top = np.argpartition(-scores, k - 1, axis=1)[:, :k]
    order = np.argsort(-np.take_along_axis(scores, top, axis=1), axis=1)
    return np.take_along_axis(top, order, axis=1)


def rows_at_once(n: int, workers: int = WORKERS) -> int:
    """Rows per block so that `workers` blocks of `n` scores stay within the memory set."""
    return max(1, min(BLOCK, MEMORY // (workers * n * 16)))


def nearest(vectors: np.ndarray, k: int, block: int = BLOCK, workers: int = 1) -> np.ndarray:
    """Indices of the `k` most similar other points, most similar first. Vectors are unit length."""
    n = len(vectors)
    k = min(k, n - 1)
    out = np.empty((n, k), dtype=np.uint32)
    starts = range(0, n, block)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        found = pool.map(lambda start: _block(vectors, start, block, k), starts)
        for start, rows in zip(starts, found, strict=True):
            out[start : start + block] = rows
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    work = work_dir(args.name)
    vectors, _ = read_vectors(work)
    with runlog.timed() as elapsed:
        found = nearest(vectors, K, rows_at_once(len(vectors)), WORKERS)
    np.save(work / NEIGHBOURS_FILE, found)
    runlog.record("neighbours", args.name, len(vectors), elapsed[0])
    log.info(
        "%d neighbours for each of %d points in %.1fs", found.shape[1], len(vectors), elapsed[0]
    )


if __name__ == "__main__":
    main()

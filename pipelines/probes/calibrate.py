"""Places the two thresholds of each probe on the calibration split.

The calibration posts are cut into bands by rank of score. The posts read in a band are the
random calibration sample that fell in it, plus, for a rare label, the posts drawn in that band
(`bands`). A threshold may only sit on a band edge: few candidates, so little is fitted to noise.
Each level takes the deepest edge whose measured precision meets its target. Test is not read.

Run: uv run --group pipelines python -m pipelines.probes.calibrate --run v1 --rounds m1 c1_calls
"""

import argparse
import json
import logging

import numpy as np

from pipelines.probes.bands import RANK_EDGES
from pipelines.probes.dataset import Labelled, load_labelled, vectors_for
from pipelines.probes.estimate import Band, estimate, make_bands
from pipelines.probes.pool import load_pool
from pipelines.probes.sample import RANDOM
from pipelines.probes.score import Probes, load_probes, score_rows, split_rows
from pipelines.probes.train import RUNS, Target, targets

log = logging.getLogger("probes.calibrate")

# The edges posts were drawn between (`bands`), then deeper ones that only the random sample fills.
EDGES = (*RANK_EDGES[1:], 60_000, 100_000, 150_000, 200_000, 250_000, 300_000, 350_000)
# Precision a level must reach on calibration, and the least it may plausibly be.
TARGETS = {"probable": 0.85, "possible": 0.65}
# A language probe gates abstention and splits every measure: one that is wrong one time in
# six is of no use, and the vector separates languages almost perfectly.
LANGUAGE_TARGETS = {"probable": 0.98, "possible": 0.95}
MARGIN = 0.15
MIN_READ = 20


def uniform_in_band(labelled: Labelled, target: Target) -> np.ndarray:
    """Posts of the target that are a uniform sample of their band: random, or drawn for it."""
    mark = f"band:{target.name}:"
    keep = [s == RANDOM or mark in s for s in (labelled.stratum[i] for i in target.rows)]
    return np.flatnonzero(keep)


def edges_of(split_scores: np.ndarray) -> list[float]:
    ordered = np.sort(split_scores)[::-1]
    return [float(ordered[rank - 1]) for rank in EDGES if rank <= len(ordered)]


def choose(bands: list[Band], wanted_by_level: dict[str, float]) -> dict[str, object]:
    """The deepest edge meeting each target, and the measures at every edge."""
    table = [{"threshold": band.low, **estimate(bands, band.low)} for band in bands[:-1]]
    levels: dict[str, float | None] = {}
    for level, wanted in wanted_by_level.items():
        ok = [
            row["threshold"]
            for row in table
            if row["precision"] is not None
            and row["read_flagged"] >= MIN_READ
            and row["precision"]["value"] >= wanted
            and row["precision"]["low"] >= wanted - MARGIN
        ]
        levels[level] = min(ok) if ok else None
    return {**levels, "edges": table}


def calibrate_target(
    probes: Probes, labelled: Labelled, target: Target, logits: np.ndarray, split: np.ndarray
) -> dict[str, object]:
    column = probes.names.index(target.name)
    used = uniform_in_band(labelled, target)
    bands = make_bands(
        split[:, column], edges_of(split[:, column]), logits[target.rows[used], column],
        target.y[used],
    )  # fmt: skip
    by_band = any(labelled.stratum[i] != RANDOM for i in target.rows[used])
    if not by_band:
        # Only the random sample was read: it is uniform over the whole split, so a band where
        # it has no post can be joined to the next one.
        bands = merge_unread(bands)
    out = {"read": len(used), "positives": int(target.y[used].sum()), "by_band": by_band}
    wanted = LANGUAGE_TARGETS if target.name.startswith("lang:") else TARGETS
    return {**out, **choose(bands, wanted)}


def merge_unread(bands: list[Band]) -> list[Band]:
    """Joins each band where nothing was read to the band just below it."""
    merged: list[Band] = []
    carry: Band | None = None
    for position, band in enumerate(bands):
        if carry is not None:
            band = Band(band.low, carry.high, band.size + carry.size, band.read, band.positive)
            carry = None
        if band.read == 0 and position < len(bands) - 1:
            carry = band
        else:
            merged.append(band)
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--rounds", nargs="+", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    pool = load_pool()
    probes = load_probes(args.run)
    labelled = load_labelled(tuple(args.rounds))
    logits = probes.logits(vectors_for(labelled.keys)[0])
    split = score_rows(probes, pool, split_rows(pool, "calibration"))
    out = {}
    for target in targets(labelled, "calibration"):
        if target.name not in probes.names:
            continue
        out[target.name] = calibrate_target(probes, labelled, target, logits, split)
        row = out[target.name]
        log.info("%-30s read=%d pos=%d possible=%s probable=%s", target.name, row["read"],
                 row["positives"], row["possible"], row["probable"])  # fmt: skip
    path = RUNS / args.run / "thresholds.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

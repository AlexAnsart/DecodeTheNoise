"""Fits one linear probe per target on the train split.

At runtime a probe is: standardise with the pool's mean and scale, one dot product, a bias.
The regularisation strength is chosen by cross-validation grouped by actor, inside train only;
calibration and test posts are never read here. Writes `data/probes/runs/<run>/`.

Run: uv run --group pipelines python -m pipelines.probes.train --run v0 --rounds m1
"""

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedGroupKFold

from pipelines.probes.dataset import Labelled, load_labelled, vectors_for
from pipelines.probes.pool import PROBES, SPLITS, Pool, load_pool
from pipelines.probes.taxonomy import LABELS, UNCLEAR, YES

log = logging.getLogger("probes.train")

RUNS = PROBES / "runs"
MOMENTS_FILE = PROBES / "moments.npz"
SEED = 20261114
C_GRID = (0.003, 0.01, 0.03, 0.1, 0.3)
FOLDS = 5
# Under this many positives in train, no probe is fitted: the target is reported as untrained.
MIN_POSITIVES = 25


@dataclass(frozen=True)
class Target:
    name: str  # a label, or "label:value" for a label with its own answers
    rows: np.ndarray  # posts of the labelled set with a settled answer
    y: np.ndarray


def pool_rows(pool: Pool, keys: tuple[str, ...] | list[str]) -> np.ndarray:
    """Row of each post in the pool: builds are stored one after the other, in row order."""
    sizes = np.bincount(pool.shard, minlength=len(pool.builds))
    offset = dict(zip(pool.builds, np.r_[0, np.cumsum(sizes)[:-1]], strict=True))
    pairs = (key.rsplit(":", 1) for key in keys)
    return np.array([offset[build] + int(idx) for build, idx in pairs], dtype=np.int64)


def moments(pool: Pool, n: int = 200_000) -> tuple[np.ndarray, np.ndarray]:
    """Mean and scale of the vectors, from random train posts: the same for every probe."""
    if MOMENTS_FILE.exists():
        with np.load(MOMENTS_FILE) as data:
            return data["mean"], data["scale"]
    rows = np.flatnonzero(pool.keep & (pool.split == SPLITS.index("train")))
    picked = np.sort(np.random.default_rng(SEED).choice(rows, size=n, replace=False))
    keys = [f"{pool.builds[pool.shard[r]]}:{pool.idx[r]}" for r in picked]
    vectors, _ = vectors_for(keys)
    mean, scale = vectors.mean(axis=0), vectors.std(axis=0)
    np.savez(MOMENTS_FILE, mean=mean, scale=scale)
    return mean, scale


def targets(labelled: Labelled, split: str) -> list[Target]:
    """Every yes/no question the labels define, on the posts of `split`."""
    out = []
    in_split = labelled.split == SPLITS.index(split)
    for label in LABELS:
        if label.name not in labelled.answers:
            continue
        values = labelled.answers[label.name]
        rows = np.flatnonzero(in_split & (values != "") & (values != UNCLEAR))
        if label.binary:
            out.append(Target(label.name, rows, (values[rows] == YES).astype(np.int8)))
        else:
            for value in label.values:
                y = (values[rows] == value).astype(np.int8)
                out.append(Target(f"{label.name}:{value}", rows, y))
    return out


def probe(strength: float) -> LogisticRegression:
    return LogisticRegression(C=strength, class_weight="balanced", max_iter=3000)


def out_of_fold(z: np.ndarray, y: np.ndarray, groups: np.ndarray, strength: float) -> np.ndarray:
    """The logit of each post from a probe that never saw its actor."""
    # A target with very few positives gets one per fold at most.
    n_splits = max(2, min(FOLDS, int(y.sum())))
    folds = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    scores = np.zeros(len(y), dtype=np.float64)
    for fit, held in folds.split(z, y, groups):
        scores[held] = probe(strength).fit(z[fit], y[fit]).decision_function(z[held])
    return scores


def fit_target(z: np.ndarray, y: np.ndarray, groups: np.ndarray) -> dict[str, object]:
    by_strength = {c: out_of_fold(z, y, groups, c) for c in C_GRID}
    ap = {c: float(average_precision_score(y, s)) for c, s in by_strength.items()}
    best = max(ap, key=ap.get)
    model = probe(best).fit(z, y)
    return {
        "c": best,
        "ap_by_c": ap,
        "oof": by_strength[best],
        "weights": model.coef_[0].astype(np.float32),
        "bias": float(model.intercept_[0]),
    }


def train(run: str, rounds: tuple[str, ...], min_positives: int = MIN_POSITIVES) -> Path:
    pool = load_pool()
    labelled = load_labelled(rounds)
    mean, scale = moments(pool)
    vectors, model_key = vectors_for(labelled.keys)
    z_all = (vectors - mean) / scale
    actors = pool.actor[pool_rows(pool, labelled.keys)]
    folder = RUNS / run
    folder.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {}
    weights, biases, names = [], [], []
    for target in targets(labelled, "train"):
        positives = int(target.y.sum())
        stats: dict[str, object] = {"n": len(target.y), "positives": positives}
        if positives >= min_positives and positives < len(target.y):
            fitted = fit_target(z_all[target.rows], target.y, actors[target.rows])
            stats.update(
                c=fitted["c"], ap_by_c=fitted["ap_by_c"], oof_ap=fitted["ap_by_c"][fitted["c"]]
            )
            np.save(folder / f"oof-{target.name.replace(':', '=')}.npy", fitted["oof"])
            weights.append(fitted["weights"])
            biases.append(fitted["bias"])
            names.append(target.name)
            log.info("%-32s n=%d pos=%d C=%g oof AP=%.3f", target.name, len(target.y), positives,
                     fitted["c"], stats["oof_ap"])  # fmt: skip
        report[target.name] = stats
    np.savez(folder / "probes.npz", names=np.array(names), weights=np.array(weights),
             bias=np.array(biases), mean=mean, scale=scale)  # fmt: skip
    config = {"run": run, "rounds": list(rounds), "model_key": model_key, "seed": SEED,
              "c_grid": list(C_GRID), "folds": FOLDS, "min_positives": min_positives}  # fmt: skip
    (folder / "train.json").write_text(json.dumps({"config": config, "targets": report}, indent=1))
    log.info("run %s: %d probes fitted of %d targets", run, len(names), len(report))
    return folder


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--rounds", nargs="+", required=True)
    parser.add_argument(
        "--min-positives",
        type=int,
        default=MIN_POSITIVES,
        help="lower it only for a search probe, never for one that is measured",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    train(args.run, tuple(args.rounds), args.min_positives)


if __name__ == "__main__":
    main()

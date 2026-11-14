"""Diagnostics of a run, on the train split only, every score out of fold and grouped by actor.

For each fitted probe: the learning curve (is more data the lever?), the linear probe against
k-NN and a small MLP (is the signal linear?), the first 64, 128 and 256 dimensions (is the
served size enough?), and similarity to the mean positive (the baseline a probe must beat).
Writes `data/probes/runs/<run>/diagnostics.json`.

Run: uv run --group pipelines python -m pipelines.probes.diagnose --run v1 --rounds m1 e1_calls
"""

import argparse
import json
import logging
from collections.abc import Callable

import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier

from pipelines.probes.dataset import load_labelled, vectors_for
from pipelines.probes.pool import load_pool
from pipelines.probes.train import FOLDS, RUNS, SEED, moments, pool_rows, probe, targets

log = logging.getLogger("probes.diagnose")

FRACTIONS = (0.25, 0.5, 1.0)
DIMS = (64, 128, 256)
# The slower comparisons run only where there are enough positives for five folds to mean much.
MIN_POSITIVES = 40


def folds(y: np.ndarray, groups: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    splitter = StratifiedGroupKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    return list(splitter.split(np.zeros(len(y)), y, groups))


def oof_ap(make: Callable[[], ClassifierMixin], x: np.ndarray, y: np.ndarray, cv: list) -> float:
    scores = np.zeros(len(y))
    for fit, held in cv:
        scores[held] = make().fit(x[fit], y[fit]).predict_proba(x[held])[:, 1]
    return float(average_precision_score(y, scores))


def centroid_ap(unit: np.ndarray, y: np.ndarray, cv: list) -> float:
    """Cosine to the mean positive of the other folds."""
    scores = np.zeros(len(y))
    for fit, held in cv:
        centre = unit[fit][y[fit] == 1].mean(axis=0)
        scores[held] = unit[held] @ (centre / np.linalg.norm(centre))
    return float(average_precision_score(y, scores))


def learning_curve(z: np.ndarray, y: np.ndarray, groups: np.ndarray, c: float) -> dict[str, float]:
    """Out-of-fold average precision when only a share of the train posts is used to fit."""
    rng = np.random.default_rng(SEED)
    order = rng.permutation(len(y))
    out = {}
    for fraction in FRACTIONS:
        scores = np.zeros(len(y))
        for fit, held in folds(y, groups):
            kept = np.intersect1d(fit, order[: int(len(y) * fraction) + 1])
            if y[kept].sum() < 2:
                return out
            scores[held] = probe(c).fit(z[kept], y[kept]).decision_function(z[held])
        out[str(fraction)] = float(average_precision_score(y, scores))
    return out


def truncated(unit: np.ndarray, dims: int) -> np.ndarray:
    """The first `dims` values, renormalised, then standardised on themselves."""
    cut = unit[:, :dims]
    cut = cut / np.linalg.norm(cut, axis=1, keepdims=True)
    return (cut - cut.mean(axis=0)) / cut.std(axis=0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--rounds", nargs="+", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    pool = load_pool()
    labelled = load_labelled(tuple(args.rounds))
    mean, scale = moments(pool)
    unit, _ = vectors_for(labelled.keys)
    z_all = (unit - mean) / scale
    actors = pool.actor[pool_rows(pool, labelled.keys)]
    trained = json.loads((RUNS / args.run / "train.json").read_text(encoding="utf-8"))["targets"]
    out: dict[str, object] = {}
    for target in targets(labelled, "train"):
        stats = trained.get(target.name, {})
        if "c" not in stats:
            continue
        rows, y, c = target.rows, target.y, stats["c"]
        cv = folds(y, actors[rows])
        row: dict[str, object] = {
            "positives": int(y.sum()),
            "chance": float(y.mean()),
            "linear": stats["oof_ap"],
            "centroid": centroid_ap(unit[rows], y, cv),
            "learning_curve": learning_curve(z_all[rows], y, actors[rows], c),
        }
        if y.sum() >= MIN_POSITIVES:
            row["knn"] = oof_ap(
                lambda: KNeighborsClassifier(n_neighbors=15, metric="cosine"), unit[rows], y, cv
            )
            row["mlp"] = oof_ap(
                lambda: MLPClassifier((64,), alpha=1e-2, max_iter=300, random_state=SEED),
                z_all[rows], y, cv,
            )  # fmt: skip
            row["dims"] = {
                str(d): oof_ap(lambda c=c: probe(c), truncated(unit[rows], d), y, cv) for d in DIMS
            }
        out[target.name] = row
        log.info("%-30s %s", target.name, {k: v for k, v in row.items() if k != "learning_curve"})
    path = RUNS / args.run / "diagnostics.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

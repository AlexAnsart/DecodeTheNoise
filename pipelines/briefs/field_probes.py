"""Test 1: can a linear probe read the fields of a brief from the posts it produced?

One probe per closed field, fitted on the posts of the development topics and scored on topics
it never saw. The reading of a group is the sum of the probe's log-probabilities over N of its
posts, so the result is a curve: accuracy against the number of posts read.

Two variants. `raw` scores the vectors as served. `topic_centred` first subtracts the mean
vector of the posts on the same subject, which needs a reference set of such posts.

Run: uv run --group pipelines python -m pipelines.briefs.field_probes
"""

import logging

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from pipelines.briefs.bench import LOOP_POSTS_FILE, POSTS_FILE, SEED, read_jsonl, write_result
from pipelines.briefs.fields import LEVELS
from pipelines.briefs.ncurve import interval, pooled_accuracy, rounded
from pipelines.briefs.vectors import embed

log = logging.getLogger("briefs.field_probes")

SIZES = (1, 2, 4, 8, 16, 32)
C_GRID = (0.001, 0.003, 0.01, 0.1)
FOLDS = 5
Rows = list[dict[str, object]]


def probe(strength: float) -> Pipeline:
    model = LogisticRegression(C=strength, max_iter=2000, class_weight="balanced")
    return make_pipeline(StandardScaler(), model)


def fit_probe(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> tuple[Pipeline, float]:
    """The regularisation is chosen on development groups held out in turn, never on test."""
    scores = {}
    for strength in C_GRID:
        guess = cross_val_predict(probe(strength), x, y, groups=groups, cv=GroupKFold(FOLDS))
        scores[strength] = float((guess == y).mean())
    best = max(scores, key=lambda c: scores[c])
    return probe(best).fit(x, y), best


def column(rows: Rows, name: str) -> np.ndarray:
    return np.array([row[name] for row in rows])


def labels(rows: Rows, name: str) -> np.ndarray:
    return np.array([LEVELS[name].index(str(row[name])) for row in rows])


def centred(vectors: np.ndarray, topics: np.ndarray) -> np.ndarray:
    """Each vector minus the mean vector of its topic: what is left is not about the subject."""
    out = vectors.copy()
    for topic in np.unique(topics):
        out[topics == topic] -= vectors[topics == topic].mean(axis=0)
    return out


def curve(
    model: Pipeline, name: str, rows: Rows, vectors: np.ndarray, rng: np.random.Generator
) -> dict[str, object]:
    """Accuracy of the pooled reading of a brief, for each number of posts read."""
    log_proba = model.predict_log_proba(vectors)
    truth, briefs = labels(rows, name), column(rows, "brief")
    guesses = log_proba.argmax(axis=1)
    # Where the errors are: each brief read from all its posts, grouped by its other fields.
    right: dict[str, dict[str, list[bool]]] = {}
    for brief in np.unique(briefs):
        members = np.flatnonzero(briefs == brief)
        hit = bool(log_proba[members].sum(axis=0).argmax() == truth[members[0]])
        for other in (*LEVELS, "topic"):
            if other != name:
                value = str(rows[members[0]][other])
                right.setdefault(other, {}).setdefault(value, []).append(hit)
    return {
        "all_posts_accuracy_by": {
            other: {
                value: {"briefs": len(hits), "accuracy": round(sum(hits) / len(hits), 2)}
                for value, hits in sorted(values.items())
            }
            for other, values in right.items()
        },
        "curve": {
            size: rounded(interval(shares, rng))
            for size in SIZES
            if len(shares := pooled_accuracy(log_proba, briefs, truth, size, rng))
        },
        "confusion_per_post": [
            [int(((truth == t) & (guesses == g)).sum()) for g in range(len(LEVELS[name]))]
            for t in range(len(LEVELS[name]))
        ],
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    rows = [row for row in read_jsonl(POSTS_FILE) if row["set"] == "bench"]
    dev = [row for row in rows if row["split"] == "dev"]
    sets = {"test": [row for row in rows if row["split"] == "test"]}
    if LOOP_POSTS_FILE.exists():
        sets["test_second_writer"] = list(read_jsonl(LOOP_POSTS_FILE))
    raw = {name: embed([str(row["text"]) for row in part])[0] for name, part in sets.items()}
    dev_raw, key = embed([str(row["text"]) for row in dev])
    variants = {
        "raw": (dev_raw, raw),
        "topic_centred": (
            centred(dev_raw, column(dev, "topic")),
            {name: centred(raw[name], column(part, "topic")) for name, part in sets.items()},
        ),
    }
    rng = np.random.default_rng(SEED)
    results: dict[str, dict[str, object]] = {}
    for variant, (x_dev, x_sets) in variants.items():
        results[variant] = {}
        for name, levels in LEVELS.items():
            model, strength = fit_probe(x_dev, labels(dev, name), column(dev, "topic"))
            scored = {part: curve(model, name, sets[part], x_sets[part], rng) for part in sets}
            results[variant][name] = {
                "levels": list(levels),
                "chance": round(1 / len(levels), 3),
                "regularisation": strength,
                **scored,
            }
            log.info("%s %s: %s", variant, name, scored["test"]["curve"])
    payload = {
        "embedding_key": key,
        "seed": SEED,
        "dev": {"posts": len(dev), "topics": len(set(column(dev, "topic")))},
        "sets": {
            name: {
                "posts": len(part),
                "briefs": len(set(column(part, "brief"))),
                "topics": len(set(column(part, "topic"))),
                "writer": str(part[0]["writer"]),
            }
            for name, part in sets.items()
        },
        "interval": "95%, bootstrap over briefs",
        "variants": results,
    }
    log.info("written: %s", write_result("field-probes", payload))


if __name__ == "__main__":
    main()

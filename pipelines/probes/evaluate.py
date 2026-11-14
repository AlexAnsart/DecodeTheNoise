"""Measures each probe once on the test split, at the thresholds frozen on calibration.

Posts read: the random test sample, and for each probe the posts drawn in its flagged bands and
just under them, or in its 100 highest scores when it has no level (`bands --split test`).
Nothing is chosen here: the thresholds come from `calibrate`, and the bar a level must reach
to be shown is fixed below. Writes `reports/probes/metrics.json`, read by the report and the app.

Run: uv run --group pipelines python -m pipelines.probes.evaluate --run v1 --rounds m1 t1_calls
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score

from pipelines.probes.calibrate import uniform_in_band
from pipelines.probes.dataset import Labelled, load_labelled, vectors_for
from pipelines.probes.estimate import estimate, make_bands, precision_at, wilson
from pipelines.probes.languages import accuracy, by_language, language_groups
from pipelines.probes.pool import load_pool
from pipelines.probes.sample import RANDOM
from pipelines.probes.score import load_probes, score_rows, split_rows
from pipelines.probes.train import RUNS, Target, targets

log = logging.getLogger("probes.evaluate")

REPORT = Path("reports") / "probes" / "metrics.json"
LEVELS = ("probable", "possible")
BASE_RATES = (0.001, 0.01, 0.05)
# A level is shown when its measured precision reaches the bar on enough read flags.
SHOWN_PRECISION = 0.6
SHOWN_READ = 30
# Without a shown level, a probe still feeds the review pass when it ranks far above chance:
# on the random sample, or among the posts read at the head of its scores.
REVIEW_LIFT = 3.0
REVIEW_HEAD = 0.25
MIN_POSITIVES_FOR_AP = 5
# A second, stronger reader re-reads some of the test posts (`audit`). When it confirms fewer than
# this share of the yes answers a probe is measured against, the probe is not shown.
AUDIT_CONFIRMED = 0.7
AUDIT_MIN = 10


def ranking(labelled: Labelled, target: Target, scores: np.ndarray) -> dict[str, object]:
    """Average precision on the random test sample, against its chance level."""
    random = np.array([labelled.stratum[i] == RANDOM for i in target.rows])
    y, s = target.y[random], scores[random]
    out: dict[str, object] = {"n": int(random.sum()), "positives": int(y.sum())}
    if y.sum() >= MIN_POSITIVES_FOR_AP:
        out["average_precision"] = float(average_precision_score(y, s))
        out["chance"] = float(y.mean())
    return out


def level_measures(bands: list, threshold: float) -> dict[str, object]:
    out = {"threshold": threshold, **estimate(bands, threshold)}
    out["wilson"] = list(wilson(out["positive_flagged"], out["read_flagged"]))
    if out["recall"] and out["fpr"]:
        out["precision_at_base_rate"] = {
            str(rate): precision_at(out["recall"]["value"], out["fpr"]["value"], rate)
            for rate in BASE_RATES
        }
    return out


def passes(measure: dict) -> bool:
    precision = measure["precision"]
    enough = measure["read_flagged"] >= SHOWN_READ
    return bool(precision) and precision["value"] >= SHOWN_PRECISION and enough


def state_of(passing: dict, measured: dict, head: dict | None, rank: dict) -> str:
    if passing:
        return "shown"
    lift = rank.get("average_precision", 0.0) / max(rank.get("chance", 1.0), 1e-9)
    heads = [m for m in (*measured.values(), head) if m and m["read_flagged"] >= SHOWN_READ]
    strong = any(m["wilson"][0] >= REVIEW_HEAD for m in heads)
    return "review-only" if lift >= REVIEW_LIFT or strong else "dropped"


def evaluate_target(
    labelled: Labelled, target: Target, levels: dict, drawn: list[dict] | None,
    read: np.ndarray, split: np.ndarray, groups: np.ndarray | None,
) -> dict[str, object]:  # fmt: skip
    used = uniform_in_band(labelled, target)
    cuts = [levels[name] for name in LEVELS if levels.get(name) is not None]
    head_cut = None
    if cuts:
        # The last band drawn is the one just under the lower threshold.
        edges = [*cuts, drawn[-1]["low"]] if drawn else cuts
    else:
        # No level: the head of the scores was read instead, to measure the ranking.
        head_cut = drawn[0]["low"] if drawn else None
        edges = [head_cut] if head_cut is not None else []
    bands = make_bands(split, edges, read[used], target.y[used])
    measured = {
        name: level_measures(bands, levels[name]) for name in LEVELS if levels.get(name) is not None
    }
    head = level_measures(bands, head_cut) if head_cut is not None else None
    rank = ranking(labelled, target, read)
    passing = {name: row for name, row in measured.items() if passes(row)}
    failing = {name: row for name, row in measured.items() if name not in passing}
    out: dict[str, object] = {
        # A shown probe keeps only the levels that pass; another keeps what was measured.
        "levels": passing or measured,
        "withdrawn": failing if passing else {},
        "head": head,
        "ranking": rank,
        "state": state_of(passing, measured, head, rank),
    }
    if groups is not None:
        out["by_language"] = by_language(read[used], target.y[used], groups[used], levels)
    return out


def second_opinions(folder: Path) -> dict[str, dict]:
    """What the audits of the run found, per target: yes confirmed and no overturned."""
    found: dict[str, dict] = {}
    for path in sorted(folder.glob("audit-*.json")):
        found.update(json.loads(path.read_text(encoding="utf-8")))
    return found


def with_second_opinion(row: dict[str, object], audit: dict | None) -> dict[str, object]:
    """Adds the audit of the target; a shown probe whose labels it does not confirm is withdrawn."""
    if not audit:
        return row
    confirmed, total = audit["yes"]
    row["audit"] = {"yes": audit["yes"], "no": audit["no"]}
    if row["state"] == "shown" and total >= AUDIT_MIN and confirmed / total < AUDIT_CONFIRMED:
        row["state"] = "review-only"
        row["demoted"] = "second opinion"
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--rounds", nargs="+", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    folder = RUNS / args.run
    thresholds = json.loads((folder / "thresholds.json").read_text(encoding="utf-8"))
    bands_path = folder / "bands-test.json"
    drawn = json.loads(bands_path.read_text(encoding="utf-8")) if bands_path.exists() else {}
    pool = load_pool()
    probes = load_probes(args.run)
    labelled = load_labelled(tuple(args.rounds))
    vectors, model_key = vectors_for(labelled.keys)
    logits = probes.logits(vectors)
    split = score_rows(probes, pool, split_rows(pool, "test"))
    groups = language_groups(probes, logits)
    audits = second_opinions(folder)
    out: dict[str, object] = {}
    for target in targets(labelled, "test"):
        if target.name not in probes.names:
            continue
        column = probes.names.index(target.name)
        measured = evaluate_target(
            labelled, target, thresholds[target.name], drawn.get(target.name),
            logits[target.rows, column], split[:, column],
            None if groups is None else groups[target.rows],
        )  # fmt: skip
        out[target.name] = with_second_opinion(measured, audits.get(target.name))
        log.info("%-30s %s", target.name, out[target.name]["state"])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = {"run": args.run, "rounds": args.rounds, "model_key": model_key, "targets": out}
    if groups is not None:
        report["language_probe"] = accuracy(labelled, groups, "test")
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    (folder / "metrics.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

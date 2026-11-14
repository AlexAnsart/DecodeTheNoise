"""The figures of the probe report, drawn from the files the campaign wrote.

Run: uv run --group pipelines python -m pipelines.probes.figures --run v1 --round m1
"""

import argparse
import json
import logging

import numpy as np

from pipelines.probes.estimate import wilson
from pipelines.probes.merge import READINGS, load_reading
from pipelines.probes.plots import (
    AQUA,
    BLUE,
    MUTED,
    ORANGE,
    SECONDARY,
    dot_rows,
    plt,
    rows_figure,
    save,
    style,
    unique_legend,
)
from pipelines.probes.sample import round_dir
from pipelines.probes.taxonomy import FAMILIES, LABELS, YES, family_labels
from pipelines.probes.train import RUNS

log = logging.getLogger("probes.figures")

THIN = 5  # under this many yes answers, a kappa says little: the dot is drawn hollow


def read_json(path: object) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def agreement(round_name: str) -> None:
    """Kappa between the two readings, label by label."""
    stats = read_json(round_dir(round_name) / "agreement.json")
    names = [label.name for label in LABELS if stats.get(label.name, {}).get("n")]
    values = [stats[name]["kappa"] for name in names]
    thin = [min(stats[n].get("yes_a", THIN), stats[n].get("yes_b", THIN)) < THIN for n in names]
    fig, (ax,) = rows_figure(len(names))
    for line, text in ((0.6, "0.6"), (0.8, "0.8")):
        ax.axvline(line, color=MUTED, linewidth=1, linestyle=(0, (3, 3)))
        ax.text(line, len(names) - 0.2, text, color=SECONDARY, ha="center", va="bottom", fontsize=8)
    dot_rows(ax, names, values, hollow=thin)
    ax.set_xlim(-0.05, 1.02)
    ax.set_xlabel("Cohen's kappa between two independent readings (hollow: fewer than 5 yes)")
    ax.set_title(f"Agreement between annotators, round {round_name}", pad=14)
    save(fig, f"agreement-{round_name}")


def prevalence(round_name: str, splits: tuple[str, ...]) -> None:
    """Share of yes among the random posts of the round, with its Wilson interval."""
    items = {i["key"]: i for i in map(json.loads, _lines(round_dir(round_name) / "items.jsonl"))}
    keep = {k for k, i in items.items() if i["stratum"] == "random" and i["split"] in splits}
    names, rates, lows, highs = [], [], [], []
    for family in FAMILIES:
        settled = read_json(round_dir(round_name) / "labels" / family / "settled.json")
        for label in family_labels(family):
            if not label.binary:
                continue
            answers = [row[label.name] for key, row in settled.items() if key in keep]
            yes, n = answers.count(YES), len(answers)
            low, high = wilson(yes, n)
            names.append(label.name)
            rates.append(max(yes / n, 3e-4) * 100)
            lows.append(max(low, 3e-4) * 100)
            highs.append(high * 100)
    fig, (ax,) = rows_figure(len(names))
    dot_rows(ax, names, rates, low=lows, high=highs)
    ax.set_xscale("log")
    ax.set_xticks([0.03, 0.1, 0.3, 1, 3, 10, 30], ["0", "0.1%", "0.3%", "1%", "3%", "10%", "30%"])
    ax.set_xlabel(f"Share of posts answered yes, random sample (n = {len(keep)}), 95% interval")
    ax.set_title("How frequent each label is in the corpus", pad=10)
    save(fig, f"prevalence-{round_name}")


def _lines(path: object) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").split("\n") if line]


def position_effect(round_name: str) -> None:
    """Share of yes by position of the post in its batch: a flat line means no fatigue."""
    yes, seen = np.zeros(41), np.zeros(41)
    for family in FAMILIES:
        for reading in READINGS[:2]:
            for row in load_reading(round_name, family, reading).values():
                answers = [v for v in row["labels"].values() if v in ("yes", "no")]
                yes[row["n"]] += answers.count(YES)
                seen[row["n"]] += len(answers)
    rate = 100 * yes[1:] / np.maximum(seen[1:], 1)
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    style(ax, grid="y")
    ax.plot(range(1, 41), rate, color=BLUE, linewidth=2, marker="o", markersize=4)
    ax.axhline(rate.mean(), color=MUTED, linewidth=1, linestyle=(0, (3, 3)))
    ax.text(40.4, rate.mean(), "mean", color=SECONDARY, va="center", fontsize=8)
    ax.set_ylim(0, max(rate) * 1.35)
    ax.set_xlabel("Position of the post in its batch of 40")
    ax.set_ylabel("Yes answers, % of decided answers")
    ax.set_title(f"Do annotators tire along a batch? Round {round_name}", pad=10)
    save(fig, f"position-{round_name}")


def model_comparison(run: str) -> None:
    """Out-of-fold average precision of the linear probe against other readers of the vector."""
    rows = {k: v for k, v in read_json(RUNS / run / "diagnostics.json").items() if "knn" in v}
    names = sorted(rows, key=lambda name: -rows[name]["linear"])
    fig, (ax,) = rows_figure(len(names))
    series = (
        ("centroid", MUTED, "Similarity to the mean positive"),
        ("knn", AQUA, "k-NN, k = 15"),
        ("mlp", ORANGE, "MLP, one hidden layer"),
        ("linear", BLUE, "Linear probe"),
    )
    for key, color, name in series:
        dot_rows(ax, names, [rows[n][key] for n in names], color=color, name=name)
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("Average precision, out of fold, train split")
    ax.set_title("Is the signal linear? Four readers of the same vectors", pad=10)
    unique_legend(ax, loc="lower right", fontsize=8)
    save(fig, f"models-{run}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run")
    parser.add_argument("--round", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    agreement(args.round)
    position_effect(args.round)
    prevalence(args.round, ("train", "calibration", "test"))
    if args.run and (RUNS / args.run / "diagnostics.json").exists():
        model_comparison(args.run)


if __name__ == "__main__":
    main()

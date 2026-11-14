"""Figures of what the probes learnt and how they measure on test.

Run: uv run --group pipelines python -m pipelines.probes.figures_results --run v1
"""

import argparse
import json
import logging
from pathlib import Path

from pipelines.probes.evaluate import LEVELS, REPORT, SHOWN_PRECISION
from pipelines.probes.plots import (
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
from pipelines.probes.train import RUNS

log = logging.getLogger("probes.figures_results")

LEVEL_COLOURS = {"probable": BLUE, "possible": ORANGE}
# One hue, light to dark: fewer to more dimensions.
DIM_COLOURS = {"64": "#9ec5f4", "128": "#5598e7", "256": "#1c5cab"}
COLUMNS = 6


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def part(row: dict, level: str, measure: str, field: str) -> float | None:
    value = row["levels"].get(level, {}).get(measure)
    return value[field] if value else None


def test_results(metrics: dict) -> None:
    """Precision and recall of each level on test, with their 95% intervals."""
    rows = {k: v for k, v in metrics["targets"].items() if v["levels"]}
    names = sorted(
        rows, key=lambda n: -max(part(rows[n], lv, "precision", "value") or 0 for lv in LEVELS)
    )
    fig, axes = rows_figure(len(names), width=10, panels=2)
    for ax, measure in zip(axes, ("precision", "recall"), strict=True):
        for level, shift in (("probable", 0.16), ("possible", -0.16)):
            dot_rows(
                ax, names,
                [part(rows[n], level, measure, "value") for n in names],
                low=[part(rows[n], level, measure, "low") for n in names],
                high=[part(rows[n], level, measure, "high") for n in names],
                color=LEVEL_COLOURS[level], name=level, offset=shift,
            )  # fmt: skip
        ax.set_xlim(0, 1.02)
        ax.set_xlabel(f"{measure.capitalize()} on test, 95% interval")
    axes[0].axvline(SHOWN_PRECISION, color=MUTED, linewidth=1, linestyle=(0, (3, 3)))
    axes[0].text(SHOWN_PRECISION, len(names) - 0.2, "bar to be shown", color=SECONDARY,
                 ha="center", va="bottom", fontsize=8)  # fmt: skip
    axes[0].set_title("Measured on test, at the thresholds frozen on calibration", pad=14)
    unique_legend(axes[1], loc="lower right", fontsize=8, title="Level")
    save(fig, f"test-{metrics['run']}")


def ranking(metrics: dict) -> None:
    """Average precision on the random test sample, against the chance level of each label."""
    rows = {k: v["ranking"] for k, v in metrics["targets"].items() if "chance" in v["ranking"]}
    names = sorted(rows, key=lambda n: -rows[n]["average_precision"])
    fig, (ax,) = rows_figure(len(names))
    dot_rows(ax, names, [rows[n]["chance"] for n in names], color=MUTED, name="Chance (prevalence)")
    dot_rows(ax, names, [rows[n]["average_precision"] for n in names], name="Linear probe")
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("Average precision on the random test sample")
    ax.set_title("Ranking quality on test posts drawn at random", pad=10)
    unique_legend(ax, loc="lower right", fontsize=8)
    save(fig, f"ranking-{metrics['run']}")


def learning_curves(run: str, diagnostics: dict) -> None:
    """Small multiples: out-of-fold average precision against the share of train posts used."""
    rows = {k: v["learning_curve"] for k, v in diagnostics.items() if len(v["learning_curve"]) == 3}
    names = sorted(rows)
    lines = -(-len(names) // COLUMNS)
    fig, axes = plt.subplots(lines, COLUMNS, figsize=(11, 1.5 * lines), sharex=True, sharey=True)
    for ax, name in zip(axes.flat, names, strict=False):
        style(ax, grid="y")
        points = rows[name]
        ax.plot([25, 50, 100], [points[k] for k in ("0.25", "0.5", "1.0")], color=BLUE,
                linewidth=2, marker="o", markersize=4)  # fmt: skip
        ax.set_title(name.replace("_", " "), fontsize=7.5, fontweight="normal", pad=3)
        ax.set_ylim(0, 1.02)
        ax.set_xticks([25, 50, 100])
    for ax in axes.flat[len(names) :]:
        ax.set_visible(False)
    fig.supxlabel("Share of the train posts used to fit, %", fontsize=9, color=SECONDARY)
    fig.supylabel("Average precision, out of fold", fontsize=9, color=SECONDARY)
    fig.suptitle("Would more labelled posts help?", x=0.01, y=0.998, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    save(fig, f"learning-{run}")


def dimensions(run: str, diagnostics: dict) -> None:
    """Out-of-fold average precision with the first 64, 128 and 256 values of the vector."""
    rows = {k: v["dims"] for k, v in diagnostics.items() if "dims" in v}
    names = sorted(rows, key=lambda n: -rows[n]["256"])
    fig, (ax,) = rows_figure(len(names))
    for dims, color in DIM_COLOURS.items():
        dot_rows(ax, names, [rows[n][dims] for n in names], color=color, name=f"{dims} dimensions")
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("Average precision, out of fold, train split")
    ax.set_title("Is the served size of the vector enough?", pad=10)
    unique_legend(ax, loc="lower right", fontsize=8)
    save(fig, f"dims-{run}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    diagnostics_path = RUNS / args.run / "diagnostics.json"
    if diagnostics_path.exists():
        diagnostics = read_json(diagnostics_path)
        learning_curves(args.run, diagnostics)
        dimensions(args.run, diagnostics)
    if REPORT.exists():
        metrics = read_json(REPORT)
        test_results(metrics)
        ranking(metrics)


if __name__ == "__main__":
    main()

"""What the probes of a run flag on a build of the map: counts, zones, and a picture.

The server scores a build itself from the exported pack. This does the same sum offline, from
the run's weights and the levels kept by the evaluation, to check a build before it is shown:
the share flagged at each level should match the share measured on test. Writes
`reports/probes/demo.json` and `docs/probes/figures/demo-<run>.png`.

Run: uv run --group pipelines python -m pipelines.probes.demo --run v1 --build tweets-2026-500k
"""

import argparse
import json
import logging

import numpy as np

from pipelines.paths import LAYOUT_FILE, VECTORS_FILE, VECTORS_META, ZONES_FILE, work_dir
from pipelines.probes.evaluate import LEVELS, REPORT
from pipelines.probes.plots import GRID, plt, save
from pipelines.probes.score import CHUNK, load_probes

log = logging.getLogger("probes.demo")

OUT = REPORT.with_name("demo.json")
ZONE_OF_POINT = "zone.npy"
# The probes drawn: frequent ones and rare ones, from different families.
DRAWN = ("political", "loaded_language", "contempt", "theme:sport", "lang:de",
         "commercial_promo", "attack_addressee", "urgency_framing")  # fmt: skip
# One hue, light then dark: `possible`, then `probable`.
COLOURS = {"possible": "#86b6ef", "probable": "#1c5cab"}
TOP_ZONES = 3


def flags(run: str, build: str, levels: dict[str, dict]) -> dict[str, dict[str, np.ndarray]]:
    """For each probe with a level, which points of the build reach each level."""
    work = work_dir(build)
    meta = json.loads((work / VECTORS_META).read_text(encoding="utf-8"))
    table = np.memmap(work / VECTORS_FILE, dtype=np.float16, mode="r")
    vectors = table.reshape(int(meta["n"]), int(meta["dims"]))
    probes = load_probes(run)
    columns = {name: probes.names.index(name) for name in levels}
    out = {n: {lv: np.zeros(len(vectors), dtype=bool) for lv in cuts} for n, cuts in levels.items()}
    for start in range(0, len(vectors), CHUNK):
        logits = probes.logits(np.asarray(vectors[start : start + CHUNK], dtype=np.float32))
        for name, cuts in levels.items():
            for level, cut in cuts.items():
                out[name][level][start : start + CHUNK] = logits[:, columns[name]] >= cut
    return out


def summary(found: dict, metrics: dict, zones: np.ndarray, names: list[str]) -> dict[str, object]:
    rows = {}
    for name, by_level in found.items():
        row: dict[str, object] = {"state": metrics[name]["state"]}
        for level, mask in by_level.items():
            share_by_zone = np.bincount(zones[mask], minlength=len(names)) / np.bincount(zones)
            top = np.argsort(-share_by_zone)[:TOP_ZONES]
            row[level] = {
                "flagged": int(mask.sum()),
                "share": float(mask.mean()),
                "share_on_test": metrics[name]["levels"][level]["flag_rate"],
                "top_zones": [{"zone": names[z], "share": float(share_by_zone[z])} for z in top],
            }
        rows[name] = row
    return rows


def picture(run: str, build: str, found: dict, positions: np.ndarray) -> None:
    """Small multiples of the 2D map: every point in grey, the flagged ones in blue."""
    rng = np.random.default_rng(0)
    base = rng.choice(len(positions), size=min(len(positions), 120_000), replace=False)
    drawn = [name for name in DRAWN if name in found]
    fig, axes = plt.subplots(2, 4, figsize=(13, 6.8))
    for ax, name in zip(axes.flat, drawn, strict=False):
        ax.scatter(*positions[base].T, s=0.15, color=GRID, linewidths=0, rasterized=True)
        for level in reversed(LEVELS):
            mask = found[name].get(level)
            if mask is not None:
                ax.scatter(*positions[mask].T, s=0.6, color=COLOURS[level], linewidths=0,
                           rasterized=True, label=level)  # fmt: skip
        widest = max(found[name].values(), key=lambda mask: mask.sum())
        ax.set_title(f"{name}  ({100 * widest.mean():.2f}% of posts)", fontsize=9, pad=4)
        # A few stray points would shrink the cloud: the frame keeps the bulk of the map.
        ax.set_xlim(*np.percentile(positions[:, 0], [0.2, 99.8]))
        ax.set_ylim(*np.percentile(positions[:, 1], [0.2, 99.8]))
        ax.set_xticks([])
        ax.set_yticks([])
        for side in ax.spines.values():
            side.set_visible(False)
    for ax in axes.flat[len(drawn) :]:
        ax.set_visible(False)
    handles = [
        plt.Line2D([], [], marker="o", linestyle="", color=c, label=lv) for lv, c in COLOURS.items()
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=9)
    fig.suptitle(
        f"Where eight probes fire on the map of {build}", x=0.01, ha="left", fontweight="bold"
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    save(fig, f"demo-{run}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--build", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    metrics = json.loads(REPORT.read_text(encoding="utf-8"))["targets"]
    levels = {
        name: {level: row["levels"][level]["threshold"] for level in row["levels"]}
        for name, row in metrics.items()
        if row["levels"] and row["state"] != "dropped"
    }
    found = flags(args.run, args.build, levels)
    work = work_dir(args.build)
    zone_names = [zone["name"] for zone in json.loads((work / ZONES_FILE).read_text("utf-8"))]
    rows = summary(found, metrics, np.load(work / ZONE_OF_POINT), zone_names)
    posts = len(next(iter(next(iter(found.values())).values())))
    report = {"run": args.run, "build": args.build, "posts": posts, "probes": rows}
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    with np.load(work / LAYOUT_FILE) as layout:
        picture(args.run, args.build, found, layout["pos2"])
    log.info("%s: %d probes on %d posts", OUT, len(rows), posts)


if __name__ == "__main__":
    main()

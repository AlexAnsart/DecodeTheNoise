"""What the probes of a run flag on a build of the map: counts, zones, and a picture.

The server scores a build itself from the exported pack. This does the same sum offline, from
the run's weights and the levels kept by the evaluation, to check a build before it is shown:
the share flagged at each level should match the share measured on test. It also records who
wrote the build: the split of its actors, and the accounts kept by hand. Writes
`reports/probes/demo.json` and `docs/probes/figures/demo-<run>.png`.

Run: uv run --group pipelines python -m pipelines.probes.demo --run v1 --build tweets-2026-100k
"""

import argparse
import json
import logging
import sqlite3
from collections import Counter
from pathlib import Path

import numpy as np

from pipelines.paths import (
    CORPUS_FILE,
    LAYOUT_FILE,
    VECTORS_FILE,
    VECTORS_META,
    ZONE_OF_POINT_FILE,
    ZONES_FILE,
    work_dir,
)
from pipelines.probes.demo_picture import picture
from pipelines.probes.evaluate import REPORT
from pipelines.probes.pool import SPLITS, split_of
from pipelines.probes.score import CHUNK, load_probes
from pipelines.sample.__main__ import SAMPLE_FILE

log = logging.getLogger("probes.demo")

OUT = REPORT.with_name("demo.json")
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


def authors(work: Path) -> tuple[dict[str, object], np.ndarray]:
    """Who wrote the build, and which points come from the accounts kept by hand, not drawn."""
    corpus = sqlite3.connect(f"file:{(work / CORPUS_FILE).as_posix()}?mode=ro", uri=True)
    actor_of_point = dict(corpus.execute("SELECT idx, actor_id FROM items"))
    corpus.close()
    actors = set(actor_of_point.values())
    sample = json.loads((work / SAMPLE_FILE).read_text(encoding="utf-8"))
    hand_kept = set(sample.get("kept", {}).get("actors", []))
    kept = np.zeros(len(actor_of_point), dtype=bool)
    for point, actor in actor_of_point.items():
        kept[point] = actor in hand_kept
    described = {
        "actors": len(actors),
        "actors_by_split": dict(Counter(SPLITS[split_of(actor)] for actor in actors)),
        "kept_actors": len(hand_kept),
        "kept_posts": int(kept.sum()),
    }
    return described, kept


def summary(
    found: dict, metrics: dict, zones: np.ndarray, names: list[str], kept: np.ndarray
) -> dict[str, object]:
    rows = {}
    for name, by_level in found.items():
        row: dict[str, object] = {"state": metrics[name]["state"]}
        for level, mask in by_level.items():
            share_by_zone = np.bincount(zones[mask], minlength=len(names)) / np.bincount(zones)
            top = np.argsort(-share_by_zone)[:TOP_ZONES]
            row[level] = {
                "flagged": int(mask.sum()),
                "flagged_in_kept": int((mask & kept).sum()),
                "share": float(mask.mean()),
                "share_on_test": metrics[name]["levels"][level]["flag_rate"],
                "top_zones": [{"zone": names[z], "share": float(share_by_zone[z])} for z in top],
            }
        rows[name] = row
    return rows


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
    described, kept = authors(work)
    rows = summary(found, metrics, np.load(work / ZONE_OF_POINT_FILE), zone_names, kept)
    report = {"run": args.run, "build": args.build, "posts": len(kept), **described, "probes": rows}
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    with np.load(work / LAYOUT_FILE) as layout:
        picture(args.run, args.build, found, layout["pos2"])
    log.info("%s: %d probes on %d posts", OUT, len(rows), len(kept))


if __name__ == "__main__":
    main()

"""Packs an evaluated probe run into the two files the server loads.

Reads the run's weights (`probes.npz`), the cuts frozen on calibration (`thresholds.json`) and
what the test split measured (`reports/probes/metrics.json`). Writes `probes.json` and
`probes.npz` (contract: backend/probes/schema.py). Every number comes from those files. A probe
keeps the levels whose precision was measured on the test split. A review-only probe without a
level is packed with the cut from which it sends an item to the LLM review. A probe with
neither stays out.

Run: uv run --group pipelines python -m pipelines.probes.export --run v1 [--out probes]
"""

import argparse
import json
import logging
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, TypeAdapter

from backend.probes.names import plain_name
from backend.probes.pack import load_probes
from backend.probes.schema import (
    PACK_FILE,
    WEIGHTS_FILE,
    LevelMeasure,
    PackedProbe,
    ProbeInfo,
    ProbePack,
)
from pipelines.probes.taxonomy import BY_NAME, PROBE

log = logging.getLogger("probes.export")

TAXONOMY_DOC = Path("docs") / "probes" / "taxonomy.md"
# Folder under `reports/` where `evaluate` writes the metrics of the probes.
REPORT_FOLDER = "probes"
LEVELS = ("possible", "probable")
# A review-only probe with no measured level sends an item to the LLM review from the deepest
# calibration edge where at least one flagged post in five was a real one, on enough posts read
# to say so, and which flags one post in a hundred at most: a wider net would send posts to the
# review for nothing. That precision is a calibration estimate: it is never shown as a measure.
REVIEW_PRECISION = 0.2
REVIEW_READ = 20
REVIEW_FLAG_RATE = 0.01
# A row of a taxonomy table: | `label` | what the annotator decides | use |
_ROW = re.compile(r"^\|\s*`(\w+)`\s*\|\s*([^|]*?)\s*\|", re.MULTILINE)


class ExportRefused(RuntimeError):
    """The files of the run do not describe one evaluated state: nothing is written."""


class _Interval(BaseModel):
    value: float
    low: float
    high: float


class _Edge(BaseModel):
    """One candidate cut of `calibrate`, with what the calibration split measured above it."""

    threshold: float
    precision: _Interval | None = None
    read_flagged: int = 0
    # Share of the calibration posts at or above the threshold.
    flag_rate: float = 1.0


class Cuts(BaseModel):
    possible: float | None = None
    probable: float | None = None
    edges: list[_Edge] = []


class _Level(BaseModel):
    threshold: float
    precision: _Interval | None
    recall: _Interval | None
    fpr: _Interval | None
    read_flagged: int
    flag_rate: float


class _Target(BaseModel):
    state: Literal["shown", "review-only", "dropped"]
    levels: dict[str, _Level]


class _Metrics(BaseModel):
    run: str
    model_key: str
    targets: dict[str, _Target]


_CUTS_FILE = TypeAdapter(dict[str, Cuts])


def descriptions(doc: Path) -> dict[str, str]:
    """What the annotator decides for each label, from the tables of the taxonomy document."""
    return dict(_ROW.findall(doc.read_text(encoding="utf-8"))) if doc.exists() else {}


def display(target: str, described: dict[str, str]) -> tuple[str, str, str]:
    """Label, description and family of a target: a label, or `label:value` for one answer."""
    name = target.partition(":")[0]
    label = plain_name(target)
    family = BY_NAME[name].family if name in BY_NAME else "other"
    return label, described.get(name, label), family


def reviewable(target: str) -> bool:
    """Whether a flag of this target is worth an LLM review: a yes/no label the taxonomy
    means as a detector on one item. A theme, a side, a language, an emotion or an auxiliary
    label is not: such a target would send posts to the review for nothing."""
    label = BY_NAME.get(target)
    return label is not None and label.binary and label.use == PROBE


def review_cut(target: str, cuts: Cuts) -> float | None:
    """The deepest calibration edge that still holds enough real posts to be worth a review."""
    if not reviewable(target):
        return None
    worth = [
        edge.threshold
        for edge in cuts.edges
        if edge.precision is not None
        and edge.precision.value >= REVIEW_PRECISION
        and edge.read_flagged >= REVIEW_READ
        and edge.flag_rate <= REVIEW_FLAG_RATE
    ]
    return min(worth) if worth else None


def measure_of(level: _Level) -> LevelMeasure | None:
    """None when the test split could not give the precision of the level."""
    if level.precision is None or not math.isfinite(level.precision.value):
        return None
    return LevelMeasure(
        precision=level.precision.value,
        precision_low=level.precision.low,
        precision_high=level.precision.high,
        false_positive_rate=level.fpr.value if level.fpr else None,
        recall=level.recall.value if level.recall else None,
        read=level.read_flagged,
        flag_rate=level.flag_rate,
    )


def measured_levels(target: str, cuts: Cuts, levels: dict[str, _Level]) -> dict[str, LevelMeasure]:
    """The levels that have a cut and a precision measured at that very cut."""
    kept = {}
    for name in LEVELS:
        cut, level = getattr(cuts, name), levels.get(name)
        if cut is None or level is None:
            continue
        if not math.isclose(cut, level.threshold, rel_tol=1e-9, abs_tol=1e-12):
            raise ExportRefused(
                f"{target}: the {name} cut is {cut} and the metrics were measured at "
                f"{level.threshold}. Run evaluate again."
            )
        measure = measure_of(level)
        if measure is None:
            log.warning("%s: the precision of %s was not measured, level left out", target, name)
        else:
            kept[name] = measure
    return kept


def packed(target: str, cuts: Cuts, measured: _Target, described: dict[str, str]) -> PackedProbe:
    """A probe keeps the levels the test split measured, shown or not. A review-only probe
    that has none is packed with its review cut instead."""
    shown = measured.state == "shown"
    levels = measured_levels(target, cuts, measured.levels)
    label, description, family = display(target, described)
    info = ProbeInfo(
        key=target,
        label=label,
        description=description,
        family=family,
        state="shown" if shown else "review-only",
        possible=levels.get("possible"),
        probable=levels.get("probable"),
        report=REPORT_FOLDER,
    )
    return PackedProbe(
        info=info,
        possible_cut=cuts.possible if "possible" in levels else None,
        probable_cut=cuts.probable if "probable" in levels else None,
        review_cut=None if shown or levels else review_cut(target, cuts),
        reviewable=reviewable(target),
    )


def export_pack(run: str, run_dir: Path, metrics_file: Path, doc: Path, out: Path) -> ProbePack:
    metrics = _Metrics.model_validate(json.loads(metrics_file.read_text(encoding="utf-8")))
    if metrics.run != run:
        raise ExportRefused(f"{metrics_file} was measured on run {metrics.run}, not {run}.")
    cuts = _CUTS_FILE.validate_python(
        json.loads((run_dir / "thresholds.json").read_text(encoding="utf-8"))
    )
    described = descriptions(doc)
    with np.load(run_dir / "probes.npz") as data:
        arrays = {name: data[name] for name in ("names", "weights", "bias", "mean", "scale")}
    rows, probes = [], []
    for row, target in enumerate(str(name) for name in arrays["names"]):
        measured = metrics.targets.get(target)
        if measured is None or target not in cuts or measured.state == "dropped":
            continue
        probe = packed(target, cuts[target], measured, described)
        if (probe.possible_cut, probe.probable_cut, probe.review_cut) == (None, None, None):
            log.warning("%s: no measured level and no review cut, probe left out", target)
            continue
        if probe.info.state == "review-only" and not probe.reviewable:
            # Never shown and never sent to the review: it would do nothing in the pack.
            log.warning("%s: review-only and not a detector, probe left out", target)
            continue
        rows.append(row)
        probes.append(probe)
    pack = ProbePack(
        embedding_key=metrics.model_key,
        run=run,
        exported_at=datetime.now(UTC).isoformat(timespec="seconds"),
        probes=probes,
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / PACK_FILE).write_text(pack.model_dump_json(indent=1), encoding="utf-8")
    np.savez(
        out / WEIGHTS_FILE,
        names=np.array([probe.info.key for probe in probes], dtype=np.str_),
        weights=arrays["weights"][rows],
        bias=arrays["bias"][rows],
        mean=arrays["mean"],
        scale=arrays["scale"],
    )
    if len(load_probes(out, pack.embedding_key).infos) != len(probes):
        raise ExportRefused(f"The pack written in {out} is not read back whole by the server.")
    return pack


def main() -> None:
    # Imported here: these two modules load scikit-learn, which packing a run does not need.
    from pipelines.probes.evaluate import REPORT
    from pipelines.probes.train import RUNS

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--out", type=Path, default=Path("probes"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    pack = export_pack(args.run, RUNS / args.run, REPORT, TAXONOMY_DOC, args.out)
    shown = sum(probe.info.state == "shown" for probe in pack.probes)
    log.info(
        "run %s: %d probes packed in %s, %d shown", args.run, len(pack.probes), args.out, shown
    )


if __name__ == "__main__":
    main()

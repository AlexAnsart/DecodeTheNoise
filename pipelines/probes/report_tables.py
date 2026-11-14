"""The tables of the probe report, built from the files of the campaign. No number is typed."""

import json
from collections import Counter
from pathlib import Path

from pipelines.probes.estimate import wilson
from pipelines.probes.pool import POOL_META
from pipelines.probes.sample import ROUNDS, read_items, round_dir
from pipelines.probes.taxonomy import BY_NAME, FAMILIES, LABELS, YES, family_labels
from pipelines.probes.train import RUNS


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def table(header: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def pct(value: float | None, digits: int = 1) -> str:
    return "n/a" if value is None else f"{100 * value:.{digits}f}%"


def num(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def span(row: dict | None, digits: int = 0) -> str:
    """A measure with its 95% interval, in percent."""
    if not row:
        return "n/a"
    return f"{pct(row['value'], digits)} ({pct(row['low'], digits)} to {pct(row['high'], digits)})"


def pool_table() -> str:
    meta = read_json(POOL_META)
    rows = [
        ["Posts read", f"{meta['posts']:,}"],
        ["Over 1,500 characters (left out)", f"{meta['too_long']:,}"],
        *[[f"Kept: {name}", f"{count:,}"] for name, count in meta["kept_per_split"].items()],
    ]
    return table(["", "Posts"], rows)


def rounds_table() -> str:
    rows = []
    for folder in sorted(ROUNDS.iterdir()):
        items = read_items(folder.name)
        splits = Counter(item.split for item in items)
        kinds = Counter(item.stratum.split(":")[0] for item in items)
        passes = [f for f in FAMILIES if (folder / "labels" / f).exists()]
        files = [len(list((folder / "labels" / f).glob("?.jsonl"))) for f in passes]
        readings = max(files, default=0)
        rows.append([
            f"`{folder.name}`", len(items),
            ", ".join(f"{n} {s}" for s, n in splits.items()),
            ", ".join(f"{n} {k}" for k, n in kinds.items()),
            len(passes), readings,
        ])  # fmt: skip
    return table(["Round", "Posts", "Split", "How drawn", "Passes", "Readings"], rows)


def agreement_table(round_name: str) -> str:
    stats = read_json(round_dir(round_name) / "agreement.json")
    rows = []
    for label in LABELS:
        row = stats.get(label.name)
        if not row or not row["n"]:
            continue
        yes = f"{row['yes_a']} / {row['yes_b']}" if label.binary else f"{len(label.values)} values"
        rows.append([
            f"`{label.name}`", row["n"], yes, num(row["kappa"]),
            num(row.get("positive_agreement")), pct(row["unclear"]), pct(row["invalid"]),
        ])  # fmt: skip
    header = ["Label", "Posts read twice", "Yes (a / b)", "Kappa", "Positive agreement",
              "Unclear", "Thrown away"]  # fmt: skip
    return table(header, rows)


def prevalence(round_name: str, splits: tuple[str, ...]) -> dict[str, dict[str, float]]:
    """Yes answers among the random posts of a round, per yes/no label, with a Wilson interval."""
    keep = {i.key for i in read_items(round_name) if i.stratum == "random" and i.split in splits}
    out: dict[str, dict[str, float]] = {}
    for family in FAMILIES:
        path = round_dir(round_name) / "labels" / family / "settled.json"
        if not path.exists():
            continue
        settled = read_json(path)
        for label in family_labels(family):
            if not label.binary:
                continue
            answers = [row[label.name] for key, row in settled.items() if key in keep]
            decided = [a for a in answers if a in ("yes", "no")]
            yes = decided.count(YES)
            low, high = wilson(yes, len(decided))
            share = yes / max(len(decided), 1)
            out[label.name] = {"decided": len(decided), "yes": yes, "share": share, "low": low,
                               "high": high}  # fmt: skip
    return out


def prevalence_table(round_name: str, splits: tuple[str, ...]) -> str:
    rows = [
        [f"`{name}`", row["decided"], row["yes"], pct(row["share"], 2),
         f"{pct(row['low'], 2)} to {pct(row['high'], 2)}"]
        for name, row in prevalence(round_name, splits).items()
    ]  # fmt: skip
    return table(["Label", "Posts decided", "Yes", "Share", "95% interval"], rows)


def training_table(run: str) -> str:
    trained = read_json(RUNS / run / "train.json")["targets"]
    path = RUNS / run / "diagnostics.json"
    diagnostics = read_json(path) if path.exists() else {}
    rows = []
    for name, row in trained.items():
        extra = diagnostics.get(name, {})
        fitted = "c" in row
        rows.append([
            f"`{name}`", row["n"], row["positives"], row["c"] if fitted else "not fitted",
            num(row.get("oof_ap")), num(extra.get("centroid")), num(extra.get("knn")),
            num(extra.get("mlp")),
        ])  # fmt: skip
    header = ["Target", "Train posts", "Positives", "C", "Linear", "Mean positive", "k-NN", "MLP"]
    return table(header, rows)


def use_of(target: str) -> str:
    return BY_NAME[target.split(":")[0]].use

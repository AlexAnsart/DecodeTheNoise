"""Writes the batch files annotators read, and the plan the workflow runs.

One batch is a text file of numbered posts. Each family and each reading shuffles the round on
its own seed, so two readings of a post never share its neighbours or its position. The guides
are copied into the round: the labels stay tied to the exact text the annotators read.

Run: uv run --group pipelines python -m pipelines.probes.batches --round p1 --readings a b
"""

import argparse
import hashlib
import json
import logging
import shutil
from pathlib import Path

import numpy as np

from pipelines.probes.sample import RoundItem, read_items, round_dir
from pipelines.probes.taxonomy import FAMILIES, family_labels

log = logging.getLogger("probes.batches")

GUIDES = Path("docs") / "probes" / "guides"
BATCH_SIZE = 40
KEY_FILE = "key.json"
PLAN_FILE = "plan.json"
SEPARATOR = "=== POST {n} ==="


def batch_seed(round_name: str, family: str, reading: str) -> int:
    digest = hashlib.sha256(f"{round_name}|{family}|{reading}".encode()).digest()
    return int.from_bytes(digest[:8], "little")


def batch_text(batch_id: str, items: list[RoundItem]) -> str:
    """A post that would imitate a separator is defused; nothing else in it is changed."""
    lines = [f"batch_id: {batch_id}", f"posts: {len(items)}", ""]
    for n, item in enumerate(items, start=1):
        lines += [SEPARATOR.format(n=n), item.text.replace("=== POST", "= = = POST"), ""]
    return "\n".join([*lines, "=== END ==="]) + "\n"


def snapshot_guides(round_name: str) -> dict[str, str]:
    """Copies the guides into the round, once, and returns the hash of each file."""
    target = round_dir(round_name) / "guides"
    if not target.exists():
        shutil.copytree(GUIDES, target)
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        for path in sorted(target.glob("*.md"))
    }


def write_family(round_name: str, family: str, reading: str, items: list[RoundItem]) -> int:
    folder = round_dir(round_name) / "batches" / family / reading
    folder.mkdir(parents=True, exist_ok=True)
    order = np.random.default_rng(batch_seed(round_name, family, reading)).permutation(len(items))
    shuffled = [items[i] for i in order]
    keys: dict[str, list[str]] = {}
    for start in range(0, len(shuffled), BATCH_SIZE):
        number = start // BATCH_SIZE + 1
        batch_id = f"{round_name}-{family}-{reading}-{number:03d}"
        chunk = shuffled[start : start + BATCH_SIZE]
        (folder / f"{number:03d}.txt").write_text(batch_text(batch_id, chunk), encoding="utf-8")
        keys[batch_id] = [item.key for item in chunk]
    (folder / KEY_FILE).write_text(json.dumps(keys), encoding="utf-8")
    return len(keys)


def label_specs(family: str) -> str:
    """The labels of a family as the workflow reads them: `name`, `name+` when a yes must quote
    the post, `name=a|b|c` for a label with its own answers."""
    tokens = []
    for label in family_labels(family):
        if not label.binary:
            tokens.append(f"{label.name}={'|'.join(label.values)}")
        else:
            tokens.append(label.name + ("+" if label.quoted else ""))
    return " ".join(tokens)


def wanted(args: argparse.Namespace, family: str, items: list[RoundItem]) -> list[RoundItem]:
    """With `--pending`, the posts of this family that `merge` left for a third reading."""
    if not args.pending:
        return items
    path = round_dir(args.round) / "labels" / family / "pending.json"
    pending = set(json.loads(path.read_text(encoding="utf-8")))
    return [item for item in items if item.key in pending]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", required=True)
    parser.add_argument("--readings", nargs="+", default=["a"])
    parser.add_argument("--families", nargs="+", default=list(FAMILIES))
    parser.add_argument("--splits", nargs="*", help="only the posts of these splits")
    parser.add_argument("--pending", action="store_true", help="only posts two readings differ on")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    items = read_items(args.round)
    if args.splits:
        items = [item for item in items if item.split in args.splits]
    guides = snapshot_guides(args.round)
    tasks = [
        {
            "family": family,
            "reading": reading,
            "batches": write_family(args.round, family, reading, wanted(args, family, items)),
        }
        for family in args.families
        for reading in args.readings
    ]
    plan = {
        "root": round_dir(args.round).resolve().as_posix(),
        "tasks": tasks,
        "labels": {family: label_specs(family) for family in args.families},
    }
    plan_path = round_dir(args.round) / PLAN_FILE.replace(".", f"-{''.join(args.readings)}.")
    plan_path.write_text(json.dumps(plan, indent=1), encoding="utf-8")
    total = sum(int(task["batches"]) for task in tasks)
    log.info("round %s: %d posts, %d batches, plan %s", args.round, len(items), total, plan_path)
    log.info("guides: %s", guides)


if __name__ == "__main__":
    main()

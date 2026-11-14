"""Checks what annotators returned and writes the labels of one round.

An answer is taken only when its batch is complete: every post, once. A `yes` that must quote
the post and whose quote is not in the post becomes `invalid`: it counts as no reading at all.
Reads the journal of a workflow run; writes `labels/<family>/<reading>.jsonl` in the round.

Run: uv run --group pipelines python -m pipelines.probes.collect --round p1 --journal <path>
"""

import argparse
import json
import logging
import re
from collections.abc import Iterator
from pathlib import Path

from pipelines.probes.batches import KEY_FILE
from pipelines.probes.sample import read_items, read_jsonl, round_dir
from pipelines.probes.taxonomy import YES, Label, family_labels

log = logging.getLogger("probes.collect")

INVALID = "invalid"
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
_BATCH_ID = re.compile(r"^(?P<round>.+)-(?P<family>[a-z_]+)-(?P<reading>[a-z])-(?P<number>\d{3})$")


def flat(text: str) -> str:
    return " ".join(text.translate(_QUOTES).casefold().split())


def quote_holds(quote: str, text: str) -> bool:
    cleaned = flat(quote).strip("\"'` ")
    return bool(cleaned) and cleaned in flat(text)


def check_post(post: dict, labels: tuple[Label, ...], text: str) -> dict[str, object]:
    """The answers of one post, with every unsupported `yes` turned into `invalid`."""
    quotes = {e["label"]: e["quote"] for e in post.get("evidence", [])}
    values: dict[str, str] = {}
    kept: dict[str, str] = {}
    for label in labels:
        value = post[label.name]
        if label.quoted and value == YES:
            quote = quotes.get(label.name, "")
            if quote_holds(quote, text):
                kept[label.name] = quote
            else:
                value = INVALID
        values[label.name] = value
    return {"labels": values, "evidence": kept}


def check_batch(
    result: dict, keys: list[str], labels: tuple[Label, ...], texts: dict[str, str]
) -> list[dict[str, object]] | None:
    """One row per post, or None when the batch does not hold every post exactly once."""
    posts = result.get("posts", [])
    if sorted(post["n"] for post in posts) != list(range(1, len(keys) + 1)):
        return None
    rows = []
    for post in sorted(posts, key=lambda p: p["n"]):
        key = keys[post["n"] - 1]
        row = {"key": key, "batch_id": result["batch_id"], "n": post["n"]}
        rows.append({**row, **check_post(post, labels, texts[key])})
    return rows


def journal_results(path: Path) -> Iterator[dict]:
    """Every structured answer found in a workflow journal."""
    for entry in read_jsonl(path):
        result = entry.get("result")
        if isinstance(result, dict) and "batch_id" in result and "posts" in result:
            yield result


def collect(round_name: str, journal: Path) -> dict[str, int]:
    texts = {item.key: item.text for item in read_items(round_name)}
    root = round_dir(round_name)
    done: dict[tuple[str, str], dict[str, list[dict[str, object]]]] = {}
    counts = {"taken": 0, "incomplete": 0, "unknown": 0}
    for result in journal_results(journal):
        match = _BATCH_ID.match(str(result["batch_id"]).strip())
        if not match or match["round"] != round_name:
            counts["unknown"] += 1
            continue
        family, reading = match["family"], match["reading"]
        keys = json.loads((root / "batches" / family / reading / KEY_FILE).read_text("utf-8"))
        rows = check_batch(result, keys[match[0]], family_labels(family), texts)
        if rows is None:
            counts["incomplete"] += 1
            continue
        done.setdefault((family, reading), {})[match[0]] = rows
        counts["taken"] += 1
    for (family, reading), batches in done.items():
        merge_into(root / "labels" / family / f"{reading}.jsonl", batches)
    return counts


def merge_into(path: Path, batches: dict[str, list[dict[str, object]]]) -> None:
    """Adds the new batches to the file; a batch already there is replaced, never doubled."""
    path.parent.mkdir(parents=True, exist_ok=True)
    old = read_jsonl(path) if path.exists() else []
    rows = [row for row in old if row["batch_id"] not in batches]
    rows += [row for batch in batches.values() for row in batch]
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", required=True)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    log.info("round %s: %s", args.round, collect(args.round, args.journal))


if __name__ == "__main__":
    main()

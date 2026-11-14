"""Samples the IRA tweets into `corpus.sqlite`.

Run: uv run python -m pipelines.ingest --name ira-3k --items 3000
"""

import argparse
import csv
import logging
import random
from collections.abc import Iterator
from pathlib import Path

from pipelines import runlog
from pipelines.corpus import read_corpus, write_corpus
from pipelines.ingest.fetch import IRA_DIR
from pipelines.ingest.ira import MIN_TEXT_CHARS, Item, is_long_enough, parse_row
from pipelines.paths import CORPUS_FILE, work_dir

log = logging.getLogger("ingest")
SEED = 42


def read_rows(paths: list[Path]) -> Iterator[dict[str, str]]:
    """Streams the files one row at a time; they are never loaded whole."""
    for path in paths:
        with path.open(encoding="utf-8", newline="") as source:
            yield from csv.DictReader(source)


def sample_rows(rows: Iterator[dict[str, str]], n: int, seed: int) -> list[dict[str, str]]:
    """A uniform sample of `n` eligible rows in one pass (reservoir sampling)."""
    rng = random.Random(seed)
    kept: list[dict[str, str]] = []
    seen = 0
    for row in rows:
        if not is_long_enough(row.get("content") or ""):
            continue
        seen += 1
        if len(kept) < n:
            kept.append(row)
        elif (slot := rng.randrange(seen)) < n:
            kept[slot] = row
    log.info("%d eligible rows, %d sampled", seen, len(kept))
    return kept


def to_items(rows: list[dict[str, str]]) -> list[Item]:
    """Parsed, one per item id, oldest first so that the point order follows time."""
    unique = {item.item_id: item for row in rows if (item := parse_row(row)) is not None}
    return sorted(unique.values(), key=lambda it: (it.created_at or 0, it.item_id))


def subset(items: list[Item], n: int, seed: int) -> list[Item]:
    """A seeded sample of a corpus already built, in its order: every text is already embedded."""
    if n >= len(items):
        return items
    kept = sorted(random.Random(seed).sample(range(len(items)), n))
    return [items[i] for i in kept]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--items", type=int, required=True)
    parser.add_argument("--subset-of", help="sample the corpus of this build, not the files")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    # Numeric order, so the sample does not depend on how the file system lists the files.
    paths = sorted(IRA_DIR.glob("IRAhandle_tweets_*.csv"), key=lambda p: int(p.stem.split("_")[-1]))
    with runlog.timed() as elapsed:
        meta = {
            "dataset": "ira-tweets-fivethirtyeight",
            "files": ",".join(p.name for p in paths),
            "seed": str(SEED),
            "min_text_chars": str(MIN_TEXT_CHARS),
            "requested_items": str(args.items),
        }
        if args.subset_of:
            items = subset(read_corpus(work_dir(args.subset_of) / CORPUS_FILE), args.items, SEED)
            meta["subset_of"] = args.subset_of
        else:
            items = to_items(sample_rows(read_rows(paths), args.items, SEED))
        write_corpus(work_dir(args.name) / CORPUS_FILE, items, meta)
    runlog.record("ingest", args.name, len(items), elapsed[0])
    log.info("wrote %d items in %.1fs", len(items), elapsed[0])


if __name__ == "__main__":
    main()

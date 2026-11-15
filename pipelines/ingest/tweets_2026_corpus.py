"""Writes one corpus per downloaded shard of the 2026 sample of X posts.

A shard gives the build `tweets-2026-sNN`, apart from the builds of other datasets. Every post
with an id, an author and a text of the minimum length is kept, in every language.

Run: uv run --group pipelines python -m pipelines.ingest.tweets_2026_corpus [--shards 0 18]
     [--limit 2000]
"""

import argparse
import logging
from collections.abc import Iterator
from pathlib import Path

import pyarrow.parquet as pq

from pipelines import runlog
from pipelines.corpus import write_corpus
from pipelines.datasets.tweets_2026 import DEFAULT_SHARDS, DOWNLOAD_DIR, NAME, REVISION, shard_path
from pipelines.ingest.ira import MIN_TEXT_CHARS, Item
from pipelines.ingest.tweets_2026 import COLUMNS, parse_row
from pipelines.paths import CORPUS_FILE, work_dir

log = logging.getLogger("ingest.tweets_2026")


def build_name(shard: int, limit: int | None) -> str:
    return f"tweets-2026-s{shard:02d}" + (f"-first{limit}" if limit else "")


def read_rows(path: Path) -> Iterator[dict[str, object]]:
    """Streams the shard in batches; only the columns an item needs are decoded."""
    for batch in pq.ParquetFile(path).iter_batches(batch_size=50_000, columns=list(COLUMNS)):
        yield from batch.to_pylist()


def read_items(path: Path, limit: int | None) -> list[Item]:
    """One item per post id, oldest first so that the point order follows time."""
    unique: dict[str, Item] = {}
    for row in read_rows(path):
        item = parse_row(row)
        if item is not None:
            unique[item.item_id] = item
            if limit and len(unique) >= limit:
                break
    return sorted(unique.values(), key=lambda it: (it.created_at or 0, it.item_id))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards", type=int, nargs="*", default=list(DEFAULT_SHARDS))
    parser.add_argument("--limit", type=int, help="keep the first posts only, for a trial build")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    for shard in args.shards:
        name = build_name(shard, args.limit)
        source = DOWNLOAD_DIR / Path(shard_path(shard)).name
        with runlog.timed() as elapsed:
            items = read_items(source, args.limit)
            meta = {
                "dataset": NAME,
                "revision": REVISION,
                "files": source.name,
                "min_text_chars": str(MIN_TEXT_CHARS),
            }
            write_corpus(work_dir(name) / CORPUS_FILE, items, meta)
        runlog.record("ingest", name, len(items), elapsed[0])
        log.info("%s: %d items in %.1fs", name, len(items), elapsed[0])


if __name__ == "__main__":
    main()

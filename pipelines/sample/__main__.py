"""Draws a sample of builds that are already embedded and writes it as a build of its own.

The sample is made of whole actors: every item an actor has in the source builds comes with
it. A uniform draw of items would leave almost every actor with one item, and nothing to say
about who repeats what. Nothing is embedded again: the vectors are copied.

With `--held-out`, only the actors of the test split of the probe campaign are drawn
(`pipelines/probes/pool.py`): the probes never trained or set a threshold on them, so what a
probe shows on this build is on the kind of posts its reliability was measured on.

`--keep` names actors taken first, whole (under the same `--held-out` rule): a smaller sample
keeps the accounts an example rests on. They are recorded with the sample, with `--keep-note`.

Run: uv run python -m pipelines.sample --name tweets-2026-500k --items 500000 --held-out \
         --sources tweets-2026-s00 tweets-2026-s18 tweets-2026-s36 tweets-2026-s54 tweets-2026-s72
"""

import argparse
import json
import logging
import sqlite3
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import numpy as np

from pipelines import runlog
from pipelines.corpus import write_corpus
from pipelines.ingest.ira import Item
from pipelines.paths import CORPUS_FILE, VECTORS_FILE, VECTORS_META, work_dir
from pipelines.sample.draw import draw_actors
from pipelines.vectors import write_vectors

log = logging.getLogger("sample")

SEED = "demo-sample-v1"
SAMPLE_FILE = "sample.json"
# For each point of the sample: the source build (its rank in `sources`) and its index there.
ORIGIN_FILE = "origin.npy"
_COLUMNS = (
    "idx, item_id, actor_id, text, created_at, lang, repost_of, urls, "
    "category, post_type, followers"
)


def _open(source: str) -> sqlite3.Connection:
    path = work_dir(source) / CORPUS_FILE
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def count_items(sources: list[str], keep: Callable[[str], bool]) -> Counter[str]:
    """Items of each kept actor over all the sources."""
    counts: Counter[str] = Counter()
    for source in sources:
        con = _open(source)
        for actor_id, items in con.execute(
            "SELECT actor_id, count(*) FROM items GROUP BY actor_id"
        ):
            if keep(actor_id):
                counts[actor_id] += items
        con.close()
    return counts


def read_chosen(source: str, chosen: set[str], seen: set[str]) -> tuple[list[Item], list[int]]:
    """The items of the chosen actors in one source, in its order, and their indices there.
    An item id already taken from another source is not taken twice."""
    items: list[Item] = []
    indices: list[int] = []
    con = _open(source)
    for row in con.execute(f"SELECT {_COLUMNS} FROM items ORDER BY idx"):
        if row[2] not in chosen or row[1] in seen:
            continue
        seen.add(row[1])
        indices.append(row[0])
        items.append(
            Item(
                row[1], row[2], row[3], row[4], row[5], row[6], tuple(json.loads(row[7])), *row[8:]
            )
        )
    con.close()
    return items, indices


def read_rows(source: str, indices: list[int]) -> tuple[np.ndarray, dict[str, object]]:
    """The vectors of the given points of a source, and what its vectors were made with."""
    work = work_dir(source)
    meta = json.loads((work / VECTORS_META).read_text(encoding="utf-8"))
    stored = np.memmap(work / VECTORS_FILE, dtype=np.float16, mode="r")
    table = stored.reshape(int(meta["n"]), int(meta["dims"]))
    return np.asarray(table[np.asarray(indices, dtype=np.int64)], dtype=np.float32), meta


def held_out_of_probes() -> Callable[[str], bool]:
    # Imported when asked for: the probe campaign is not needed to draw any other sample.
    from pipelines.probes.pool import SPLITS, split_of

    test = SPLITS.index("test")
    return lambda actor_id: split_of(actor_id) == test


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--sources", nargs="+", required=True)
    parser.add_argument("--items", type=int, required=True)
    parser.add_argument("--held-out", action="store_true")
    parser.add_argument("--keep", nargs="*", default=[], help="actors taken first, whole")
    parser.add_argument("--keep-note", default="", help="why they are kept, recorded as given")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    work: Path = work_dir(args.name)
    work.mkdir(parents=True, exist_ok=True)

    with runlog.timed() as elapsed:
        counts = count_items(
            args.sources, held_out_of_probes() if args.held_out else lambda _: True
        )
        chosen = set(draw_actors(counts, args.items, SEED, first=args.keep))
        kept_first = sorted(set(args.keep) & chosen)
        log.info("%d actors drawn of %d, for %d items", len(chosen), len(counts), args.items)
        items: list[Item] = []
        parts: list[np.ndarray] = []
        origin: list[tuple[int, int]] = []
        seen: set[str] = set()
        metas = []
        for rank, source in enumerate(args.sources):
            taken, indices = read_chosen(source, chosen, seen)
            vectors, meta = read_rows(source, indices)
            items.extend(taken)
            parts.append(vectors)
            origin.extend((rank, index) for index in indices)
            metas.append(meta)
            log.info("%s: %d items", source, len(taken))
        keys = {str(meta["key"]) for meta in metas}
        if len(keys) != 1:
            raise SystemExit(f"the sources were not embedded with one model: {sorted(keys)}")
        kept = "actors of the test split of the probe campaign" if args.held_out else "any actor"
        description = {
            "sources": args.sources,
            "seed": SEED,
            "asked": args.items,
            "items": len(items),
            "actors": len({item.actor_id for item in items}),
            "drawn_from": kept,
            "unit": "whole actors: every item an actor has in the sources",
        }
        if kept_first:
            # Said with the sample: these actors were not drawn, they were asked for.
            description["kept"] = {
                "actors": kept_first,
                "items": sum(item.actor_id in kept_first for item in items),
                "why": args.keep_note,
            }
        write_corpus(work / CORPUS_FILE, items, {"sample": json.dumps(description)})
        write_vectors(work, np.concatenate(parts), keys.pop(), int(metas[0]["native_dims"]))
        np.save(work / ORIGIN_FILE, np.asarray(origin, dtype=np.int32))
        (work / SAMPLE_FILE).write_text(json.dumps(description, indent=1), encoding="utf-8")
    note = f"whole actors, {kept}, from {len(args.sources)} builds"
    runlog.record("sample", args.name, len(items), elapsed[0], note=note)
    log.info("%d items of %d actors in %.1fs", len(items), description["actors"], elapsed[0])


if __name__ == "__main__":
    main()

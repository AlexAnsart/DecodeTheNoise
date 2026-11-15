"""Merges vector caches filled on several machines into one.

A corpus split over machines leaves one cache per machine. Vectors already in the target are
skipped, so the command can be run again as parts arrive.

Run: uv run python -m pipelines.embed.merge --into <cache folder> <part folder> [<part folder>...]
"""

import argparse
import json
import logging
from pathlib import Path

from pipelines.embed.store import HASHES_FILE, META_FILE, VectorStore

log = logging.getLogger("embed.merge")

# Rows copied per write: 50,000 vectors of 768 values are about 150 MB as float32.
CHUNK = 50_000


def merge(into: Path, parts: list[Path]) -> int:
    """Copies the vectors `into` lacks from each part and returns how many that was."""
    key = json.loads((parts[0] / META_FILE).read_text(encoding="utf-8"))["key"]
    target = VectorStore(into, key)
    added = 0
    for folder in parts:
        part = VectorStore(folder, key)
        listed = (folder / HASHES_FILE).read_text(encoding="ascii").split()
        # A part interrupted between its two writes lists hashes whose rows are not on disk.
        unwritten = set(part.missing(listed))
        todo = target.missing([h for h in listed if h not in unwritten])
        for start in range(0, len(todo), CHUNK):
            chunk = todo[start : start + CHUNK]
            target.add(chunk, part.rows(chunk))
        added += len(todo)
        log.info("%s: %d vectors added", folder, len(todo))
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--into", type=Path, required=True)
    parser.add_argument("parts", type=Path, nargs="+")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    log.info("%d vectors added in total", merge(args.into, args.parts))


if __name__ == "__main__":
    main()

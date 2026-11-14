"""Draws the posts of one annotation round at random from the pool, split by split.

A round is a folder `data/probes/rounds/<round>/`. Its `items.jsonl` lists the posts with their
split and the reason they were drawn (`stratum`). Annotators never see those two fields.
A post drawn in an earlier round is never drawn again.

Run: uv run --group pipelines python -m pipelines.probes.sample --round p1 --train 240 --seed 1
"""

import argparse
import json
import logging
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from pipelines.paths import CORPUS_FILE, work_dir
from pipelines.probes.pool import PROBES, SPLITS, Pool, load_pool

log = logging.getLogger("probes.sample")

ROUNDS = PROBES / "rounds"
ITEMS_FILE = "items.jsonl"
RANDOM = "random"


@dataclass(frozen=True)
class RoundItem:
    key: str  # "<build>:<row in the build>"
    split: str
    stratum: str
    text: str


def round_dir(name: str) -> Path:
    return ROUNDS / name


def read_jsonl(path: Path) -> list[dict]:
    """One object per line. A post may hold a Unicode line separator, which `splitlines`
    would cut on: only "\n" ends a line here."""
    lines = path.read_text(encoding="utf-8").split("\n")
    return [json.loads(line) for line in lines if line]


def read_items(name: str) -> list[RoundItem]:
    return [RoundItem(**row) for row in read_jsonl(round_dir(name) / ITEMS_FILE)]


def write_items(name: str, items: list[RoundItem]) -> None:
    folder = round_dir(name)
    if (folder / ITEMS_FILE).exists():
        raise FileExistsError(f"round {name} already has its items: a round is never redrawn")
    folder.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(asdict(item), ensure_ascii=False) + "\n" for item in items)
    (folder / ITEMS_FILE).write_text(text, encoding="utf-8")


def drawn_keys() -> set[str]:
    """Every post already in a round."""
    if not ROUNDS.exists():
        return set()
    return {row["key"] for path in ROUNDS.glob(f"*/{ITEMS_FILE}") for row in read_jsonl(path)}


def keys_of(pool: Pool, rows: np.ndarray) -> list[str]:
    return [f"{pool.builds[pool.shard[r]]}:{pool.idx[r]}" for r in rows]


def fetch_texts(keys: list[str]) -> dict[str, str]:
    by_build: dict[str, list[int]] = {}
    for key in keys:
        build, idx = key.rsplit(":", 1)
        by_build.setdefault(build, []).append(int(idx))
    texts: dict[str, str] = {}
    for build, rows in by_build.items():
        path = work_dir(build) / CORPUS_FILE
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        for start in range(0, len(rows), 500):
            chunk = rows[start : start + 500]
            marks = ",".join("?" * len(chunk))
            query = f"SELECT idx, text FROM items WHERE idx IN ({marks})"  # noqa: S608
            texts.update({f"{build}:{i}": t for i, t in con.execute(query, chunk)})
        con.close()
    return texts


def draw(pool: Pool, split: str, n: int, rng: np.random.Generator, taken: set[str]) -> list[str]:
    """`n` kept posts of `split`, uniformly at random, none of them in `taken`."""
    rows = np.flatnonzero(pool.keep & (pool.split == SPLITS.index(split)))
    picked: list[str] = []
    for key in keys_of(pool, rng.permutation(rows)[: n + len(taken)]):
        if key not in taken and len(picked) < n:
            picked.append(key)
    return picked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", required=True)
    parser.add_argument("--seed", type=int, required=True)
    for split in SPLITS:
        parser.add_argument(f"--{split}", type=int, default=0)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    pool = load_pool()
    rng = np.random.default_rng(args.seed)
    taken = drawn_keys()
    wanted = {split: getattr(args, split) for split in SPLITS}
    keys = {split: draw(pool, split, n, rng, taken) for split, n in wanted.items() if n}
    texts = fetch_texts([key for group in keys.values() for key in group])
    items = [RoundItem(k, split, RANDOM, texts[k]) for split, group in keys.items() for k in group]
    write_items(args.round, items)
    log.info("round %s: %s, seed %d", args.round, {s: len(g) for s, g in keys.items()}, args.seed)


if __name__ == "__main__":
    main()

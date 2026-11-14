"""Indexes the posts the probe campaign may draw from, and fixes the split of each one.

The split is by actor: a hash of the actor id, so it is the same in every shard and every run.
A text is kept once per split, and a text found in several splits is kept in one of them only:
a copy on each side of a split is leakage. Writes `data/probes/pool.npz`.

Run: uv run --group pipelines python -m pipelines.probes.pool --builds tweets-2026-s00 ...
"""

import argparse
import hashlib
import json
import logging
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pipelines.paths import CORPUS_FILE, DATA, work_dir

log = logging.getLogger("probes.pool")

PROBES = DATA / "probes"
POOL_FILE = PROBES / "pool.npz"
POOL_META = PROBES / "pool.json"
SPLITS = ("train", "calibration", "test")
# Share of actors per split, in hundredths: 60, 20, 20.
SPLIT_BOUNDS = (60, 80, 100)
SPLIT_SALT = "probes-split-v1"
# Longer posts are left out of the labelled samples: about one post in fifty.
MAX_CHARS = 1500
_URL = re.compile(r"https?://\S+")
_MENTION = re.compile(r"@\w+")
_DIGITS = re.compile(r"\d+")


@dataclass(frozen=True)
class Pool:
    builds: tuple[str, ...]
    shard: np.ndarray  # index into `builds`
    idx: np.ndarray  # row of the post in its build, the row of its vector
    split: np.ndarray  # index into SPLITS
    actor: np.ndarray  # 48 bits of the hashed actor id
    norm: np.ndarray  # hash of the normalised text
    chars: np.ndarray
    keep: np.ndarray  # one post per distinct text and split, no text across splits


def normalise(text: str) -> str:
    """The text with links, mentions and numbers masked: two copies of a template match."""
    masked = _DIGITS.sub("0", _MENTION.sub("@", _URL.sub(" ", text.lower())))
    return " ".join(masked.split())


def text_hash(text: str) -> int:
    digest = hashlib.blake2b(normalise(text).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little")


def split_of(actor_id: str) -> int:
    bucket = int(hashlib.sha1(f"{SPLIT_SALT}|{actor_id}".encode()).hexdigest()[:8], 16) % 100
    return next(i for i, bound in enumerate(SPLIT_BOUNDS) if bucket < bound)


def one_split_per_text(norm: np.ndarray, split: np.ndarray) -> np.ndarray:
    """True for the first post of each text in each split, in the one split a shared text keeps."""
    order = np.lexsort((np.arange(len(norm)), split, norm))
    n_sorted, s_sorted = norm[order], split[order]
    first_of_pair = np.ones(len(order), dtype=bool)
    first_of_pair[1:] = (n_sorted[1:] != n_sorted[:-1]) | (s_sorted[1:] != s_sorted[:-1])
    keep = np.zeros(len(norm), dtype=bool)
    pair_rows = order[first_of_pair]
    pair_norm = norm[pair_rows]
    starts = np.flatnonzero(np.r_[True, pair_norm[1:] != pair_norm[:-1]])
    counts = np.diff(np.r_[starts, len(pair_norm)])
    # A text present in several splits stays in one, picked by its own hash.
    pick = starts + (pair_norm[starts] % counts.astype(np.uint64)).astype(np.int64)
    keep[pair_rows[pick]] = True
    log.info("%d distinct texts, %d found in several splits", len(starts), int((counts > 1).sum()))
    return keep


def read_build(name: str) -> tuple[np.ndarray, ...]:
    path = work_dir(name) / CORPUS_FILE
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    rows = con.execute("SELECT idx, actor_id, text FROM items ORDER BY idx")
    idx, split, actor, norm, chars = [], [], [], [], []
    for row_idx, actor_id, text in rows:
        idx.append(row_idx)
        split.append(split_of(actor_id))
        actor.append(int(actor_id, 16))
        norm.append(text_hash(text))
        chars.append(len(text))
    con.close()
    return (
        np.array(idx, dtype=np.int32),
        np.array(split, dtype=np.int8),
        np.array(actor, dtype=np.uint64),
        np.array(norm, dtype=np.uint64),
        np.array(chars, dtype=np.int32),
    )


def build_pool(builds: tuple[str, ...]) -> Pool:
    parts = []
    for number, name in enumerate(builds):
        columns = read_build(name)
        parts.append((np.full(len(columns[0]), number, dtype=np.int8), *columns))
        log.info("%s: %d posts", name, len(columns[0]))
    shard, idx, split, actor, norm, chars = (
        np.concatenate(col) for col in zip(*parts, strict=True)
    )
    keep = one_split_per_text(norm, split) & (chars <= MAX_CHARS)
    return Pool(builds, shard, idx, split, actor, norm, chars, keep)


def save_pool(pool: Pool) -> None:
    PROBES.mkdir(parents=True, exist_ok=True)
    arrays = {k: v for k, v in vars(pool).items() if k != "builds"}
    np.savez(POOL_FILE, **arrays)
    meta = {
        "builds": list(pool.builds),
        "posts": len(pool.idx),
        "kept": int(pool.keep.sum()),
        "max_chars": MAX_CHARS,
        "split_salt": SPLIT_SALT,
        "kept_per_split": {
            name: int((pool.keep & (pool.split == i)).sum()) for i, name in enumerate(SPLITS)
        },
        "too_long": int((pool.chars > MAX_CHARS).sum()),
    }
    POOL_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log.info("pool: %s", meta)


def load_pool(path: Path = POOL_FILE) -> Pool:
    builds = tuple(json.loads(POOL_META.read_text(encoding="utf-8"))["builds"])
    with np.load(path) as data:
        return Pool(builds, **{key: data[key] for key in data.files})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--builds", nargs="+", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    save_pool(build_pool(tuple(args.builds)))


if __name__ == "__main__":
    main()

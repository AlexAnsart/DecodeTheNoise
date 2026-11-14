"""The files of one workspace: its items, its vectors (float16 rows in point order), and the
last layout computed for it."""

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backend.map.schema import ZoneInfo

ITEMS_FILE = "items.sqlite"
VECTORS_FILE = "vectors.f16"
LAYOUT_FILE = "layout.npz"
EMBEDDING_KEY = "embedding_key"

# `idx` is the point of the map; null while the item waits to be embedded or is too short.
# `repost_of`, `urls` and `attrs` are the columns the map routes read for an item card.
SCHEMA = """
CREATE TABLE IF NOT EXISTS items(
    item_id TEXT PRIMARY KEY, idx INTEGER UNIQUE, actor_id TEXT, actor_name TEXT,
    text TEXT NOT NULL, created_at INTEGER, lang TEXT, kind TEXT, parent_id TEXT,
    parent_actor_id TEXT, repost_of TEXT, urls TEXT NOT NULL, source TEXT, meta TEXT NOT NULL,
    attrs TEXT NOT NULL, content_hash TEXT NOT NULL, received_at INTEGER NOT NULL,
    status TEXT NOT NULL, review TEXT);
CREATE INDEX IF NOT EXISTS items_status ON items(status, received_at);
CREATE INDEX IF NOT EXISTS items_actor ON items(actor_id, created_at);
CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
    text, tokenize='unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

PENDING, PLACED, SHORT = "pending", "placed", "short"


@dataclass(frozen=True)
class Layout:
    """Positions and zones of the first `len(pos3)` points, as the last refresh computed them."""

    epoch: int
    pos3: np.ndarray
    pos2: np.ndarray
    zone: np.ndarray  # uint16 per point
    centres: np.ndarray  # one unit vector per zone
    zones: tuple[ZoneInfo, ...]


def open_items(folder: Path) -> sqlite3.Connection:
    folder.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(folder / ITEMS_FILE, check_same_thread=False)
    with db:
        db.executescript(SCHEMA)
    return db


def read_vectors(folder: Path, dims: int) -> np.ndarray:
    path = folder / VECTORS_FILE
    if not path.exists():
        return np.zeros((0, dims), dtype=np.float32)
    stored = np.fromfile(path, dtype=np.float16)
    return stored[: len(stored) // dims * dims].reshape(-1, dims).astype(np.float32)


def truncate_vectors(folder: Path, rows: int, dims: int) -> None:
    path = folder / VECTORS_FILE
    if path.exists():
        with path.open("r+b") as out:
            out.truncate(rows * dims * 2)


def append_vectors(folder: Path, rows: np.ndarray) -> None:
    with (folder / VECTORS_FILE).open("ab") as out:
        out.write(rows.astype(np.float16).tobytes())


def write_vector(folder: Path, index: int, row: np.ndarray) -> None:
    with (folder / VECTORS_FILE).open("r+b") as out:
        out.seek(index * row.size * 2)
        out.write(row.astype(np.float16).tobytes())


def save_layout(folder: Path, layout: Layout) -> None:
    zones = json.dumps([zone.model_dump() for zone in layout.zones], ensure_ascii=False)
    # Written beside, then renamed: a crash never leaves half a layout.
    partial = folder / (LAYOUT_FILE + ".partial.npz")
    np.savez(
        partial,
        epoch=np.int64(layout.epoch),
        pos3=layout.pos3,
        pos2=layout.pos2,
        zone=layout.zone,
        centres=layout.centres,
        zones=np.array(zones),
    )
    partial.replace(folder / LAYOUT_FILE)


def load_layout(folder: Path) -> Layout | None:
    path = folder / LAYOUT_FILE
    if not path.exists():
        return None
    with np.load(path) as data:
        zones = tuple(ZoneInfo.model_validate(zone) for zone in json.loads(str(data["zones"])))
        return Layout(
            int(data["epoch"]), data["pos3"], data["pos2"], data["zone"], data["centres"], zones
        )


def delete_files(folder: Path) -> None:
    for name in (VECTORS_FILE, LAYOUT_FILE):
        (folder / name).unlink(missing_ok=True)

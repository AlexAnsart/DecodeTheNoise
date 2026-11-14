"""Rows of a workspace's item table. Every function expects the caller to hold `db_lock`."""

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from backend.analyze.place import beginning
from backend.analyze.schema import EMBED_BUDGET_CHARS, MIN_TEXT_CHARS
from backend.ingest.schema import ItemIn
from backend.workspace.files import PENDING, SHORT

_COLUMNS = "item_id, idx, actor_id, text, created_at, lang, content_hash, status, review"
_URL = re.compile(r"https?://\S+")
_VARIABLES = 500


@dataclass(frozen=True)
class Row:
    item_id: str
    idx: int | None
    actor_id: str | None
    text: str
    created_at: int | None  # milliseconds since the epoch
    lang: str | None
    content_hash: str
    status: str
    review: str | None  # a Review as JSON


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_long_enough(text: str) -> bool:
    """Same rule as the corpus the probes were fitted on: the text without its links."""
    return len(" ".join(_URL.sub(" ", text).split())) >= MIN_TEXT_CHARS


def embedded_text(text: str) -> str:
    """What the model reads of an item: a post in full, the beginning of a long text."""
    return beginning(text, EMBED_BUDGET_CHARS)


def to_datetime(milliseconds: float | None) -> datetime | None:
    if not milliseconds:
        return None
    return datetime.fromtimestamp(milliseconds / 1000, UTC)


def row_of(db: sqlite3.Connection, item_id: str) -> Row | None:
    found = db.execute(f"SELECT {_COLUMNS} FROM items WHERE item_id = ?", (item_id,)).fetchone()
    return Row(*found) if found else None


def rows_at(db: sqlite3.Connection, indices: list[int]) -> dict[int, Row]:
    """The items behind the given points."""
    out: dict[int, Row] = {}
    for start in range(0, len(indices), _VARIABLES):
        part = indices[start : start + _VARIABLES]
        marks = ",".join("?" * len(part))
        for found in db.execute(f"SELECT {_COLUMNS} FROM items WHERE idx IN ({marks})", part):
            out[found[1]] = Row(*found)
    return out


def known_hashes(db: sqlite3.Connection, item_ids: list[str]) -> dict[str, tuple[str, int | None]]:
    """For the ids already stored: the hash of their text and their point, if they have one."""
    out: dict[str, tuple[str, int | None]] = {}
    for start in range(0, len(item_ids), _VARIABLES):
        part = item_ids[start : start + _VARIABLES]
        marks = ",".join("?" * len(part))
        query = f"SELECT item_id, content_hash, idx FROM items WHERE item_id IN ({marks})"
        for item_id, digest, idx in db.execute(query, part):
            out[item_id] = (digest, idx)
    return out


def pending_rows(db: sqlite3.Connection, limit: int, only: str | None = None) -> list[Row]:
    """Items waiting to be embedded, oldest first; or the one item asked for."""
    if only is not None:
        query = f"SELECT {_COLUMNS} FROM items WHERE status = ? AND item_id = ?"
        return [Row(*found) for found in db.execute(query, (PENDING, only))]
    query = f"SELECT {_COLUMNS} FROM items WHERE status = ? ORDER BY received_at, rowid LIMIT ?"
    return [Row(*found) for found in db.execute(query, (PENDING, limit))]


def count_pending(db: sqlite3.Connection) -> int:
    return int(db.execute("SELECT count(*) FROM items WHERE status = ?", (PENDING,)).fetchone()[0])


def upsert(db: sqlite3.Connection, item: ItemIn, placed: bool, now: int) -> None:
    """Writes the item as sent. A point keeps its place: only its text is embedded again."""
    text = item.text.strip()
    attrs = {"kind": item.kind, "source": item.source, "actor": item.actor_name, **item.meta}
    status = PENDING if placed or is_long_enough(text) else SHORT
    db.execute(
        "INSERT INTO items(item_id, actor_id, actor_name, text, created_at, lang, kind, "
        "parent_id, parent_actor_id, repost_of, urls, source, meta, attrs, content_hash, "
        "received_at, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT (item_id) DO UPDATE SET actor_id = excluded.actor_id, "
        "actor_name = excluded.actor_name, text = excluded.text, "
        "created_at = excluded.created_at, lang = excluded.lang, kind = excluded.kind, "
        "parent_id = excluded.parent_id, parent_actor_id = excluded.parent_actor_id, "
        "repost_of = excluded.repost_of, urls = excluded.urls, source = excluded.source, "
        "meta = excluded.meta, attrs = excluded.attrs, content_hash = excluded.content_hash, "
        "received_at = excluded.received_at, status = excluded.status, review = NULL",
        (
            item.id,
            item.actor_id,
            item.actor_name,
            text,
            int(item.created_at.timestamp() * 1000) if item.created_at else None,
            item.lang,
            item.kind,
            item.parent_id,
            item.parent_actor_id,
            item.parent_id if item.kind == "repost" else None,
            json.dumps(item.urls),
            item.source,
            json.dumps(item.meta, ensure_ascii=False),
            json.dumps({k: v for k, v in attrs.items() if v is not None}, ensure_ascii=False),
            content_hash(text),
            now,
            status,
        ),
    )

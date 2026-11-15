"""The normalised corpus of one build: `corpus.sqlite`, written by ingest, read by every step."""

import json
import sqlite3
from pathlib import Path

from pipelines.ingest.ira import Item, content_hash

SCHEMA = """
CREATE TABLE items(
    item_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, text TEXT NOT NULL, created_at INTEGER,
    lang TEXT, repost_of TEXT, urls TEXT NOT NULL,
    idx INTEGER NOT NULL UNIQUE, content_hash TEXT NOT NULL,
    category TEXT NOT NULL, post_type TEXT NOT NULL, followers INTEGER);
CREATE TABLE actors(
    actor_id TEXT PRIMARY KEY, n_items INTEGER NOT NULL, first_seen INTEGER, last_seen INTEGER);
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def _row(idx: int, item: Item) -> tuple[object, ...]:
    return (
        item.item_id,
        item.actor_id,
        item.text,
        item.created_at,
        item.lang,
        item.repost_of,
        json.dumps(list(item.urls)),
        idx,
        content_hash(item.text),
        item.category,
        item.post_type,
        item.followers,
    )


def write_corpus(path: Path, items: list[Item], meta: dict[str, str]) -> None:
    """`items` order is the point order of the map: row i gets `idx` i."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    with con:
        con.executescript(SCHEMA)
        con.executemany(
            "INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [_row(idx, item) for idx, item in enumerate(items)],
        )
        con.execute(
            "INSERT INTO actors SELECT actor_id, count(*), min(created_at), max(created_at) "
            "FROM items GROUP BY actor_id"
        )
        con.executemany("INSERT INTO meta VALUES (?, ?)", list(meta.items()))
    con.close()


def read_meta(path: Path) -> dict[str, str]:
    """What the step that wrote the corpus recorded about it: its dataset and the files read,
    or how it was drawn from other builds."""
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    meta = dict(con.execute("SELECT key, value FROM meta"))
    con.close()
    return meta


def read_corpus(path: Path) -> list[Item]:
    """Items in point order."""
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT item_id, actor_id, text, created_at, lang, repost_of, urls, category, post_type, "
        "followers FROM items ORDER BY idx"
    ).fetchall()
    con.close()
    return [
        Item(r[0], r[1], r[2], r[3], r[4], r[5], tuple(json.loads(r[6])), r[7], r[8], r[9])
        for r in rows
    ]

"""Writes `items.sqlite`: the content of every point, by point index, with a full-text index."""

import json
import sqlite3
from pathlib import Path

from pipelines.ingest.ira import Item

SCHEMA = """
CREATE TABLE items(
    idx INTEGER PRIMARY KEY, item_id TEXT NOT NULL, actor_id TEXT NOT NULL, text TEXT NOT NULL,
    created_at INTEGER, lang TEXT, repost_of TEXT, urls TEXT NOT NULL, attrs TEXT NOT NULL);
CREATE VIRTUAL TABLE items_fts USING fts5(
    text, content='items', content_rowid='idx', tokenize='unicode61 remove_diacritics 2');
"""


def display_attrs(item: Item, hidden: frozenset[str] = frozenset()) -> dict[str, str | int | None]:
    attrs = {"category": item.category, "post_type": item.post_type, "followers": item.followers}
    return {key: value for key, value in attrs.items() if key not in hidden}


def write_items(path: Path, items: list[Item], hidden: frozenset[str] = frozenset()) -> None:
    """`hidden` names the attributes left out of the cards: those every item shares."""
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    with con:
        con.executescript(SCHEMA)
        con.executemany(
            "INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?)",
            [
                (
                    idx,
                    item.item_id,
                    item.actor_id,
                    item.text,
                    item.created_at,
                    item.lang,
                    item.repost_of,
                    json.dumps(list(item.urls)),
                    json.dumps(display_attrs(item, hidden)),
                )
                for idx, item in enumerate(items)
            ],
        )
        # The index holds no copy of the text: it is rebuilt from the table it points at.
        con.execute("INSERT INTO items_fts(items_fts) VALUES ('rebuild')")
    con.execute("VACUUM")
    con.close()

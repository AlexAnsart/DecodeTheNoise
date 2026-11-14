"""Word search over item texts: one byte per point, 1 for a hit."""

import re
import sqlite3

import numpy as np

from backend.map.store import MapBuild

_WORD = re.compile(r"[\w#@]+", re.UNICODE)


def fts_query(text: str) -> str | None:
    """Every word must be present; the last one matches as a prefix, as the user is still typing."""
    words = _WORD.findall(text)
    if not words:
        return None
    quoted = [f'"{word}"' for word in words]
    quoted[-1] += "*"
    return " AND ".join(quoted)


def text_hits(build: MapBuild, text: str) -> np.ndarray:
    mask = np.zeros(build.manifest.n, dtype=np.uint8)
    query = fts_query(text)
    if query is None:
        return mask
    with build.items_lock:
        try:
            rows = build.items.execute(
                "SELECT rowid FROM items_fts WHERE items_fts MATCH ?", (query,)
            ).fetchall()
        except sqlite3.OperationalError:
            # A token the FTS grammar still rejects: no hit rather than a server error.
            return mask
    if rows:
        mask[np.fromiter((row[0] for row in rows), dtype=np.int64, count=len(rows))] = 1
    return mask

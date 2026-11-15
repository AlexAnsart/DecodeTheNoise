"""Reviews already paid for, kept by a hash of the question: the model, the prompt version, the
prompt and the text. The same question is never sent to the LLM twice, whoever asks it."""

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

REVIEWS_FILE = "reviews.sqlite"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews(
    key TEXT PRIMARY KEY, body TEXT NOT NULL, created_at TEXT NOT NULL);
"""


class ReviewCache:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.executescript(_SCHEMA)

    def get(self, key: str) -> str | None:
        with self._lock:
            row = self._db.execute("SELECT body FROM reviews WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def put(self, key: str, body: str) -> None:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        with self._lock, self._db:
            self._db.execute("INSERT OR REPLACE INTO reviews VALUES (?, ?, ?)", (key, body, now))

    def close(self) -> None:
        with self._lock:
            self._db.close()

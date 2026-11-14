"""Which key opens which workspace: the keys (hashed), the settings and the daily usage."""

import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from backend.accounts.keys import hash_key, new_key, new_workspace_id
from backend.workspace.schema import WorkspaceSettings

SCHEMA = """
CREATE TABLE IF NOT EXISTS workspaces(
    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, settings TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS keys(
    key_hash TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS usage(
    workspace_id TEXT NOT NULL, day TEXT NOT NULL, kind TEXT NOT NULL, count INTEGER NOT NULL,
    PRIMARY KEY (workspace_id, day, kind));
"""


@dataclass(frozen=True)
class Account:
    id: str
    created_at: str
    settings: WorkspaceSettings


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


class AccountStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.executescript(SCHEMA)

    def _account(self, where: str, value: str) -> Account | None:
        with self._lock:
            row = self._db.execute(
                f"SELECT id, created_at, settings FROM workspaces WHERE {where}", (value,)
            ).fetchone()
        if row is None:
            return None
        return Account(row[0], row[1], WorkspaceSettings.model_validate_json(row[2]))

    def by_id(self, workspace_id: str) -> Account | None:
        return self._account("id = ?", workspace_id)

    def by_key(self, key: str) -> Account | None:
        return self._account(
            "id = (SELECT workspace_id FROM keys WHERE key_hash = ?)", hash_key(key)
        )

    def create(self) -> tuple[Account, str]:
        """A new workspace and its key."""
        account = Account(new_workspace_id(), _now(), WorkspaceSettings())
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO workspaces VALUES (?, ?, ?)",
                (account.id, account.created_at, account.settings.model_dump_json()),
            )
        return account, self.rotate_key(account.id)

    def rotate_key(self, workspace_id: str) -> str:
        """The key of the workspace stops working; a new one replaces it."""
        key = new_key()
        with self._lock, self._db:
            self._db.execute("DELETE FROM keys WHERE workspace_id = ?", (workspace_id,))
            self._db.execute(
                "INSERT INTO keys VALUES (?, ?, ?)", (hash_key(key), workspace_id, _now())
            )
        return key

    def save_settings(self, workspace_id: str, settings: WorkspaceSettings) -> None:
        with self._lock, self._db:
            self._db.execute(
                "UPDATE workspaces SET settings = ? WHERE id = ?",
                (settings.model_dump_json(), workspace_id),
            )

    def used_today(self, workspace_id: str, kind: str) -> int:
        with self._lock:
            row = self._db.execute(
                "SELECT count FROM usage WHERE workspace_id = ? AND day = ? AND kind = ?",
                (workspace_id, _today(), kind),
            ).fetchone()
        return int(row[0]) if row else 0

    def use(self, workspace_id: str, kind: str, count: int = 1) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO usage VALUES (?, ?, ?, ?) ON CONFLICT (workspace_id, day, kind) "
                "DO UPDATE SET count = count + excluded.count",
                (workspace_id, _today(), kind, count),
            )

    def close(self) -> None:
        self._db.close()

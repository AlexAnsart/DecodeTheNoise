"""The workspaces loaded in memory. One is read from its files the first time it is used."""

import threading
import time
from collections.abc import Callable
from pathlib import Path

from backend.accounts.store import Account, AccountStore
from backend.workspace.load import load_workspace
from backend.workspace.state import Workspace

# Beyond this many, the ones nobody used for a while are closed; they load again on demand.
MAX_LOADED = 48
IDLE_SECONDS = 600.0


class Workspaces:
    def __init__(
        self,
        root: Path,
        accounts: AccountStore,
        embedding_key: str,
        dims: int,
        on_load: Callable[[Workspace], None] | None = None,
    ) -> None:
        self._root = root
        self._accounts = accounts
        self._embedding_key = embedding_key
        self._dims = dims
        # Called with a workspace just read from disk: unfinished work is taken up again.
        self.on_load = on_load
        self._loaded: dict[str, Workspace] = {}
        self._lock = threading.Lock()

    def of(self, account: Account) -> Workspace:
        with self._lock:
            workspace = self._loaded.get(account.id)
            if workspace is None:
                workspace = load_workspace(
                    account, self._root / account.id, self._embedding_key, self._dims
                )
                self._loaded[account.id] = workspace
                self._close_idle()
                fresh = True
            else:
                fresh = False
            workspace.last_used = time.monotonic()
        if fresh and self.on_load is not None:
            self.on_load(workspace)
        return workspace

    def get(self, workspace_id: str) -> Workspace | None:
        """By id, for background work. None when the workspace no longer exists."""
        with self._lock:
            workspace = self._loaded.get(workspace_id)
        if workspace is not None:
            return workspace
        account = self._accounts.by_id(workspace_id)
        return self.of(account) if account else None

    def loaded(self) -> list[Workspace]:
        with self._lock:
            return list(self._loaded.values())

    def _close_idle(self) -> None:
        if len(self._loaded) <= MAX_LOADED:
            return
        now = time.monotonic()
        for workspace_id, workspace in list(self._loaded.items()):
            busy = workspace.pending or workspace.refreshing or workspace.refresh_queued
            if not busy and now - workspace.last_used > IDLE_SECONDS:
                del self._loaded[workspace_id]
                workspace.close()

    def close(self) -> None:
        with self._lock:
            for workspace in self._loaded.values():
                workspace.close()
            self._loaded.clear()

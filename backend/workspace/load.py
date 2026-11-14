"""Reads a workspace back from its files: the items, the vectors, the last layout."""

import logging
from pathlib import Path

import numpy as np

from backend.accounts.store import Account
from backend.workspace.files import (
    EMBEDDING_KEY,
    PENDING,
    load_layout,
    read_vectors,
    truncate_vectors,
)
from backend.workspace.state import Workspace

logger = logging.getLogger(__name__)


def _stored_key(workspace: Workspace, current: str) -> str:
    """The embedding key the workspace's vectors were made with; set on first use."""
    with workspace.db_lock, workspace.db:
        query = "SELECT value FROM meta WHERE key = ?"
        row = workspace.db.execute(query, (EMBEDDING_KEY,)).fetchone()
        if row is None:
            workspace.db.execute("INSERT INTO meta VALUES (?, ?)", (EMBEDDING_KEY, current))
            return current
    return str(row[0])


def _repair(workspace: Workspace, on_disk: int) -> int:
    """Points the database and the vector file agree on. A crash between the two writes
    leaves one ahead of the other: the surplus is undone, and the items are embedded again."""
    with workspace.db_lock, workspace.db:
        placed = int(
            workspace.db.execute("SELECT count(*) FROM items WHERE idx IS NOT NULL").fetchone()[0]
        )
        points = min(placed, on_disk)
        if placed > points:
            workspace.db.execute("DELETE FROM items_fts WHERE rowid >= ?", (points,))
            workspace.db.execute(
                "UPDATE items SET idx = NULL, status = ? WHERE idx >= ?", (PENDING, points)
            )
    if on_disk > points:
        truncate_vectors(workspace.folder, points, workspace.dims)
    return points


def load_workspace(account: Account, folder: Path, embedding_key: str, dims: int) -> Workspace:
    workspace = Workspace(account, folder, embedding_key, dims)
    workspace.embedding_key = _stored_key(workspace, embedding_key)
    if workspace.embedding_key != embedding_key:
        # Its vectors come from another model: they are not read, and nothing is added to
        # them until the workspace is emptied.
        logger.warning("workspace %s was built with another embedding key", workspace.id)
        vectors = np.zeros((0, dims), dtype=np.float32)
    else:
        vectors = read_vectors(folder, dims)
        vectors = vectors[: _repair(workspace, len(vectors))]
    with workspace.db_lock:
        rows = workspace.db.execute(
            "SELECT actor_id, created_at FROM items WHERE idx IS NOT NULL ORDER BY idx"
        ).fetchall()[: len(vectors)]
        total, pending = workspace.db.execute(
            "SELECT count(*), coalesce(sum(status = ?), 0) FROM items", (PENDING,)
        ).fetchone()
    workspace.items = int(total)
    workspace.set_pending(int(pending))
    ts = np.array([row[1] or 0 for row in rows], dtype=np.float64)
    workspace.restore(vectors, ts, [row[0] for row in rows], load_layout(folder))
    logger.info("loaded workspace %s: %d points, %d pending", workspace.id, workspace.n, pending)
    return workspace

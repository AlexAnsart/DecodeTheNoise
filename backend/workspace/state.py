"""One workspace in memory: the vectors of its points, where they sit, who wrote them.

Points are only appended, so a point keeps its index for life. Every change is made under
`lock` and moves `version`, which is what tells a reader to fetch the map again.
"""

import sqlite3
import threading
import time
from pathlib import Path

import numpy as np

from backend.accounts.limits import LIMITS
from backend.accounts.store import Account
from backend.analyze.place import neighbour_weights, strongest
from backend.map.schema import NO_VALUE, ZoneInfo
from backend.map.store import MapBuild
from backend.workspace.actors import ActorIndex
from backend.workspace.files import Layout, delete_files, open_items
from backend.workspace.neighbours import NeighbourLists
from backend.workspace.schema import Limits, WorkspaceSettings
from pipelines.layout.pca import principal_axes
from pipelines.layout.scale import scale_layout

INITIAL_CAPACITY = 256
# Under this many points there is nothing to cluster: the points sit on their principal axes.
FIRST_REFRESH = 20
# A batch can outrun the first refresh. Up to this many points, the map waiting for it is laid
# on its principal axes again after each group of arrivals: a product of n rows by dims squared.
AXES_LIMIT = 5_000
NO_ACTOR = -1


class Workspace:
    def __init__(self, account: Account, folder: Path, embedding_key: str, dims: int) -> None:
        self.id = account.id
        self.created_at = account.created_at
        self.settings: WorkspaceSettings = account.settings
        self.folder = folder
        self.embedding_key = embedding_key
        self.dims = dims
        self.lock = threading.RLock()
        self.db: sqlite3.Connection = open_items(folder)
        self.db_lock = threading.Lock()
        self.version = int(time.time() * 1000)
        self.items = 0
        self.pending = 0
        # The batch being embedded: how many posts it held, and when it started to wait.
        self.batch_total = 0
        self.batch_started = 0.0
        # Why the embedding stopped advancing, and how many times in a row it failed.
        self.ingest_error: str | None = None
        self.ingest_failures = 0
        self.refreshing = False
        self.refresh_queued = False
        self.cached_build: MapBuild | None = None
        # The last few maps served, by version: a reader fetches the manifest, then the
        # buffers of that same version, and the map may have moved in between.
        self.recent_builds: dict[int, MapBuild] = {}
        self.last_used = time.monotonic()
        self._reset()

    @property
    def limits(self) -> Limits:
        return LIMITS

    def set_pending(self, pending: int) -> int:
        """Records how many posts wait. Returns the size of the batch that just finished,
        when this call is the one that emptied the queue; 0 otherwise."""
        added = pending - self.pending
        self.pending = pending
        if pending == 0:
            finished, self.batch_total = self.batch_total, 0
            return finished
        if self.batch_total == 0:
            self.batch_total, self.batch_started = pending, time.monotonic()
        elif added > 0:
            self.batch_total += added
        return 0

    def _reset(self) -> None:
        self.n = 0
        self.vectors = np.zeros((INITIAL_CAPACITY, self.dims), dtype=np.float32)
        self.pos3 = np.zeros((INITIAL_CAPACITY, 3), dtype=np.float32)
        self.pos2 = np.zeros((INITIAL_CAPACITY, 2), dtype=np.float32)
        self.ts = np.zeros(INITIAL_CAPACITY, dtype=np.float64)
        self.zone = np.full(INITIAL_CAPACITY, NO_VALUE, dtype=np.uint16)
        self.actor_row = np.full(INITIAL_CAPACITY, NO_ACTOR, dtype=np.int32)
        self.knn = NeighbourLists(INITIAL_CAPACITY)
        self.actors = ActorIndex(self.dims)
        self.zones: tuple[ZoneInfo, ...] = ()
        self.centres: np.ndarray | None = None
        self.epoch = 0
        self.points_covered = 0

    def _reserve(self, capacity: int) -> None:
        if capacity <= len(self.vectors):
            return
        size = max(capacity, 2 * len(self.vectors))

        def grown(array: np.ndarray, fill: float) -> np.ndarray:
            out = np.full((size, *array.shape[1:]), fill, dtype=array.dtype)
            out[: len(array)] = array
            return out

        self.vectors, self.pos3, self.pos2 = (
            grown(self.vectors, 0),
            grown(self.pos3, 0),
            grown(self.pos2, 0),
        )
        self.ts, self.zone = grown(self.ts, 0), grown(self.zone, NO_VALUE)
        self.actor_row = grown(self.actor_row, NO_ACTOR)
        self.knn.grow(size)

    def touch(self) -> None:
        self.version += 1

    def add_point(self, vector: np.ndarray, ts: float, actor_id: str | None) -> int:
        """Appends a point and sets it down among the points it resembles; returns its index."""
        index = self.n
        self._reserve(index + 1)
        scores = self.vectors[:index] @ vector
        self.vectors[index] = vector
        self.ts[index] = ts
        self.actor_row[index] = self.actors.add(actor_id, vector, ts) if actor_id else NO_ACTOR
        self.knn.add(index, scores)
        self.n = index + 1
        self._place(index, scores)
        return index

    def replace_point(self, index: int, vector: np.ndarray) -> None:
        """The text of a point changed: its vector is swapped, and it is set down again."""
        if self.actor_row[index] != NO_ACTOR:
            self.actors.replace(int(self.actor_row[index]), self.vectors[index].copy(), vector)
        self.vectors[index] = vector
        self.knn.rebuild(self.vectors[: self.n])
        scores = self.vectors[: self.n] @ vector
        scores[index] = -np.inf
        self._place(index, scores)

    def _place(self, index: int, scores: np.ndarray) -> None:
        """`scores` is the cosine of the point to the others (minus infinity for itself)."""
        if self.centres is None:
            self.zone[index] = NO_VALUE
            # Past the first few points the axes are no longer computed for each arrival: a
            # batch can outrun the first refresh, and its points then sit beside their neighbours.
            if self.n <= FIRST_REFRESH:
                self._lay_on_axes()
                return
        else:
            self.zone[index] = int(np.argmax(self.centres @ self.vectors[index]))
        order, top = strongest(scores, self.knn.k)
        if len(order):
            weights = neighbour_weights(top)
            self.pos3[index] = weights @ self.pos3[order]
            self.pos2[index] = weights @ self.pos2[order]

    def _lay_on_axes(self) -> None:
        """Before the first refresh: every point on the principal axes of the few there are."""
        if self.n < 2:
            self.pos3[: self.n] = 0
            self.pos2[: self.n] = 0
            return
        with np.errstate(invalid="ignore", divide="ignore"):
            coordinates, _ = principal_axes(self.vectors[: self.n], 3)
        self.pos3[: self.n] = scale_layout(coordinates)
        self.pos2[: self.n] = scale_layout(coordinates[:, :2])

    def settle_arrivals(self) -> None:
        """After a group of points was added: while no layout was computed yet, the whole map
        is laid on its principal axes, so that it shows its shape before the first refresh."""
        if self.centres is None and FIRST_REFRESH < self.n <= AXES_LIMIT:
            self._lay_on_axes()

    def restore(
        self,
        vectors: np.ndarray,
        ts: np.ndarray,
        actor_ids: list[str | None],
        layout: Layout | None,
    ) -> None:
        """Fills the arrays from the files in one go, when the workspace is loaded."""
        n = len(vectors)
        self._reserve(n)
        self.vectors[:n], self.ts[:n] = vectors, ts
        for index, actor_id in enumerate(actor_ids):
            if actor_id:
                self.actor_row[index] = self.actors.add(actor_id, vectors[index], float(ts[index]))
        self.n = n
        self.knn.rebuild(self.vectors[:n])
        if layout is not None and len(layout.pos3) <= n:
            self.apply_layout(layout)
        else:
            self._lay_on_axes()

    def apply_layout(self, layout: Layout) -> None:
        """Takes the positions and zones a refresh computed; points added since are set down
        again among their neighbours, in the new layout."""
        covered = len(layout.pos3)
        self.pos3[:covered], self.pos2[:covered] = layout.pos3, layout.pos2
        self.zone[:covered] = layout.zone
        self.centres, self.zones = layout.centres, layout.zones
        self.epoch, self.points_covered = layout.epoch, covered
        for index in range(covered, self.n):
            self._place(index, self.vectors[:index] @ self.vectors[index])

    def next_refresh_at(self) -> int:
        """Every `refresh_every` points, and every tenth of the map once it is larger."""
        if self.epoch == 0:
            return FIRST_REFRESH
        step = max(self.settings.refresh_every, self.points_covered // 10)
        return (self.points_covered // step + 1) * step

    def refresh_due(self) -> bool:
        return self.n >= self.next_refresh_at()

    def clear(self) -> None:
        """Forgets every item. The workspace, its key and its settings stay."""
        with self.lock:
            with self.db_lock, self.db:
                self.db.execute("DELETE FROM items")
                self.db.execute("DELETE FROM items_fts")
            delete_files(self.folder)
            self._reset()
            self.items = self.pending = self.batch_total = 0
            self.ingest_error, self.ingest_failures = None, 0
            self.touch()

    def close(self) -> None:
        with self.db_lock:
            self.db.close()

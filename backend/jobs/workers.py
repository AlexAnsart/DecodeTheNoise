"""Background work, one thread per kind so that a long layout or a slow LLM answer never holds
back the embedding of another workspace: batches to embed, maps to refresh, zones to name,
flagged items to review."""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable, Hashable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services import Services

logger = logging.getLogger(__name__)

_STOP = object()


class Worker:
    """Runs `handle(key)` for each key submitted, one at a time. A key already waiting is not
    queued twice."""

    def __init__(self, name: str, handle: Callable[[Hashable], None]) -> None:
        self._handle = handle
        self._queue: queue.Queue[object] = queue.Queue()
        self._waiting: set[Hashable] = set()
        self._lock = threading.Lock()
        # Jobs set to start after a wait: `join` counts them as work still to do.
        self._delayed = 0
        self._none_delayed = threading.Condition(self._lock)
        self._thread = threading.Thread(target=self._run, name=f"noisemap-{name}", daemon=True)
        self._thread.start()

    def submit(self, key: Hashable) -> None:
        with self._lock:
            if key in self._waiting:
                return
            self._waiting.add(key)
        self._queue.put(key)

    def submit_later(self, key: Hashable, seconds: float) -> None:
        """Queues the key after a wait: how a job that failed is tried again."""

        def fire() -> None:
            self.submit(key)
            with self._none_delayed:
                self._delayed -= 1
                self._none_delayed.notify_all()

        with self._lock:
            self._delayed += 1
        timer = threading.Timer(seconds, fire)
        timer.daemon = True
        timer.start()

    def _run(self) -> None:
        while True:
            key = self._queue.get()
            if key is _STOP:
                return
            with self._lock:
                self._waiting.discard(key)
            try:
                self._handle(key)
            except Exception:
                # One failed job must not stop the thread that serves every workspace.
                logger.exception("background job failed for %r", key)
            finally:
                self._queue.task_done()

    def join(self, delayed: bool = True) -> None:
        """Returns when nothing is queued or running, the jobs that jobs queued included; and,
        unless `delayed` is false, when no job is set to start later either."""
        while True:
            if delayed:
                with self._none_delayed:
                    self._none_delayed.wait_for(lambda: self._delayed == 0)
            self._queue.join()
            with self._lock:
                if (not delayed or self._delayed == 0) and self._queue.unfinished_tasks == 0:
                    return

    def stop(self) -> None:
        self._queue.put(_STOP)
        self._thread.join(timeout=5.0)


class Jobs:
    def __init__(self, services: Services) -> None:
        # Imported here: each job module needs `Services`, which holds these workers.
        from backend.ingest.background import embed_pending
        from backend.refresh.job import refresh_workspace
        from backend.refresh.naming import name_zones
        from backend.review.job import review_flagged

        self.ingest = Worker("ingest", lambda key: embed_pending(services, str(key)))
        self.refresh = Worker("refresh", lambda key: refresh_workspace(services, str(key)))
        self.names = Worker("names", lambda key: name_zones(services, str(key)))
        self.review = Worker("review", lambda key: review_flagged(services, key))
        self._all = (self.ingest, self.refresh, self.names, self.review)

    def join(self, delayed: bool = True) -> None:
        """Returns when every background job is done. A job can queue another (an embedding
        queues a refresh, a refresh queues names), so the round is made twice."""
        for worker in (*self._all, *self._all):
            worker.join(delayed)

    def stop(self) -> None:
        for worker in self._all:
            worker.stop()

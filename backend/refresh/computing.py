"""The process that computes layouts: one, apart from the API, at the lowest priority.

UMAP compiles for about a minute the first time it runs and keeps a core busy while it works.
Inside the API process that starved everything else on the two cores of the server: measured
there, posts were embedded at 1 a second instead of 8 while it compiled, and a search took 7
seconds. In a process of its own, at the lowest priority, a layout only takes the processor
time nothing else wants, and the requests never wait for it.

One process, one task at a time: the compiled code under UMAP is also not safe to run from
two threads at once (it gave corrupted neighbour indices when a refresh met the start-up
compilation).
"""

import logging
import multiprocessing
import os
import threading
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from typing import Protocol

logger = logging.getLogger(__name__)

LOWEST_PRIORITY = 19


class Computing(Protocol):
    """Where the heavy computations of a refresh run."""

    def run[T](self, function: Callable[..., T], *args: object) -> T: ...

    def start(self, function: Callable[..., object], *args: object) -> None: ...

    def close(self) -> None: ...


def _settle() -> None:
    """Runs once in the computing process, before any task."""
    # One core at most: the other one stays for the embedding model.
    os.environ.setdefault("NUMBA_NUM_THREADS", "1")
    if hasattr(os, "nice"):
        os.nice(LOWEST_PRIORITY)


class ComputingProcess:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pool = self._new_pool()

    @staticmethod
    def _new_pool() -> ProcessPoolExecutor:
        # A fresh interpreter, not a copy of the API process and its threads.
        return ProcessPoolExecutor(
            max_workers=1, mp_context=multiprocessing.get_context("spawn"), initializer=_settle
        )

    def run[T](self, function: Callable[..., T], *args: object) -> T:
        """The result of `function(*args)`, computed in the other process. `function` is a
        module-level function, and what it takes and returns can be pickled."""
        with self._lock:
            pool = self._pool
        try:
            return pool.submit(function, *args).result()
        except BrokenProcessPool:
            # The process died (killed for memory, most likely): a new one takes over, once.
            logger.exception("the computing process died: starting another")
            with self._lock:
                if self._pool is pool:
                    self._pool = self._new_pool()
                pool = self._pool
            return pool.submit(function, *args).result()

    def start(self, function: Callable[..., object], *args: object) -> None:
        """Queues a task nobody waits for: the compilation at start-up."""
        with self._lock:
            self._pool.submit(function, *args)

    def close(self) -> None:
        with self._lock:
            self._pool.shutdown(wait=False, cancel_futures=True)

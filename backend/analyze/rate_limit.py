"""A per-client rate limit kept in memory: the route is public and the server is small."""

import time
from collections import deque
from collections.abc import Callable
from threading import Lock

from fastapi import Request

# Beyond this many clients on record, the ones with nothing left in their window are dropped.
_SWEEP_ABOVE = 10_000


class RateLimiter:
    """At most `limit` requests per `window` seconds for each client."""

    def __init__(
        self, limit: int, window: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.limit = limit
        self._window = window
        self._clock = clock
        self._seen: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, client: str) -> bool:
        now = self._clock()
        with self._lock:
            if len(self._seen) > _SWEEP_ABOVE:
                self._sweep(now)
            times = self._seen.setdefault(client, deque())
            while times and now - times[0] >= self._window:
                times.popleft()
            if len(times) >= self.limit:
                return False
            times.append(now)
            return True

    def _sweep(self, now: float) -> None:
        stale = [
            c for c, times in self._seen.items() if not times or now - times[-1] >= self._window
        ]
        for client in stale:
            del self._seen[client]


def client_address(request: Request) -> str:
    """The first hop of `X-Forwarded-For` when a proxy set it, else the peer address."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

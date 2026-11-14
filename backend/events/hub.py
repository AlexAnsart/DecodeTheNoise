"""Tells the open dashboards of a workspace that it changed. Jobs publish from their threads;
subscribers wait on the event loop. A subscriber only ever holds the latest state."""

import asyncio
import threading


class Subscriber:
    def __init__(self) -> None:
        self.event = asyncio.Event()
        self.latest: str | None = None

    def put(self, payload: str) -> None:
        self.latest = payload
        self.event.set()


class Hub:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: dict[str, set[Subscriber]] = {}
        self._lock = threading.Lock()

    def attach(self, loop: asyncio.AbstractEventLoop) -> None:
        """The loop the subscribers wait on; called once, at start-up."""
        self._loop = loop

    def subscribe(self, workspace_id: str) -> Subscriber:
        subscriber = Subscriber()
        with self._lock:
            self._subscribers.setdefault(workspace_id, set()).add(subscriber)
        return subscriber

    def unsubscribe(self, workspace_id: str, subscriber: Subscriber) -> None:
        with self._lock:
            watching = self._subscribers.get(workspace_id)
            if watching is None:
                return
            watching.discard(subscriber)
            if not watching:
                del self._subscribers[workspace_id]

    def publish(self, workspace_id: str, payload: str) -> None:
        """From any thread. Without a watcher it costs a dictionary lookup."""
        with self._lock:
            targets = list(self._subscribers.get(workspace_id, ()))
        if self._loop is None:
            return
        for subscriber in targets:
            self._loop.call_soon_threadsafe(subscriber.put, payload)

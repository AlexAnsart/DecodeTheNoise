"""One line per step run, kept for the write-up of what ran where and how long it took."""

import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from pipelines.paths import RUN_LOG

MACHINE = "laptop Snapdragon X, CPU"


def record(step: str, build: str, items: int, seconds: float, machine: str = MACHINE) -> None:
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "step": step,
        "build": build,
        "machine": machine,
        "items": items,
        "seconds": round(seconds, 1),
    }
    with RUN_LOG.open("a", encoding="utf-8") as out:
        out.write(json.dumps(line) + "\n")


@contextmanager
def timed() -> Iterator[list[float]]:
    """Yields a one-element list filled with the elapsed seconds on exit."""
    elapsed = [0.0]
    start = time.perf_counter()
    try:
        yield elapsed
    finally:
        elapsed[0] = time.perf_counter() - start

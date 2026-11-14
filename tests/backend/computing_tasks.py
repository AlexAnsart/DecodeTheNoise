"""Tasks run in the computing process by its test: module-level, so that they can be pickled."""

import os
import time


def spend(seconds: float) -> tuple[float, float, int]:
    """When the task started and ended, and the process it ran in."""
    started = time.time()
    time.sleep(seconds)
    return started, time.time(), os.getpid()


def die() -> None:
    os._exit(1)

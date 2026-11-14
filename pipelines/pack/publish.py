"""Makes a build the one the server loads, without ever leaving a half-copied folder behind."""

import shutil
from pathlib import Path

from pipelines.paths import build_dir

CURRENT = "current"


def publish_as_current(build: Path) -> None:
    """Copies `build` aside, then swaps it in by renaming.

    If a running server still holds files of the old folder (Windows refuses the rename), this
    raises and `current` stays the old, complete build: stop the server and run pack again.
    """
    current = build_dir(CURRENT)
    staged = build_dir(CURRENT + ".new")
    retired = build_dir(CURRENT + ".old")
    shutil.rmtree(staged, ignore_errors=True)
    shutil.rmtree(retired, ignore_errors=True)
    shutil.copytree(build, staged)
    if current.exists():
        current.rename(retired)
    staged.rename(current)
    shutil.rmtree(retired, ignore_errors=True)

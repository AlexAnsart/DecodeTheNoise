"""Files of the brief benchmark under `data/datasets/brief-bench/`, and how they are read.

The benchmark holds real posts (organic pools of the 2026 sample) and synthetic posts written
from known briefs. Nothing here is served: it feeds the three tests of `docs/brief-recovery/`.
"""

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from pipelines.paths import DATA

NAME = "brief-bench"
BENCH = DATA / "datasets" / NAME
POOLS_FILE = BENCH / "pools.jsonl"
POOLS_EXTRA_FILE = BENCH / "pools-extra.jsonl"
TOPICS_FILE = BENCH / "topics.json"
BRIEFS_FILE = BENCH / "briefs.json"
TASKS_DIR = BENCH / "tasks"
WRITTEN_DIR = BENCH / "written"
POSTS_FILE = BENCH / "posts.jsonl"
# Posts a second model wrote from the true briefs of the held-out topics (written by test 3).
LOOP_POSTS_FILE = BENCH / "loop-posts.jsonl"
# Results are small and committed, beside the write-up that reads them.
RESULTS = Path("docs") / "brief-recovery" / "results"
SEED = 20261114


def read_jsonl(path: Path) -> Iterator[dict[str, object]]:
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_result(name: str, payload: dict[str, object]) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{name}.json"
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path

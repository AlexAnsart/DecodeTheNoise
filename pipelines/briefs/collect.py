"""Gathers what the writers produced into `posts.jsonl`, one synthetic post per line.

A writing task is one context. Posts of a `shared` task are dealt to the actors at random: the
operator wrote them in one go and spread them over the accounts.

Run: uv run --group pipelines python -m pipelines.briefs.collect
"""

import json
import logging
import random
from pathlib import Path

from pydantic import BaseModel, ValidationError

from pipelines.briefs.bench import BENCH, BRIEFS_FILE, POSTS_FILE, SEED, WRITTEN_DIR, write_jsonl
from pipelines.briefs.design import ACTORS
from pipelines.datasets.manifest import Dataset, record
from pipelines.ingest.ira import hashed

log = logging.getLogger("briefs.collect")

WRITER = "claude-haiku-5.5 (Claude Code subagent, one context per task)"
MAX_CHARS = 600
# A task that returned fewer posts than this share of what was asked is asked a second time.
MIN_SHARE = 0.9
# Its subject stayed a real policy debate after the fictional rewrite: no post is kept on it.
DROPPED_TOPICS = ("t02",)
# Tasks a writer declined or botched, asked once more in a new context (see docs/brief-recovery).
SECOND_ASK_FILE = BENCH / "second-ask.json"


class Written(BaseModel):
    task: str
    posts: list[str]


def clean(posts: list[str]) -> list[str]:
    """Stripped, non-empty, of a plausible length, without exact repeats; order kept."""
    kept = dict.fromkeys(" ".join(post.split()) for post in posts)
    return [post for post in kept if 0 < len(post) <= MAX_CHARS]


def read_written(path: Path) -> Written | None:
    try:
        return Written.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValidationError, OSError) as error:
        log.warning("%s is unreadable: %s", path.name, error)
        return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    design = json.loads(BRIEFS_FILE.read_text(encoding="utf-8"))
    briefs = {brief["id"]: brief for brief in design["briefs"]}
    rng = random.Random(SEED)
    second_ask = (
        set(json.loads(SECOND_ASK_FILE.read_text("utf-8"))) if SECOND_ASK_FILE.exists() else set()
    )
    rows: list[dict[str, object]] = []
    redo: list[str] = []
    for task_id, brief_id in design["tasks"].items():
        brief = briefs[brief_id]
        if brief["topic"] in DROPPED_TOPICS:
            continue
        asked = json.loads((BENCH / "tasks" / f"{task_id}.json").read_text("utf-8"))["n_posts"]
        path = WRITTEN_DIR / f"{task_id}.json"
        written = read_written(path) if path.exists() else None
        posts = clean(written.posts) if written else []
        if len(posts) < MIN_SHARE * asked:
            redo.append(task_id)
            continue
        posts = posts[:asked]
        mode, _, tail = task_id.partition("-")
        # Dealt at random for a shared task, the task's own actor otherwise, none for the bench.
        deal = [i % ACTORS for i in range(len(posts))]
        rng.shuffle(deal)
        for index, text in enumerate(posts):
            actor = ""
            if mode == "shared":
                actor = f"{brief['topic']}-shared-a{deal[index]}"
            elif mode != "bench":
                actor = f"{mode}-{tail}"
            rows.append(
                {
                    "id": hashed(f"{task_id}:{index}", 16),
                    "task": task_id,
                    "mode": mode,
                    "actor": actor,
                    "text": text,
                    "writer": WRITER,
                    "synthetic": True,
                    "second_ask": task_id in second_ask,
                    "brief": brief_id,
                    **{k: brief[k] for k in ("set", "topic", "split")},
                    **{k: brief[k] for k in ("stance", "persona", "tone", "format")},
                }
            )
    written_count = write_jsonl(POSTS_FILE, rows)
    (BENCH / "redo.json").write_text(json.dumps(redo), encoding="utf-8")
    record(
        Dataset(
            name="brief-bench",
            source="generated: " + WRITER,
            licence="MIT (synthetic posts); organic pools follow tweets-sample-2026",
            fetch="uv run --group pipelines python -m pipelines.briefs.collect",
            folder=BENCH,
            files=(BRIEFS_FILE, POSTS_FILE),
        )
    )
    log.info(
        "%d posts from %d tasks; %d tasks without posts",
        written_count,
        len({row["task"] for row in rows}),
        len(redo),
    )


if __name__ == "__main__":
    main()

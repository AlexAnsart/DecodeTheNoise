"""Draws the briefs of the benchmark from the topics, and the writing task of each context.

Bench briefs: ten per topic, every level of every field as evenly as ten slots allow, each
field shuffled on its own so that none can be guessed from the topic or from another field.
Twin briefs: one per topic, written three times, once per way of running the accounts.

Run: uv run --group pipelines python -m pipelines.briefs.design
"""

import dataclasses
import json
import logging
import random

from pipelines.briefs.bench import BRIEFS_FILE, SEED, TASKS_DIR, TOPICS_FILE
from pipelines.briefs.fields import (
    AGES,
    HABITS,
    LEVELS,
    PLACES,
    Brief,
    account_sketch,
    operator_prompt,
)

log = logging.getLogger("briefs.design")

BENCH_TOPICS = 16
TEST_TOPICS = 6
BRIEFS_PER_TOPIC = 10
BENCH_POSTS = 32
ACTORS = 6
POSTS_PER_ACTOR = 8
MODES = ("shared", "solo", "persona")


def balanced(levels: tuple[str, ...], slots: int, offset: int, rng: random.Random) -> list[str]:
    """`slots` values, each level as often as the others; `offset` rotates who gets the extras."""
    turned = levels[offset % len(levels) :] + levels[: offset % len(levels)]
    values = [turned[i % len(turned)] for i in range(slots)]
    rng.shuffle(values)
    return values


def bench_briefs(topics: list[dict[str, object]], rng: random.Random) -> list[Brief]:
    briefs: list[Brief] = []
    for index, topic in enumerate(topics[:BENCH_TOPICS]):
        # Two identical briefs in one topic could not be told apart: draw again.
        columns: dict[str, list[str]] = {}
        while len(set(zip(*columns.values(), strict=True))) < BRIEFS_PER_TOPIC:
            columns = {
                name: balanced(levels, BRIEFS_PER_TOPIC, index, rng)
                for name, levels in LEVELS.items()
            }
        for slot in range(BRIEFS_PER_TOPIC):
            fields = {name: values[slot] for name, values in columns.items()}
            briefs.append(make_brief(f"{topic['code']}-b{slot:02d}", "bench", index, topic, fields))
    return briefs


def make_brief(
    brief_id: str, kind: str, index: int, topic: dict[str, object], fields: dict[str, str]
) -> Brief:
    split = "" if kind == "twin" else ("test" if index < TEST_TOPICS else "dev")
    return Brief(
        id=brief_id,
        set=kind,
        topic=str(topic["code"]),
        split=split,
        subject=str(topic["subject"]),
        position=str(topic[f"position_{fields['stance']}"]),
        **fields,
    )


def tasks_of(brief: Brief, rng: random.Random) -> dict[str, dict[str, object]]:
    """Task id to task. One task is one writing context: it never sees another task."""
    prompt = operator_prompt(brief)
    if brief.set == "bench":
        return {f"bench-{brief.id}": {"n_posts": BENCH_POSTS, "instruction": prompt}}
    tasks: dict[str, dict[str, object]] = {
        f"shared-{brief.topic}": {"n_posts": ACTORS * POSTS_PER_ACTOR, "instruction": prompt}
    }
    sketches = zip(
        rng.sample(AGES, ACTORS),
        rng.sample(PLACES, ACTORS),
        rng.sample(HABITS, ACTORS),
        strict=True,
    )
    for actor, (age, place, habit) in enumerate(sketches):
        tasks[f"solo-{brief.topic}-a{actor}"] = {"n_posts": POSTS_PER_ACTOR, "instruction": prompt}
        tasks[f"persona-{brief.topic}-a{actor}"] = {
            "n_posts": POSTS_PER_ACTOR,
            "instruction": f"{prompt}\n{account_sketch(age, place, habit)}",
        }
    return tasks


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    rng = random.Random(SEED)
    topics = json.loads(TOPICS_FILE.read_text(encoding="utf-8"))["kept"]
    rng.shuffle(topics)
    for index, topic in enumerate(topics):
        topic["code"] = f"t{index:02d}"

    briefs = bench_briefs(topics, rng)
    for index, topic in enumerate(topics):
        fields = {name: rng.choice(levels) for name, levels in LEVELS.items()}
        briefs.append(make_brief(f"{topic['code']}-twin", "twin", index, topic, fields))

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    tasks: dict[str, dict[str, object]] = {}
    for brief in briefs:
        for task_id, task in tasks_of(brief, rng).items():
            tasks[task_id] = {"task": task_id, "brief": brief.id, **task}
            path = TASKS_DIR / f"{task_id}.json"
            path.write_text(json.dumps(tasks[task_id], indent=1), encoding="utf-8")
    payload = {
        "seed": SEED,
        "topics": [{k: t[k] for k in ("code", "id", "pool_subject", "subject")} for t in topics],
        "briefs": [dataclasses.asdict(brief) for brief in briefs],
        "tasks": {task_id: str(task["brief"]) for task_id, task in tasks.items()},
    }
    BRIEFS_FILE.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    log.info("%d briefs, %d writing tasks", len(briefs), len(tasks))


if __name__ == "__main__":
    main()

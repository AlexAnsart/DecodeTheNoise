"""Test 3: does a propose-run-compare-correct loop recover a brief better than one reading?

Each held-out brief gives 32 posts: 16 are seen by the loop, 16 are hidden and only measured.
Two anchors frame every distance to the hidden half: the subject alone (floor) and the true
instruction run by the same model (ceiling).

Run: uv run --group pipelines python -m pipelines.briefs.loop_run
"""

import json
import logging
import random
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

from pipelines.briefs.bench import (
    BENCH,
    BRIEFS_FILE,
    LOOP_POSTS_FILE,
    POSTS_FILE,
    SEED,
    read_jsonl,
    write_jsonl,
)
from pipelines.briefs.fields import LEVELS, Brief, operator_prompt, topic_only_prompt
from pipelines.briefs.llm import CachedChat
from pipelines.briefs.loop import Round, chosen, recover, run_guess
from pipelines.briefs.loop_prompts import Guess
from pipelines.briefs.vectors import embed

log = logging.getLogger("briefs.loop")

MODEL = "gemini-3.8-flash"
BRIEFS_PER_TOPIC = 8
MIN_POSTS = 24
WORKERS = 6
LOOP_FILE = BENCH / "loop.json"
_embedding = threading.Lock()


@dataclass(frozen=True)
class Target:
    brief: Brief
    seen_texts: list[str]
    seen: np.ndarray
    hidden: np.ndarray


def embed_one_at_a_time(texts: list[str]) -> np.ndarray:
    """The vector cache is one append-only file: threads take turns."""
    with _embedding:
        return embed(texts)[0]


def targets() -> list[Target]:
    """Held-out briefs with their posts split in two halves by a fixed shuffle."""
    briefs = {b["id"]: Brief(**b) for b in json.loads(BRIEFS_FILE.read_text("utf-8"))["briefs"]}
    texts: dict[str, list[str]] = defaultdict(list)
    for row in read_jsonl(POSTS_FILE):
        if row["set"] == "bench" and row["split"] == "test":
            texts[str(row["brief"])].append(str(row["text"]))
    rng = random.Random(SEED)
    found = []
    for brief_id in sorted(texts):
        posts = texts[brief_id]
        if len(posts) < MIN_POSTS:
            continue
        rng.shuffle(posts)
        vectors = embed_one_at_a_time(posts)
        half = len(posts) // 2
        found.append(Target(briefs[brief_id], posts[:half], vectors[:half], vectors[half:]))
    return found


def run_one(chat: CachedChat, target: Target) -> dict[str, object]:
    args = (target.seen, target.hidden, embed_one_at_a_time)
    rounds = recover(chat, target.seen_texts, *args)
    brief = target.brief
    floor = run_guess(chat, Guess({}, brief.subject, topic_only_prompt(brief.subject)), 100, *args)
    truth = {name: getattr(brief, name) for name in LEVELS}
    ceiling = run_guess(chat, Guess(truth, brief.subject, operator_prompt(brief)), 101, *args)
    # The chosen round was picked on the very posts it is measured with: write new ones.
    fresh = run_guess(chat, rounds[chosen(rounds)].guess, 200, *args) if rounds else None
    log.info("%s: %d rounds", brief.id, len(rounds))
    return {
        "brief": brief.id,
        "topic": brief.topic,
        "truth": truth,
        "true_prompt": operator_prompt(brief),
        "rounds": [as_dict(r) for r in rounds],
        "chosen": chosen(rounds) if rounds else None,
        "fresh": as_dict(fresh) if fresh else None,
        "floor": as_dict(floor),
        "ceiling": as_dict(ceiling),
    }


def as_dict(round_: Round) -> dict[str, object]:
    return {
        "fields": round_.guess.fields,
        "prompt": round_.guess.prompt,
        "differences": list(round_.guess.differences),
        "posts": list(round_.posts),
        "seen_distance": round_.seen_distance,
        "hidden_distance": round_.hidden_distance,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    by_topic: dict[str, list[Target]] = defaultdict(list)
    for target in targets():
        by_topic[target.brief.topic].append(target)
    rng = random.Random(SEED)
    picked = [
        t
        for topic in sorted(by_topic)
        for t in rng.sample(by_topic[topic], min(BRIEFS_PER_TOPIC, len(by_topic[topic])))
    ]
    log.info("%d briefs of %d topics", len(picked), len(by_topic))
    chat = CachedChat(MODEL)
    with ThreadPoolExecutor(WORKERS) as pool:
        runs = list(pool.map(lambda target: run_one(chat, target), picked))
    chat.close()
    LOOP_FILE.write_text(
        json.dumps({"model": MODEL, "runs": runs}, ensure_ascii=False), encoding="utf-8"
    )
    # Posts another model wrote from the true briefs: a second writer for the probes of test 1.
    written = write_jsonl(
        LOOP_POSTS_FILE,
        (
            {
                "brief": run["brief"],
                "topic": run["topic"],
                "text": post,
                "writer": MODEL,
                **run["truth"],
            }
            for run in runs
            for post in run["ceiling"]["posts"]
        ),
    )
    log.info("%d runs written to %s; %d posts from the true briefs", len(runs), LOOP_FILE, written)


if __name__ == "__main__":
    main()

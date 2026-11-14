"""Baseline of test 1: an LLM reads N posts of a brief and fills the same closed fields.

It answers the question a probe has to beat: what does one LLM call read from the same posts?
The model is pinned, the temperature is 0 and every answer is cached.

Run: uv run --group pipelines python -m pipelines.briefs.field_reader
"""

import logging
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from pipelines.briefs.bench import POSTS_FILE, SEED, read_jsonl, write_result
from pipelines.briefs.fields import FIELD_GUIDE, LEVELS
from pipelines.briefs.llm import CachedChat
from pipelines.briefs.ncurve import interval, rounded

log = logging.getLogger("briefs.field_reader")

MODEL = "gemini-3.8-flash"
PROMPT_VERSION = "brief-reader-v1"
SIZES = (1, 4, 16)
SYSTEM = (
    "You read social-media posts that were all written from one hidden brief, and you recover "
    "the brief. Answer with one JSON object and nothing else."
)

USER = f"""These posts were written from the same brief.

{{posts}}

Fill the brief. Choose exactly one value per key:
{FIELD_GUIDE}
Return a JSON object with these four keys."""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    posts: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in read_jsonl(POSTS_FILE):
        if row["set"] == "bench" and row["split"] == "test":
            posts[str(row["brief"])].append(row)

    rng = random.Random(SEED)
    asks = []
    for brief in sorted(posts):
        for size in SIZES:
            sample = rng.sample(posts[brief], min(size, len(posts[brief])))
            listed = "\n".join(f"- {row['text']}" for row in sample)
            asks.append((brief, size, USER.format(posts=listed)))

    chat = CachedChat(MODEL)
    with ThreadPoolExecutor(8) as pool:
        replies = list(pool.map(lambda ask: chat.ask(SYSTEM, ask[2], max_tokens=800), asks))
    chat.close()

    hits: dict[tuple[str, int], list[float]] = defaultdict(list)
    unusable = 0
    for (brief, size, _), reply in zip(asks, replies, strict=True):
        unusable += not reply.data
        for field in LEVELS:
            hits[(field, size)].append(float(reply.data.get(field) == posts[brief][0][field]))
    generator = np.random.default_rng(SEED)
    payload = {
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "temperature": 0,
        "briefs": len(posts),
        "calls": len(asks),
        "unusable_answers": unusable,
        "interval": "95%, bootstrap over test briefs",
        "fields": {
            field: {
                size: rounded(interval(np.array(hits[(field, size)]), generator)) for size in SIZES
            }
            for field in LEVELS
        },
    }
    log.info("written: %s", write_result("field-reader", payload))


if __name__ == "__main__":
    main()

"""Turns each organic pool into a subject with two opposed positions, then makes it fictional.

Two LLM calls per kept pool. The first reads what the real posts talk about. The second
(`fiction.py`) replaces every real name with an invented one. Pools that are incoherent or
sensitive are left out.

Run: uv run --group pipelines python -m pipelines.briefs.topics
"""

import json
import logging
import random
from collections import defaultdict

from pydantic import BaseModel, ValidationError

from pipelines.briefs.bench import POOLS_FILE, SEED, TOPICS_FILE, read_jsonl
from pipelines.briefs.fiction import PLACES, Topic, fictional
from pipelines.briefs.fiction import PROMPT_VERSION as FICTION_VERSION
from pipelines.briefs.llm import CachedChat

log = logging.getLogger("briefs.topics")

MODEL = "gemini-3.8-flash"
PROMPT_VERSION = f"brief-topic-v1+{FICTION_VERSION}"
SAMPLES = 20
N_TOPICS = 24
# Read by hand after the model's own screen: no synthetic post is written on these subjects.
SCREENED_OUT = {
    "a real party, leader or creed": (
        "alp",
        "dementia",
        "atonement",
        "macarthur",
        "sacrament",
        "satanism",
        "varna",
        "moroccan",
    ),
    "health": ("metastatic", "sobriety"),
    "a named financial product or trading advice": ("kairos", "levels", "resistance"),
    "same subject as a kept topic, or no real debate": (
        "assistants",
        "innovation",
        "fremont",
        "marist",
        "shropshire",
        "spokane",
    ),
}
SYSTEM = (
    "You describe what a set of social-media posts is about, for a research benchmark on "
    "coordinated campaigns. Answer with one JSON object and nothing else."
)
USER = """These posts all contain the word "{term}" and were posted in the same month.

{posts}

Return a JSON object with these keys:
- "subject": what most of these posts talk about, as a neutral phrase of at most 12 words.
- "position_for": an opinion that approves of or defends the main thing the subject names, as
  an ordinary person could hold it, one sentence.
- "position_against": the opposite opinion, critical of that same thing, one sentence.
- "coherent": true if at least half of the posts are about that subject, else false.
- "sensitive": true if the subject is medical advice, the integrity of an election, a named
  private person, a violent conflict, or hostility toward a group of people; else false."""


class Reading(BaseModel):
    """What a pool of real posts talks about, as the model read it."""

    id: str
    subject: str
    position_for: str
    position_against: str
    coherent: bool
    sensitive: bool
    actors: int


def rewritten(chat: CachedChat, reading: Reading, place: str) -> Topic | None:
    return fictional(
        chat, reading.id, reading.subject, reading.position_for, reading.position_against, place
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    texts: dict[str, list[str]] = defaultdict(list)
    actors: dict[str, set[str]] = defaultdict(set)
    for row in read_jsonl(POOLS_FILE):
        texts[str(row["pool"])].append(str(row["text"]))
        actors[str(row["pool"])].add(str(row["actor"]))

    chat = CachedChat(MODEL)
    rng = random.Random(SEED)
    topics: list[Reading] = []
    for pool in sorted(texts):
        sample = rng.sample(texts[pool], min(SAMPLES, len(texts[pool])))
        posts = "\n".join(f"- {text[:280]}" for text in sample)
        term = pool.rsplit("-", 2)[0]
        reply = chat.ask(SYSTEM, USER.format(term=term, posts=posts), max_tokens=1200)
        try:
            topics.append(Reading(id=pool, actors=len(actors[pool]), **reply.data))
        except (ValidationError, TypeError):
            log.warning("pool %s: unusable answer %s", pool, reply.data)

    screened = {term for terms in SCREENED_OUT.values() for term in terms}
    usable = [
        t
        for t in topics
        if t.coherent and not t.sensitive and t.id.rsplit("-", 2)[0] not in screened
    ]
    chosen = sorted(usable, key=lambda t: (-t.actors, t.id))[:N_TOPICS]
    kept = [
        topic
        for reading, place in zip(chosen, PLACES, strict=True)
        if (topic := rewritten(chat, reading, place)) is not None
    ]
    chat.close()
    payload = {
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "temperature": 0,
        "kept": [t.model_dump() for t in kept],
        "left_out": [t.model_dump() for t in topics if t not in chosen],
    }
    TOPICS_FILE.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    log.info("%d topics kept of %d pools read", len(kept), len(topics))


if __name__ == "__main__":
    main()

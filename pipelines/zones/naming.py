"""Names a zone from its distinctive words and a few of its texts, with an LLM.

The model reads what the clustering already found; it does not judge the posts. An answer
that is missing or malformed leaves the zone under its words.
"""

import hashlib
import json
from typing import Protocol

import numpy as np
from pydantic import BaseModel, ValidationError, field_validator

PROMPT_VERSION = "zone-name-v1"
SAMPLES_PER_ZONE = 12
SAMPLE_CHARS = 280
MIN_WORDS = 2
MAX_WORDS = 5
MAX_NAME_CHARS = 48

SYSTEM = (
    "You name groups of social media posts for the legend of a map. "
    'Answer with a JSON object {"name": string} and nothing else. '
    f"The name has {MIN_WORDS} to {MAX_WORDS} plain English words and says what the posts are "
    "about, whatever language they are written in. It makes no claim about truth, intent or "
    "who wrote the posts."
)


class Completer(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class ZoneName(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _short_and_plain(cls, value: str) -> str:
        name = " ".join(value.split()).strip(" .\"'")
        if not MIN_WORDS <= len(name.split()) <= MAX_WORDS or len(name) > MAX_NAME_CHARS:
            raise ValueError(f"a zone name has {MIN_WORDS} to {MAX_WORDS} words")
        return name


class CachedName(BaseModel):
    """What one call returned, kept with what produced it."""

    model: str
    prompt_version: str
    raw: str
    name: str | None


def build_prompt(words: list[str], samples: list[str]) -> str:
    shown = "\n".join(f"- {' '.join(text.split())[:SAMPLE_CHARS]}" for text in samples)
    return f"Distinctive words: {', '.join(words)}\n\nPosts from the group:\n{shown}"


def parse_name(raw: str) -> str | None:
    """The name in the model's answer, or None when the answer is not the JSON asked for."""
    try:
        return ZoneName.model_validate(json.loads(raw)).name
    except (json.JSONDecodeError, ValidationError, TypeError):
        return None


def representative(vectors: np.ndarray, members: np.ndarray, count: int) -> list[int]:
    """The members nearest to the mean direction of their zone: the texts that say it best."""
    mean = vectors[members].mean(axis=0)
    scores = vectors[members] @ (mean / max(float(np.linalg.norm(mean)), 1e-12))
    return members[np.argsort(-scores, kind="stable")[:count]].tolist()


def cache_key(model: str, user: str) -> str:
    text = "\n".join((model, PROMPT_VERSION, SYSTEM, user))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def name_zone(
    client: Completer,
    model: str,
    cache: dict[str, CachedName],
    words: list[str],
    samples: list[str],
) -> str | None:
    """One call per zone, answered from the cache when the same question was asked before."""
    user = build_prompt(words, samples)
    key = cache_key(model, user)
    if key not in cache:
        raw = client.complete(SYSTEM, user)
        cache[key] = CachedName(
            model=model, prompt_version=PROMPT_VERSION, raw=raw, name=parse_name(raw)
        )
    return cache[key].name


def tell_apart(names: list[str], words: list[list[str]]) -> list[str]:
    """Two zones can receive the same name. The first keeps it; each later one adds its first
    distinctive word that neither the name nor an earlier twin already holds."""
    out: list[str] = []
    taken: dict[str, set[str]] = {}
    for name, own in zip(names, words, strict=True):
        lowered = [word.lower() for word in own]
        if name not in taken:
            taken[name] = set(name.lower().split()) | set(lowered)
            out.append(name)
            continue
        extra = next((word for word in own if word.lower() not in taken[name]), None)
        taken[name] |= set(lowered)
        out.append(f"{name} ({extra})" if extra else name)
    return out

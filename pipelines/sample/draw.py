"""Draws whole actors until a number of items is reached. Pure and seeded."""

import hashlib
from collections.abc import Mapping


def _rank(seed: str, actor_id: str) -> str:
    return hashlib.sha256(f"{seed}|{actor_id}".encode()).hexdigest()


def draw_actors(counts: Mapping[str, int], wanted: int, seed: str) -> list[str]:
    """The actors of a sample of exactly `wanted` items, when the corpus can give them.

    Actors come in the order of a hash of their id, which is arbitrary and fixed by `seed`.
    Each one is taken with all its items while it fits; an actor with more items than the room
    left is passed over. An actor is therefore never cut: what it says elsewhere in the corpus
    is in the sample too.
    """
    chosen: list[str] = []
    room = wanted
    for actor_id in sorted(counts, key=lambda actor: _rank(seed, actor)):
        if room == 0:
            break
        if counts[actor_id] <= room:
            chosen.append(actor_id)
            room -= counts[actor_id]
    return chosen

"""Draws whole actors until a number of items is reached. Pure and seeded."""

import hashlib
from collections.abc import Mapping, Sequence


def _rank(seed: str, actor_id: str) -> str:
    return hashlib.sha256(f"{seed}|{actor_id}".encode()).hexdigest()


def draw_actors(
    counts: Mapping[str, int], wanted: int, seed: str, first: Sequence[str] = ()
) -> list[str]:
    """The actors of a sample of exactly `wanted` items, when the corpus can give them.

    Actors come in the order of a hash of their id, which is arbitrary and fixed by `seed`.
    Each one is taken with all its items while it fits; an actor with more items than the room
    left is passed over. An actor is therefore never cut: what it says elsewhere in the corpus
    is in the sample too.

    `first` names actors taken before the draw, whole, when the corpus has them: a smaller
    sample can keep the accounts an example rests on. The draw fills the room they leave.
    """
    chosen = [actor_id for actor_id in dict.fromkeys(first) if actor_id in counts]
    taken = set(chosen)
    room = wanted - sum(counts[actor_id] for actor_id in chosen)
    for actor_id in sorted(counts, key=lambda actor: _rank(seed, actor)):
        if room <= 0:
            break
        if actor_id not in taken and counts[actor_id] <= room:
            chosen.append(actor_id)
            room -= counts[actor_id]
    return chosen

"""Draws posts for a stage of the evaluation. Pure.

The order depends on the seed and on the set of posts, never on how they were listed, so a
shorter run reads the first posts of a longer one and their answers are paid for once.
"""

import random
from collections.abc import Iterable


def seeded_order(keys: Iterable[str], seed: int) -> list[str]:
    ordered = sorted(keys)
    random.Random(seed).shuffle(ordered)
    return ordered


def draw(keys: Iterable[str], n: int, seed: int) -> list[str]:
    """`n` of the posts, uniformly at random; all of them when there are fewer."""
    return seeded_order(keys, seed)[:n]

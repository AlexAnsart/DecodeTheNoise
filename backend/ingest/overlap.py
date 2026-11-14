"""How much two texts share of their wording, whatever they mean. Pure.

Two texts close in meaning that share most of their character 5-grams are copies of one
another; close in meaning with few in common, the same statement was written twice.
"""

import re

GRAM = 5
# Links, mentions and hashtags vary between copies of one template: they are left out.
_NOISE = re.compile(r"https?://\S+|[@#]\w+")


def _grams(text: str) -> set[str]:
    clean = " ".join(_NOISE.sub(" ", text.lower()).split())
    if len(clean) <= GRAM:
        return {clean} if clean else set()
    return {clean[i : i + GRAM] for i in range(len(clean) - GRAM + 1)}


def word_overlap(first: str, second: str) -> float:
    """Jaccard of the character 5-grams of the two texts, between 0 and 1."""
    a, b = _grams(first), _grams(second)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

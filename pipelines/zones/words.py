"""Distinctive words of each zone by class-based TF-IDF. Pure."""

import math
import re
from collections import Counter

from pipelines.zones.stopwords import STOP_WORDS

TOP_WORDS = 8
NOISE = re.compile(r"https?://\S+|@\w+")
# Letters only, three or more: drops numbers, punctuation and the shortest function words.
WORD = re.compile(r"[^\W\d_]{3,}")


def tokens(text: str) -> list[str]:
    """Lowercase words of a text, without links, mentions and stop words."""
    return [w for w in WORD.findall(NOISE.sub(" ", text).lower()) if w not in STOP_WORDS]


def distinctive_words(texts_by_zone: list[list[str]], top: int = TOP_WORDS) -> list[list[str]]:
    """For each zone, the words frequent in it and rare elsewhere, best first.

    Score of word t in zone c: tf(t, c) * log(1 + A / f(t)), where tf is the share of the zone's
    words that are t, f(t) the count of t over all zones and A the mean word count per zone.
    """
    counts = [Counter(w for text in texts for w in tokens(text)) for texts in texts_by_zone]
    overall: Counter[str] = Counter()
    for zone_counts in counts:
        overall.update(zone_counts)
    mean_size = sum(overall.values()) / max(len(counts), 1)
    out: list[list[str]] = []
    for zone_counts in counts:
        size = sum(zone_counts.values())
        scored = {
            word: (n / size) * math.log(1.0 + mean_size / overall[word])
            for word, n in zone_counts.items()
        }
        # Ties broken by the word itself, so the result does not depend on dictionary order.
        ranked = sorted(scored, key=lambda word: (-scored[word], word))
        out.append(ranked[:top])
    return out

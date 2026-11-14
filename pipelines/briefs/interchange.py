"""Surface habits of a post: the style reading of the interchangeable-actors test.

The score itself (the gap between posts of one actor and posts of different actors, against a
shuffle of who wrote what) is `backend/voices/score.py`: the server runs the same code.
"""

import re

import numpy as np

_EMOJI = re.compile("[🌀-🫿☀-➿]")


def style_features(text: str) -> list[float]:
    """Surface habits of a post that do not depend on what it talks about."""
    words = text.split()
    letters = [c for c in text if c.isalpha()]
    return [
        float(np.log1p(len(text))),
        float(np.log1p(len(words))),
        float(np.mean([len(w) for w in words])) if words else 0.0,
        sum(c.isupper() for c in letters) / max(len(letters), 1),
        float(text[:1].islower()),
        text.count("!") / max(len(words), 1),
        text.count("?") / max(len(words), 1),
        text.count(",") / max(len(words), 1),
        text.count(".") / max(len(words), 1),
        float("..." in text or "…" in text),
        text.count("#") / max(len(words), 1),
        text.count("@") / max(len(words), 1),
        len(_EMOJI.findall(text)) / max(len(words), 1),
        sum(c.isdigit() for c in text) / max(len(text), 1),
        float(text.rstrip()[-1:] in ".!?"),
        sum(w.isupper() and len(w) > 1 for w in words) / max(len(words), 1),
    ]


def style_similarity(features: np.ndarray) -> np.ndarray:
    """Negative distance between posts; `features` are already standardised over the corpus."""
    diff = features[:, None, :] - features[None, :, :]
    return -np.sqrt((diff**2).sum(axis=2))

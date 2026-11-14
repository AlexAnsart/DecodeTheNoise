"""Do the actors of a group speak with one voice? The score. Pure numpy.

Inside a group, two posts by one actor are compared with two posts by different actors. When
actors have a voice of their own, the first pair is closer. Shuffling who wrote what gives the
gap chance alone produces: the score is the observed gap in standard deviations of the shuffled
ones. Near 0, the actors are interchangeable.

The evaluation (`pipelines/briefs/voices_report.py`) and the server call the same functions, so
what is served is what was measured.
"""

from dataclasses import dataclass

import numpy as np

# (actors, posts of each): the group sizes the check was measured on, the largest first.
SIZES = ((6, 6), (4, 4))
DRAWS = 20
PERMUTATIONS = 999
ALPHA = 0.05


@dataclass(frozen=True)
class Interchange:
    gap: float  # within-actor similarity minus between-actor similarity
    z: float  # the gap in standard deviations of its shuffled values
    p: float  # share of shuffles with a gap at least as large
    attribution: float  # share of posts given back to their actor, each post left out in turn
    chance: float  # what attribution scores when actors are interchangeable


@dataclass(frozen=True)
class Voices:
    """The reading of one group at one measured size, averaged over the draws."""

    score: float
    attribution: float
    actors: int
    posts_each: int
    eligible_actors: int  # actors of the group with enough posts to be drawn


def cosine(vectors: np.ndarray) -> np.ndarray:
    unit = vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
    return unit @ unit.T


def gap(similarity: np.ndarray, actors: np.ndarray) -> float:
    same = actors[:, None] == actors[None, :]
    apart = ~np.eye(len(actors), dtype=bool)
    return float(similarity[same & apart].mean() - similarity[~same].mean())


def attribution(similarity: np.ndarray, actors: np.ndarray) -> float:
    """Each post goes to the actor whose other posts are closest on average."""
    labels = np.unique(actors)
    apart = ~np.eye(len(actors), dtype=bool)
    scores = np.stack(
        [
            (similarity * (apart & (actors == label)[None, :])).sum(axis=1)
            / np.maximum((apart & (actors == label)[None, :]).sum(axis=1), 1)
            for label in labels
        ],
        axis=1,
    )
    return float((labels[scores.argmax(axis=1)] == actors).mean())


def interchange_test(
    similarity: np.ndarray, actors: np.ndarray, rng: np.random.Generator
) -> Interchange:
    """`similarity` is any symmetric post-to-post score; `actors` names the author of each row."""
    observed = gap(similarity, actors)
    # Shuffling who wrote what is the same as shuffling the rows and columns of the scores.
    same = actors[:, None] == actors[None, :]
    within = same & ~np.eye(len(actors), dtype=bool)
    order = np.argsort(rng.random((PERMUTATIONS, len(actors))), axis=1)
    mixed = similarity[order[:, :, None], order[:, None, :]]
    shuffled = (mixed * within).sum(axis=(1, 2)) / within.sum() - (mixed * ~same).sum(
        axis=(1, 2)
    ) / (~same).sum()
    spread = float(shuffled.std())
    return Interchange(
        gap=observed,
        z=(observed - float(shuffled.mean())) / spread if spread else 0.0,
        p=float((1 + (shuffled >= observed).sum()) / (1 + PERMUTATIONS)),
        attribution=attribution(similarity, actors),
        chance=1.0 / len(np.unique(actors)),
    )


def eligible(actors: np.ndarray, posts: int) -> np.ndarray:
    """The actors with at least `posts` posts in the group."""
    names, counts = np.unique(actors, return_counts=True)
    return names[counts >= posts]


def draw(actors: np.ndarray, size: tuple[int, int], rng: np.random.Generator) -> np.ndarray | None:
    """Rows of `size[0]` actors with `size[1]` posts each, or None when the group is too small."""
    able = eligible(actors, size[1])
    if len(able) < size[0]:
        return None
    chosen = rng.choice(able, size=size[0], replace=False)
    picks = [rng.choice(np.flatnonzero(actors == a), size[1], replace=False) for a in chosen]
    return np.concatenate(picks)


def measured_size(actors: np.ndarray) -> tuple[int, int] | None:
    """The largest measured size this group can be read at."""
    for size in SIZES:
        if len(eligible(actors, size[1])) >= size[0]:
            return size
    return None


def read_voices(
    vectors: np.ndarray, actors: np.ndarray, size: tuple[int, int], rng: np.random.Generator
) -> Voices | None:
    """The score of a group at one size: the mean over `DRAWS` draws. None when too small."""
    tests = []
    for _ in range(DRAWS):
        rows = draw(actors, size, rng)
        if rows is None:
            return None
        tests.append(interchange_test(cosine(vectors[rows]), actors[rows], rng))
    return Voices(
        score=float(np.mean([test.z for test in tests])),
        attribution=float(np.mean([test.attribution for test in tests])),
        actors=size[0],
        posts_each=size[1],
        eligible_actors=len(eligible(actors, size[1])),
    )

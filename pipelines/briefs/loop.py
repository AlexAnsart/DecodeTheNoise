"""Test 3, one brief: recover an instruction by proposing, running, comparing and correcting.

Round 0 is one reading of the seen posts. Each later round runs the best guess so far, shows
the editor what came out next to the real posts, and takes its rewrite. The search only ever
looks at the seen half; the hidden half is measured for the report and never steers anything.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from pipelines.briefs.llm import CachedChat
from pipelines.briefs.loop_prompts import Guess, edit, read, write

ROUNDS = 3
Embed = Callable[[list[str]], np.ndarray]


def energy_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Zero when two sets of vectors come from one distribution; grows as they move apart."""

    def mean_gap(x: np.ndarray, y: np.ndarray, same: bool) -> float:
        gaps = np.linalg.norm(x[:, None, :] - y[None, :, :], axis=2)
        if same:  # leave out each vector's distance to itself
            return float(gaps.sum() / (len(x) * (len(x) - 1)))
        return float(gaps.mean())

    return 2 * mean_gap(a, b, False) - mean_gap(a, a, True) - mean_gap(b, b, True)


@dataclass(frozen=True)
class Round:
    guess: Guess
    posts: tuple[str, ...]
    seen_distance: float  # steers the search
    hidden_distance: float  # reported, never used to choose


def run_guess(
    chat: CachedChat, guess: Guess, sample: int, seen: np.ndarray, hidden: np.ndarray, embed: Embed
) -> Round:
    """Writes posts from a guess and measures how far they land from each half."""
    posts = write(chat, guess.prompt, sample)
    if len(posts) < 2:  # a refusal or an unreadable answer: the guess cannot be scored
        return Round(guess, tuple(posts), float("inf"), float("inf"))
    vectors = embed(posts)
    return Round(
        guess, tuple(posts), energy_distance(vectors, seen), energy_distance(vectors, hidden)
    )


def recover(
    chat: CachedChat, seen_texts: list[str], seen: np.ndarray, hidden: np.ndarray, embed: Embed
) -> list[Round]:
    """Rounds 0 to `ROUNDS`, in order. Empty when the first reading gave no instruction."""
    guess = read(chat, seen_texts)
    if guess is None:
        return []
    rounds: list[Round] = []
    for number in range(ROUNDS + 1):
        rounds.append(run_guess(chat, guess, number, seen, hidden, embed))
        if number == ROUNDS:
            break
        best = min(rounds, key=lambda r: r.seen_distance)
        # An unusable rewrite keeps the best guess: it is run again with a new sample.
        guess = edit(chat, seen_texts, best.guess, list(best.posts)) or best.guess
    return rounds


def chosen(rounds: list[Round]) -> int:
    """The round a user would be shown: the closest to the seen half."""
    return int(np.argmin([r.seen_distance for r in rounds]))

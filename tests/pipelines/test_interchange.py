import numpy as np
import pytest

from backend.voices.score import ALPHA, cosine, interchange_test
from pipelines.briefs.fields import LEVELS, Brief, operator_prompt
from pipelines.briefs.interchange import style_features, style_similarity


def group(rng: np.random.Generator, own_voice: float) -> tuple[np.ndarray, np.ndarray]:
    """Four actors of six posts; `own_voice` is how far each actor sits from the others."""
    actors = np.repeat(np.arange(4), 6)
    centres = rng.normal(size=(4, 16)) * own_voice
    return centres[actors] + rng.normal(size=(24, 16)), actors


def test_actors_with_a_voice_are_told_apart() -> None:
    rng = np.random.default_rng(0)
    vectors, actors = group(rng, own_voice=3.0)
    result = interchange_test(cosine(vectors), actors, rng)
    assert result.p < ALPHA
    assert result.attribution > 0.9
    assert result.chance == 0.25


def test_actors_without_a_voice_are_interchangeable() -> None:
    rng = np.random.default_rng(1)
    rejected = 0
    for _ in range(40):
        vectors, actors = group(rng, own_voice=0.0)
        rejected += interchange_test(cosine(vectors), actors, rng).p < ALPHA
    # The test keeps its level: about one group in twenty is told apart by chance.
    assert rejected <= 6


def test_style_similarity_is_highest_for_the_same_habits() -> None:
    posts = [
        "this is all lowercase no punctuation",
        "another lowercase one here",
        "LOUD! VERY LOUD!",
    ]
    features = np.array([style_features(p) for p in posts])
    features = (features - features.mean(axis=0)) / (features.std(axis=0) + 1e-9)
    similarity = style_similarity(features)
    assert similarity[0, 1] > similarity[0, 2]


def test_clean_drops_repeats_and_empty_posts() -> None:
    # The collector records a manifest line through the dataset tooling: skipped without it.
    pytest.importorskip("pipelines.datasets.manifest")
    from pipelines.briefs.collect import clean

    assert clean([" a  b ", "a b", "", "c"]) == ["a b", "c"]


def test_operator_prompt_carries_every_field() -> None:
    brief = Brief(
        "t00-b00",
        "bench",
        "t00",
        "dev",
        "bus fares",
        "Fares should be free.",
        "for",
        "parent",
        "angry",
        "short",
    )
    prompt = operator_prompt(brief)
    assert "bus fares" in prompt and "Fares should be free." in prompt
    assert "parent" in prompt and "angry" in prompt and "under 100 characters" in prompt
    assert set(LEVELS) == {"stance", "persona", "tone", "format"}

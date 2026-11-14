import numpy as np

from pipelines.zones.__main__ import by_size, describe
from pipelines.zones.kmeans import MAX_ZONES, MIN_ZONES, spherical_kmeans, zone_count
from pipelines.zones.words import distinctive_words, tokens

CATS = ["The cat sat on the mat", "My cat chases every mouse", "cat videos all day"]
DOGS = ["The dog barks at the mailman", "My dog fetches every ball", "dog walks all day"]


def test_tokens_drop_links_mentions_stop_words_and_short_words() -> None:
    assert tokens("RT @someone: The CAT is on https://t.co/xyz at 10 am") == ["cat"]


def test_tokens_keep_other_alphabets() -> None:
    assert tokens("Новости России и мира") == ["новости", "россии", "мира"]


def test_word_shared_by_every_zone_ranks_under_the_word_of_one_zone() -> None:
    words = distinctive_words([CATS, DOGS])
    assert words[0][0] == "cat"
    assert words[1][0] == "dog"
    assert words[0].index("cat") < words[0].index("day")


def test_top_limits_the_words() -> None:
    assert all(len(w) <= 2 for w in distinctive_words([CATS, DOGS], top=2))


def test_zone_count_is_clamped() -> None:
    assert zone_count(100) == MIN_ZONES
    assert zone_count(10_000) == 25
    assert zone_count(10_000_000) == MAX_ZONES


def _two_blobs() -> np.ndarray:
    rng = np.random.default_rng(0)
    a = np.array([1.0, 0.0, 0.0]) + rng.normal(0, 0.05, (30, 3))
    b = np.array([0.0, 1.0, 0.0]) + rng.normal(0, 0.05, (20, 3))
    points = np.vstack([a, b]).astype(np.float32)
    return points / np.linalg.norm(points, axis=1, keepdims=True)


def test_kmeans_separates_two_directions_and_is_seeded() -> None:
    vectors = _two_blobs()
    labels = spherical_kmeans(vectors, 2, seed=42)
    assert len(set(labels[:30].tolist())) == 1
    assert len(set(labels[30:].tolist())) == 1
    assert labels[0] != labels[-1]
    assert np.array_equal(labels, spherical_kmeans(vectors, 2, seed=42))


def test_zones_are_numbered_by_size() -> None:
    ranked = by_size(np.array([5, 5, 2, 2, 2, 9]))
    assert ranked.tolist() == [1, 1, 0, 0, 0, 2]


def test_zone_takes_its_first_words_as_a_name_until_named() -> None:
    zones = describe(np.array([0, 0, 0, 1, 1, 1]), [*CATS, *DOGS])
    assert [z.size for z in zones] == [3, 3]
    assert zones[0].name.split(" · ")[0] == "cat"
    assert zones[0].name == " · ".join(zones[0].words[:3])
    assert not zones[0].named

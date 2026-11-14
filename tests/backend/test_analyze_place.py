import numpy as np
import pytest

from backend.analyze.place import (
    beginning,
    nearest,
    neighbour_weights,
    weighted_position,
    with_title,
)


def test_nearest_returns_the_closest_first() -> None:
    vectors = np.asarray([[1, 0], [0, 1], [0.8, 0.6], [-1, 0]], dtype=np.float32)

    indices, scores = nearest(vectors, np.asarray([1, 0], dtype=np.float32), k=3)

    assert indices.tolist() == [0, 2, 1]
    assert scores.tolist() == pytest.approx([1.0, 0.8, 0.0])


def test_nearest_takes_every_point_when_the_map_is_smaller_than_k() -> None:
    vectors = np.asarray([[1, 0], [0, 1]], dtype=np.float32)

    indices, _ = nearest(vectors, np.asarray([0, 1], dtype=np.float32), k=10)

    assert indices.tolist() == [1, 0]


def test_equal_scores_weigh_the_same() -> None:
    weights = neighbour_weights(np.full(4, 0.7, dtype=np.float32))

    assert weights.tolist() == pytest.approx([0.25] * 4)


def test_a_neighbour_far_ahead_takes_most_of_the_weight() -> None:
    weights = neighbour_weights(np.asarray([0.99, 0.60, 0.59, 0.58], dtype=np.float32))

    assert weights.sum() == pytest.approx(1.0)
    assert weights[0] > 0.5
    assert weights.tolist() == sorted(weights.tolist(), reverse=True)


def test_position_is_the_weighted_mean_of_the_neighbours() -> None:
    coordinates = np.asarray([[0, 0], [10, 0], [0, 10]], dtype=np.float32)

    position = weighted_position(coordinates, np.asarray([1, 2]), np.asarray([0.75, 0.25]))

    assert position == pytest.approx([7.5, 2.5])


def test_beginning_cuts_between_words() -> None:
    assert beginning("short text", 50) == "short text"
    assert beginning("one two three four", 9) == "one two"
    # No space in the second half of the budget: cut at the budget itself.
    assert beginning("a" * 30, 10) == "a" * 10


def test_title_is_put_first_unless_the_text_opens_with_it() -> None:
    assert with_title("Title", "Body.") == "Title\nBody."
    assert with_title("Title", "Title and body.") == "Title and body."
    assert with_title(None, "Body.") == "Body."

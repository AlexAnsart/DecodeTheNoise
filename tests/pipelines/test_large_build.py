"""What a large build needs: a sample of whole actors, a layout from landmarks, neighbours
found by several workers, and columns only for attributes that tell points apart."""

import numpy as np

from backend.analyze.place import neighbour_weights
from pipelines.ingest.ira import Item
from pipelines.layout.landmarks import place_from_landmarks
from pipelines.neighbours.__main__ import MEMORY, nearest, rows_at_once
from pipelines.pack.__main__ import MAX_COLUMN_VALUES, columns_of, tells_apart
from pipelines.pack.items import display_attrs
from pipelines.sample.draw import draw_actors


def _unit_rows(n: int, dims: int, seed: int) -> np.ndarray:
    rows = np.random.default_rng(seed).normal(size=(n, dims)).astype(np.float32)
    return rows / np.linalg.norm(rows, axis=1, keepdims=True)


def _item(index: int, actor: str, category: str = "Unknown", post_type: str = "original") -> Item:
    return Item(
        f"item{index}",
        actor,
        f"post number {index}",
        None,
        None,
        None,
        (),
        category,
        post_type,
        None,
    )


def test_a_sample_takes_whole_actors_and_the_number_asked() -> None:
    counts = {f"actor{i}": 1 + i % 7 for i in range(400)} | {"prolific": 5_000}

    chosen = draw_actors(counts, 600, seed="s")
    again = draw_actors(dict(reversed(counts.items())), 600, seed="s")
    other = draw_actors(counts, 600, seed="another seed")

    assert sum(counts[actor] for actor in chosen) == 600
    # An actor with more items than the sample holds is passed over, never cut.
    assert "prolific" not in chosen and len(set(chosen)) == len(chosen)
    assert chosen == again and chosen != other


def test_a_sample_larger_than_the_corpus_takes_everything() -> None:
    counts = {"a": 3, "b": 2}

    assert sorted(draw_actors(counts, 100, seed="s")) == ["a", "b"]


def test_points_are_set_down_among_their_nearest_landmarks() -> None:
    vectors = _unit_rows(300, 8, seed=1)
    landmarks = np.arange(0, 300, 3)
    layout = np.random.default_rng(2).normal(size=(len(landmarks), 3)).astype(np.float32)

    placed = place_from_landmarks(vectors, landmarks, layout)

    assert placed.shape == (300, 3) and placed.dtype == np.float32
    assert np.array_equal(placed[landmarks], layout)
    # Point 1 by hand: its ten nearest landmarks, weighted as the paste box weights them.
    scores = vectors[landmarks] @ vectors[1]
    top = np.argsort(-scores)[:10]
    assert np.allclose(placed[1], neighbour_weights(scores[top]) @ layout[top], atol=1e-5)
    # A weighted mean of landmarks never leaves the box that holds them.
    low, high = layout.min(axis=0), layout.max(axis=0)
    assert ((placed >= low - 1e-5) & (placed <= high + 1e-5)).all()


def test_weights_of_a_block_are_the_weights_of_each_row() -> None:
    scores = np.sort(np.random.default_rng(3).uniform(0.5, 1.0, size=(6, 10)), axis=1)[:, ::-1]

    together = neighbour_weights(scores)

    for row, weights in zip(scores, together, strict=True):
        assert np.allclose(weights, neighbour_weights(row))
    assert np.allclose(together.sum(axis=1), 1.0)


def test_neighbours_are_the_same_whatever_the_blocks_and_the_workers() -> None:
    vectors = _unit_rows(120, 8, seed=4)

    alone = nearest(vectors, k=5, block=120)
    shared = nearest(vectors, k=5, block=7, workers=4)

    assert np.array_equal(alone, shared)
    assert not (alone == np.arange(120)[:, None]).any()


def test_blocks_shrink_to_fit_the_memory_set() -> None:
    assert rows_at_once(1_000) == 2_048
    assert rows_at_once(500_000, workers=6) == MEMORY // (6 * 500_000 * 16)
    assert rows_at_once(10**9) == 1


def test_only_attributes_that_tell_points_apart_get_a_column() -> None:
    assert tells_apart(["a", "b", None])
    assert not tells_apart(["a", "a", None]) and not tells_apart([None, None])
    assert tells_apart([str(i) for i in range(MAX_COLUMN_VALUES)])
    assert not tells_apart([str(i) for i in range(MAX_COLUMN_VALUES + 1)])

    items = [
        _item(i, f"actor{i % 3}", post_type="reply" if i % 2 else "original") for i in range(6)
    ]
    columns, buffers = columns_of(items, [], np.zeros(6, dtype=np.uint16))

    # One category for every item and no language: neither is a column. Three accounts are.
    assert [column.key for column in columns] == ["zone", "actor", "post_type"]
    assert set(buffers) == {"col_zone", "col_actor", "col_post_type"}


def test_an_attribute_every_item_shares_is_left_out_of_the_cards() -> None:
    item = _item(1, "actor")

    assert "category" in display_attrs(item)
    assert display_attrs(item, frozenset({"category"})) == {
        "post_type": "original",
        "followers": None,
    }


def test_actors_asked_for_come_first_and_the_draw_fills_the_rest() -> None:
    counts = {f"actor-{i}": 10 for i in range(40)}
    plain = draw_actors(counts, 100, seed="s")
    asked = [actor for actor in counts if actor not in plain][:2]

    chosen = draw_actors(counts, 100, seed="s", first=[*asked, "not in the corpus", asked[0]])

    assert chosen[:2] == asked and len(set(chosen)) == len(chosen)
    assert sum(counts[actor] for actor in chosen) == 100
    # The rest is the same seeded order: the first actors of the plain draw, as many as fit.
    assert chosen[2:] == plain[:8]

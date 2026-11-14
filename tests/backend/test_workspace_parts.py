"""The pure parts under a workspace: neighbour lists, zone names, the embedding cache, overlap."""

from pathlib import Path

import numpy as np
from workspace_fakes import FakeModel

from backend.ingest.embedder import ItemEmbedder
from backend.ingest.overlap import word_overlap
from backend.map.schema import ZoneInfo
from backend.refresh.zones import carry_names, make_zones, zone_count
from backend.workspace.actors import ActorIndex
from backend.workspace.neighbours import NeighbourLists


def _unit_rows(n: int, dims: int, seed: int) -> np.ndarray:
    rows = np.random.default_rng(seed).normal(size=(n, dims)).astype(np.float32)
    return rows / np.linalg.norm(rows, axis=1, keepdims=True)


def test_lists_kept_point_by_point_equal_lists_computed_at_once() -> None:
    vectors = _unit_rows(60, 8, seed=3)
    grown = NeighbourLists(4, k=5)
    for point in range(len(vectors)):
        if point == len(grown.index):
            grown.grow(2 * point)
        grown.add(point, vectors[:point] @ vectors[point])
    exact = NeighbourLists(len(vectors), k=5)
    exact.rebuild(vectors)

    assert np.array_equal(grown.index[:60], exact.index[:60])
    assert np.allclose(grown.score[:60], exact.score[:60], atol=1e-6)
    assert not (exact.index[:60] == np.arange(60)[:, None]).any()


def test_a_zone_that_stayed_keeps_its_name() -> None:
    centres = _unit_rows(3, 8, seed=1)
    previous = (
        ZoneInfo(id=0, name="Fuel prices", words=["fuel"], size=10, named=True),
        ZoneInfo(id=1, name="rain · wind", words=["rain"], size=5, named=False),
    )
    previous_centres = np.stack([centres[2], centres[0]])
    zones = [ZoneInfo(id=i, name=f"w{i}", words=[f"w{i}"], size=1, named=False) for i in range(3)]

    carried = carry_names(zones, centres, previous, previous_centres)

    # Zone 2 continues the named zone; zone 0 continues one that had no name to carry.
    names = [(zone.name, zone.named) for zone in carried]
    assert names == [("w0", False), ("w1", False), ("Fuel prices", True)]


def test_zones_cover_every_point_and_stay_few() -> None:
    vectors = _unit_rows(40, 8, seed=5)
    texts = [f"text about subject {i % 4} with word{i % 4} repeated" for i in range(40)]

    zoning = make_zones(vectors, texts, (), None)

    assert len(zoning.zones) == zone_count(40) == 3
    sizes = sorted(np.bincount(zoning.zone).tolist(), reverse=True)
    assert sizes == [zone.size for zone in zoning.zones]
    assert np.allclose(np.linalg.norm(zoning.centres, axis=1), 1.0, atol=1e-5)
    assert zone_count(20) == 3 and zone_count(400) == 10 and zone_count(10_000) == 24


def test_a_text_is_embedded_once_and_remembered_in_the_file(tmp_path: Path) -> None:
    model = FakeModel()
    embedder = ItemEmbedder(model, tmp_path / "cache.sqlite")

    first = embedder.embed(["one", "two", "one"])
    second = embedder.embed(["two", "three"])
    embedder.close()
    again = ItemEmbedder(FakeModel(), tmp_path / "cache.sqlite")
    third = again.embed(["three", "one"])
    again.close()

    assert model.calls == [["one", "two"], ["three"]]
    assert np.array_equal(first[0], first[2])
    assert np.allclose(second[0], first[1], atol=1e-3)
    assert np.allclose(third[1], first[0], atol=1e-3)


def test_overlap_tells_a_copy_from_a_rewording() -> None:
    template = "Tell @{} to stop the cuts today! https://example.org/{}"
    copy = word_overlap(template.format("anna", 1), template.format("bob", 2).upper())
    reworded = word_overlap("Stop the cuts today!", "Nobody should accept these reductions.")

    assert copy == 1.0
    assert reworded < 0.1
    assert word_overlap("", "anything at all") == 0.0


def test_actors_are_compared_only_above_the_minimum() -> None:
    actors = ActorIndex(dims=3)
    east, north = np.array([1, 0, 0], np.float32), np.array([0, 1, 0], np.float32)
    for _ in range(3):
        ann = actors.add("ann", east, 1000.0)
        actors.add("bob", east, 2000.0)
        actors.add("cat", north, 0.0)
    lone = actors.add("dan", east, 0.0)

    assert actors.similar(ann, top=5, minimum=3) == [("bob", 1.0, 3), ("cat", 0.0, 3)]
    assert actors.similar(lone, top=5, minimum=3) == []
    assert (actors.first[ann], actors.last[ann]) == (1000.0, 1000.0)

from pathlib import Path

import numpy as np
import pytest

from pipelines.embed.merge import merge
from pipelines.embed.store import VectorStore

KEY = "model@rev|prefix=''"


def _store(folder: Path, hashes: list[str], first_value: float, key: str = KEY) -> VectorStore:
    store = VectorStore(folder, key)
    vectors = np.arange(len(hashes) * 4, dtype=np.float32).reshape(len(hashes), 4) + first_value
    store.add(hashes, vectors)
    return store


def test_parts_are_merged_and_a_shared_vector_is_copied_once(tmp_path: Path) -> None:
    a = _store(tmp_path / "a", ["h1", "h2"], 0.0)
    _store(tmp_path / "b", ["h2", "h3"], 100.0)

    added = merge(tmp_path / "all", [tmp_path / "a", tmp_path / "b"])

    merged = VectorStore(tmp_path / "all", KEY)
    assert added == 3
    assert merged.missing(["h1", "h2", "h3", "h4"]) == ["h4"]
    assert np.array_equal(merged.rows(["h1", "h2"]), a.rows(["h1", "h2"]))
    assert merged.rows(["h3"])[0, 0] == 104.0


def test_merging_again_adds_nothing(tmp_path: Path) -> None:
    _store(tmp_path / "a", ["h1", "h2"], 0.0)
    merge(tmp_path / "all", [tmp_path / "a"])
    assert merge(tmp_path / "all", [tmp_path / "a"]) == 0


def test_a_part_of_another_model_is_refused(tmp_path: Path) -> None:
    _store(tmp_path / "a", ["h1"], 0.0)
    _store(tmp_path / "b", ["h2"], 0.0, key="other@rev|prefix=''")
    with pytest.raises(ValueError, match="holds vectors of"):
        merge(tmp_path / "all", [tmp_path / "a", tmp_path / "b"])

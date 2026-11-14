from pathlib import Path

import numpy as np
import pytest

from pipelines.embed.ollama import remember_in_env
from pipelines.embed.store import HASHES_FILE, VectorStore

KEY = "model@rev|prefix='p: '"


def _vectors(rows: int, width: int = 4) -> np.ndarray:
    return np.arange(rows * width, dtype=np.float32).reshape(rows, width) / 8


def test_store_returns_rows_in_the_asked_order(tmp_path: Path) -> None:
    store = VectorStore(tmp_path, KEY)
    store.add(["a", "b", "c"], _vectors(3))
    assert store.width == 4
    assert np.array_equal(store.rows(["c", "a"]), _vectors(3)[[2, 0]])


def test_store_only_asks_for_what_it_lacks(tmp_path: Path) -> None:
    store = VectorStore(tmp_path, KEY)
    store.add(["a", "b"], _vectors(2))
    assert store.missing(["b", "c", "a", "c"]) == ["c"]


def test_store_resumes_from_disk(tmp_path: Path) -> None:
    VectorStore(tmp_path, KEY).add(["a", "b"], _vectors(2))
    reopened = VectorStore(tmp_path, KEY)
    reopened.add(["c"], _vectors(3)[2:])
    assert reopened.missing(["a", "b", "c"]) == []
    assert np.array_equal(VectorStore(tmp_path, KEY).rows(["a", "b", "c"]), _vectors(3))


def test_hash_without_its_vector_is_embedded_again(tmp_path: Path) -> None:
    VectorStore(tmp_path, KEY).add(["a", "b"], _vectors(2))
    with (tmp_path / HASHES_FILE).open("a", encoding="ascii") as out:
        out.write("ghost\n")
    assert VectorStore(tmp_path, KEY).missing(["a", "ghost"]) == ["ghost"]


def test_store_refuses_vectors_of_another_model(tmp_path: Path) -> None:
    VectorStore(tmp_path, KEY).add(["a"], _vectors(1))
    with pytest.raises(ValueError):
        VectorStore(tmp_path, "other@rev|prefix=''")


def test_env_line_is_appended_once_and_other_lines_stay(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("SECRET=keep\n", encoding="utf-8")
    remember_in_env(env, "EMBEDDING_REVISION", "abc")
    remember_in_env(env, "EMBEDDING_REVISION", "abc")
    assert env.read_text(encoding="utf-8") == "SECRET=keep\nEMBEDDING_REVISION=abc\n"
    remember_in_env(env, "EMBEDDING_REVISION", "def")
    assert env.read_text(encoding="utf-8").splitlines()[-1] == "EMBEDDING_REVISION=def"


def test_env_line_is_not_glued_to_a_last_line_without_newline(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("SECRET=keep", encoding="utf-8")
    remember_in_env(env, "EMBEDDING_REVISION", "abc")
    assert env.read_text(encoding="utf-8") == "SECRET=keep\nEMBEDDING_REVISION=abc\n"

import numpy as np
import pytest

from backend.map.schema import NO_VALUE
from pipelines.layout.scale import EXTENT, scale_layout
from pipelines.neighbours.__main__ import nearest
from pipelines.pack.buffers import (
    ALIGNMENT,
    actor_names,
    encode_column,
    pack_buffers,
    unpack_buffer,
)


def test_buffers_round_trip_at_aligned_offsets() -> None:
    arrays = {
        "pos3": np.arange(9, dtype=np.float32),
        "codes": np.array([1, 2, 3], dtype=np.uint16),
        "ts": np.array([1.5e12, 0.0, 1.6e12], dtype=np.float64),
        "neighbours": np.array([4, 5, 6, 7], dtype=np.uint32),
    }
    blob, specs = pack_buffers(arrays)
    assert list(specs) == list(arrays)
    for name, array in arrays.items():
        assert specs[name].offset % ALIGNMENT == 0
        assert specs[name].dtype == str(array.dtype)
        assert specs[name].length == array.size
        assert np.array_equal(unpack_buffer(blob, specs[name]), array)


def test_column_codes_follow_frequency_then_name() -> None:
    codes, names = encode_column(["b", "a", "b", None, "c", "a", "b"])
    assert names == ["b", "a", "c"]
    assert codes.dtype == np.uint16
    assert codes.tolist() == [0, 1, 0, NO_VALUE, 2, 1, 0]


def test_column_with_too_many_values_is_refused() -> None:
    with pytest.raises(ValueError):
        encode_column([str(i) for i in range(NO_VALUE)])


def test_actor_names_stay_short_unless_two_ids_start_the_same() -> None:
    assert actor_names(["3fa2c1aaaaaa", "9b00d2bbbbbb"])["3fa2c1aaaaaa"] == "acct-3fa2c1"
    clash = actor_names(["3fa2c1aaaaaa", "3fa2c1bbbbbb"])
    assert clash["3fa2c1aaaaaa"] == "acct-3fa2c1a"
    assert len(set(clash.values())) == 2


def test_layout_is_centred_and_scaled_to_the_extent() -> None:
    rng = np.random.default_rng(1)
    scaled = scale_layout(rng.normal(5.0, 3.0, (2000, 3)))
    assert scaled.dtype == np.float32
    assert np.allclose(scaled.mean(axis=0), 0.0, atol=1e-3)
    assert np.percentile(np.linalg.norm(scaled, axis=1), 99) == pytest.approx(EXTENT, rel=1e-4)


def test_layout_of_identical_points_does_not_divide_by_zero() -> None:
    assert np.array_equal(scale_layout(np.ones((5, 2))), np.zeros((5, 2), dtype=np.float32))


def test_nearest_leaves_the_point_out_and_sorts_by_similarity() -> None:
    angles = np.deg2rad([0.0, 10.0, 25.0, 90.0])
    vectors = np.stack([np.cos(angles), np.sin(angles)], axis=1).astype(np.float32)
    found = nearest(vectors, k=2, block=3)
    assert found.dtype == np.uint32
    assert found.tolist() == [[1, 2], [0, 2], [1, 0], [2, 1]]

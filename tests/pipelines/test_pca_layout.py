import numpy as np

from pipelines.layout.pca import principal_axes
from pipelines.layout.scale import EXTENT, EXTENT_PERCENTILE, scale_layout

# A cloud stretched along three known directions of a 6-dimensional space, most along the
# first, then the second, then the third; the three other directions hold almost nothing.
SPREAD = np.array([9.0, 4.0, 2.0, 0.1, 0.1, 0.1])


def cloud() -> np.ndarray:
    rng = np.random.default_rng(7)
    return (rng.normal(size=(500, 6)) * SPREAD + 3.0).astype(np.float32)


def test_axes_come_in_order_of_variance_and_follow_the_stretched_directions() -> None:
    vectors = cloud()
    coordinates, kept = principal_axes(vectors, 3)
    assert coordinates.shape == (500, 3)
    assert kept[0] > kept[1] > kept[2]
    assert 0.99 < kept.sum() <= 1.0
    for axis in range(3):
        assert abs(np.corrcoef(coordinates[:, axis], vectors[:, axis])[0, 1]) > 0.99


def test_two_axes_are_the_first_two_of_three() -> None:
    vectors = cloud()
    three, kept3 = principal_axes(vectors, 3)
    two, kept2 = principal_axes(vectors, 2)
    assert np.allclose(two, three[:, :2])
    assert np.allclose(kept2, kept3[:2])


def test_same_vectors_give_the_same_coordinates() -> None:
    first, _ = principal_axes(cloud(), 3)
    second, _ = principal_axes(cloud(), 3)
    assert np.array_equal(first, second)


def test_scaled_layout_keeps_the_frame_of_the_map() -> None:
    coordinates, _ = principal_axes(cloud(), 3)
    for points in (scale_layout(coordinates), scale_layout(coordinates[:, :2])):
        assert points.dtype == np.float32
        assert np.allclose(points.mean(axis=0), 0, atol=1e-3)
        reach = np.percentile(np.linalg.norm(points, axis=1), EXTENT_PERCENTILE)
        assert abs(reach - EXTENT) < 1e-2

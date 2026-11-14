import numpy as np

from pipelines.embed.compare import cosines


def test_cosines_compare_rows_pairwise_whatever_their_length() -> None:
    a = np.array([[1.0, 0.0], [0.0, 2.0], [1.0, 1.0]], dtype=np.float32)
    b = np.array([[3.0, 0.0], [1.0, 0.0], [1.0, 1.0]], dtype=np.float32)
    assert np.allclose(cosines(a, b), [1.0, 0.0, 1.0])

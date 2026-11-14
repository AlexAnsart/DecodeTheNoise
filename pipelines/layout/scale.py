"""Puts a layout in the frame the front end expects. Pure."""

import numpy as np

EXTENT = 100.0
EXTENT_PERCENTILE = 99.0


def scale_layout(points: np.ndarray) -> np.ndarray:
    """Centres the points, then scales them so that 99% lie within 100 units of the centre.

    The percentile keeps a few far-flung points from shrinking the whole cloud.
    """
    centred = points - points.mean(axis=0, keepdims=True)
    reach = np.percentile(np.linalg.norm(centred, axis=1), EXTENT_PERCENTILE)
    if reach == 0:
        return centred.astype(np.float32)
    return (centred * (EXTENT / reach)).astype(np.float32)

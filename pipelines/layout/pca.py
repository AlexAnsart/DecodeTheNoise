"""Projects vectors on their axes of largest variance (principal component analysis). Pure."""

import numpy as np


def principal_axes(vectors: np.ndarray, components: int) -> tuple[np.ndarray, np.ndarray]:
    """Coordinates on the `components` first axes, and the share of the variance each keeps.

    Exact (eigen-decomposition of the covariance), with no random part: the same vectors
    always give the same coordinates. The axes are nested, so the first two columns of a 3D
    result are the 2D result.
    """
    centred = vectors.astype(np.float64) - vectors.mean(axis=0, dtype=np.float64)
    variances, axes = np.linalg.eigh(centred.T @ centred / (len(vectors) - 1))
    order = np.argsort(variances)[::-1][:components]
    kept = axes[:, order]
    # An axis and its opposite describe the same line: fix the sign so a rerun cannot mirror it.
    kept = kept * np.sign(kept[np.abs(kept).argmax(axis=0), np.arange(components)])
    return centred @ kept, variances[order] / variances.sum()

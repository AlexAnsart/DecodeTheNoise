"""Loads the probe pack once: `probes.json` and the weights beside it, folded for scoring.

The pack is written by `pipelines.probes.export` from an evaluated run. A pack the server
cannot trust gives no probe at all, with the reason logged: the map still works without them.
"""

import logging
import zipfile
from pathlib import Path

import numpy as np
from pydantic import ValidationError

from backend.probes.schema import PACK_FILE, WEIGHTS_FILE, PackedProbe, ProbeInfo, ProbePack
from backend.probes.scoring import EMPTY, Probes
from backend.probes.uniform import Rescale, rescale

__all__ = ["EMPTY", "Probes", "load_probes"]

logger = logging.getLogger(__name__)

_ARRAYS = ("names", "weights", "bias", "mean", "scale")


def _read_arrays(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as data:
        return {name: data[name] for name in _ARRAYS}


def _shapes_agree(arrays: dict[str, np.ndarray]) -> bool:
    weights, scale = arrays["weights"], arrays["scale"]
    if weights.ndim != 2 or not len(weights) == len(arrays["names"]) == len(arrays["bias"]):
        return False
    same_dims = arrays["mean"].shape == scale.shape == (weights.shape[1],)
    # The vectors are divided by the scale: a zero would turn every score into NaN.
    return same_dims and bool(np.all(np.isfinite(scale) & (scale > 0)))


def _in_force(probe: PackedProbe) -> tuple[ProbeInfo, Rescale] | None:
    """The probe with the levels it really has, and how its logit becomes a score.

    A level needs its cut and its measure: a cut nobody measured is not applied. None when no
    level is left.
    """
    info = probe.info
    scale = rescale(
        probe.possible_cut if info.possible is not None else None,
        probe.probable_cut if info.probable is not None else None,
    )
    if scale is None:
        return None
    levels = {
        "possible": info.possible if scale.has_possible else None,
        "probable": info.probable if scale.has_probable else None,
    }
    return info.model_copy(update=levels), scale


def _fold(pack: ProbePack, arrays: dict[str, np.ndarray]) -> Probes:
    """Standardisation, weights, bias and rescaling as one weight row and one bias per probe."""
    row_of = {str(name): row for row, name in enumerate(arrays["names"])}
    missing = [probe.info.key for probe in pack.probes if probe.info.key not in row_of]
    if missing:
        logger.warning("the probe weights lack %s: no probe is served", ", ".join(missing))
        return EMPTY
    kept = [found for probe in pack.probes if (found := _in_force(probe)) is not None]
    if not kept:
        return EMPTY
    rows = [row_of[info.key] for info, _ in kept]
    slope = np.array([scale.slope for _, scale in kept])
    shift = np.array([scale.shift for _, scale in kept])
    # Float64 here: the fold is done once, and its rounding would sit in every score.
    on_vectors = arrays["weights"][rows].astype(np.float64) / arrays["scale"].astype(np.float64)
    offset = arrays["bias"][rows].astype(np.float64) - on_vectors @ arrays["mean"].astype(
        np.float64
    )
    return Probes(
        infos=tuple(info for info, _ in kept),
        weights=(slope[:, None] * on_vectors).astype(np.float32),
        bias=(slope * offset + shift).astype(np.float32),
        caps=np.array([scale.cap for _, scale in kept], dtype=np.float32),
    )


def load_probes(folder: Path, embedding_key: str) -> Probes:
    """The probes of the pack in `folder`, or none when there is no pack the server can apply."""
    pack_path = folder / PACK_FILE
    if not pack_path.is_file():
        logger.info("no probe pack at %s: no probe is served", folder)
        return EMPTY
    try:
        pack = ProbePack.model_validate_json(pack_path.read_text(encoding="utf-8"))
        arrays = _read_arrays(folder / WEIGHTS_FILE)
    except (ValidationError, OSError, KeyError, ValueError, zipfile.BadZipFile) as error:
        logger.error("the probe pack at %s cannot be read: %s", folder, error)
        return EMPTY
    if pack.embedding_key != embedding_key:
        # A probe is never applied to vectors of another model, prefix or dimension.
        logger.warning(
            "the probe pack was fitted on %s and this server embeds with %s: no probe is served",
            pack.embedding_key,
            embedding_key,
        )
        return EMPTY
    if not _shapes_agree(arrays):
        logger.warning(
            "the probe weights at %s have inconsistent shapes: no probe is served", folder
        )
        return EMPTY
    probes = _fold(pack, arrays)
    logger.info(
        "loaded %d probes (%d shown) of run %s", len(probes.infos), len(probes.shown()), pack.run
    )
    return probes

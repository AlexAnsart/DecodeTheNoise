"""A hand-made probe pack in a folder: known cuts, seeded weights. No model is involved."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backend.probes.schema import (
    PACK_FILE,
    WEIGHTS_FILE,
    LevelMeasure,
    PackedProbe,
    ProbeInfo,
    ProbePack,
    ProbeState,
)

# The key and size of the tiny build of `conftest.py`, so a pack can be applied to it.
PACK_EMBEDDING_KEY = "test-model@0|prefix=''|dims=4"
PACK_DIMS = 4
POSSIBLE_MEASURE = LevelMeasure(
    precision=0.7,
    precision_low=0.6,
    precision_high=0.8,
    false_positive_rate=0.03,
    recall=0.5,
    read=60,
    flag_rate=0.05,
)
PROBABLE_MEASURE = LevelMeasure(
    precision=0.9,
    precision_low=0.8,
    precision_high=0.96,
    false_positive_rate=0.01,
    recall=0.3,
    read=40,
    flag_rate=0.02,
)


@dataclass(frozen=True)
class FakeProbe:
    """A level exists in the pack when its cut is given; its measure can be left out. A
    review-only probe can be given the cut from which it sends an item to the review."""

    key: str
    possible_cut: float | None = None
    probable_cut: float | None = None
    state: ProbeState = "shown"
    measured_possible: bool = True
    measured_probable: bool = True
    review_cut: float | None = None
    reviewable: bool = True


def _packed(probe: FakeProbe) -> PackedProbe:
    has_possible = probe.possible_cut is not None and probe.measured_possible
    has_probable = probe.probable_cut is not None and probe.measured_probable
    info = ProbeInfo(
        key=probe.key,
        label=probe.key.replace("_", " ").capitalize(),
        description=f"Does the post show {probe.key}?",
        family="test",
        state=probe.state,
        possible=POSSIBLE_MEASURE if has_possible else None,
        probable=PROBABLE_MEASURE if has_probable else None,
        report="probes",
    )
    return PackedProbe(
        info=info,
        possible_cut=probe.possible_cut,
        probable_cut=probe.probable_cut,
        review_cut=probe.review_cut,
        reviewable=probe.reviewable,
    )


def write_pack(
    folder: Path,
    probes: list[FakeProbe],
    embedding_key: str = PACK_EMBEDDING_KEY,
    dims: int = PACK_DIMS,
    seed: int = 0,
) -> dict[str, np.ndarray]:
    """Writes `probes.json` and `probes.npz`; returns the arrays, to recompute a logit by hand."""
    rng = np.random.default_rng(seed)
    arrays = {
        "names": np.array([probe.key for probe in probes]),
        "weights": rng.normal(size=(len(probes), dims)).astype(np.float32),
        "bias": rng.normal(size=len(probes)),
        "mean": rng.normal(scale=0.05, size=dims).astype(np.float32),
        "scale": rng.uniform(0.02, 0.08, size=dims).astype(np.float32),
    }
    pack = ProbePack(
        embedding_key=embedding_key,
        run="test-run",
        exported_at="2026-11-14T00:00:00+00:00",
        probes=[_packed(probe) for probe in probes],
    )
    folder.mkdir(parents=True, exist_ok=True)
    (folder / PACK_FILE).write_text(pack.model_dump_json(), encoding="utf-8")
    np.savez(folder / WEIGHTS_FILE, **arrays)
    return arrays


def raw_logits(arrays: dict[str, np.ndarray], vectors: np.ndarray) -> np.ndarray:
    """The probes' raw output, step by step: standardise, one dot product, a bias."""
    standardised = (vectors.astype(np.float64) - arrays["mean"]) / arrays["scale"]
    return standardised @ arrays["weights"].astype(np.float64).T + arrays["bias"]


def vector_with_logits(arrays: dict[str, np.ndarray], logits: list[float]) -> np.ndarray:
    """A vector whose raw outputs are `logits`, one per probe (at most `dims` probes)."""
    weights = arrays["weights"].astype(np.float64)
    standardised = np.linalg.pinv(weights) @ (np.asarray(logits) - arrays["bias"])
    return (standardised * arrays["scale"] + arrays["mean"]).astype(np.float32)

"""A probe as the API shows it, and the pack of probes the server loads.

A probe is a linear read-out of an embedding vector. Its raw output is rescaled so that the two
levels sit at the same score for every probe: `possible` starts at 0.5 and `probable` at 0.8.
The score is therefore a position against the probe's own measured thresholds, not a
probability. What a level is worth is in its measure, taken on held-out posts.
"""

from typing import Literal

from pydantic import BaseModel

PACK_FILE = "probes.json"
WEIGHTS_FILE = "probes.npz"

POSSIBLE_SCORE = 0.5
PROBABLE_SCORE = 0.8

ProbeState = Literal["shown", "review-only"]
FlagLevel = Literal["possible", "probable"]


class LevelMeasure(BaseModel):
    """What the held-out test split measured at one level of one probe."""

    precision: float
    precision_low: float
    precision_high: float
    false_positive_rate: float | None
    recall: float | None
    # Flagged posts that were read on the test split, and the share of the split flagged.
    read: int
    flag_rate: float


class ProbeInfo(BaseModel):
    """`review-only` probes never appear in the interface: they only send items to the review."""

    key: str
    label: str
    description: str
    family: str
    state: ProbeState
    possible: LevelMeasure | None
    probable: LevelMeasure | None
    # Folder under `reports/` that holds the evaluation this probe was shipped on.
    report: str


class ProbeReading(BaseModel):
    """One probe that flagged one item: the level, and how reliable that level measured to be."""

    key: str
    label: str
    score: float
    level: FlagLevel
    reliability: LevelMeasure
    report: str


class PackedProbe(BaseModel):
    """One probe of the pack. The thresholds are cuts on the raw output (the logit)."""

    info: ProbeInfo
    possible_cut: float | None
    probable_cut: float | None


class ProbePack(BaseModel):
    """`probes.json`. `probes.npz` beside it holds `names`, `weights`, `bias`, `mean`, `scale`:
    one row of weights per name, in the standardised space `(vector - mean) / scale`."""

    embedding_key: str
    run: str
    exported_at: str
    probes: list[PackedProbe]

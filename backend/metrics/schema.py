"""A detector's measured reliability: the contract of `reports/<detector>/metrics.json`.

The file is written by the evaluation code of a detector. The API serves it as it is and
attaches it to every verdict of that detector; nothing in it is typed by hand.
"""

from pydantic import BaseModel, JsonValue

METRICS_FILE = "metrics.json"


class Measure(BaseModel):
    """One measured rate. `set` names the data it was measured on, caveats included."""

    name: str
    kind: str
    set: str
    n: int
    value: float
    low: float | None = None
    high: float | None = None


class PrecisionAtBaseRate(BaseModel):
    """What precision becomes when `prevalence` of the units are positive."""

    prevalence: float
    precision: float
    low: float | None = None
    high: float | None = None


class FailureMode(BaseModel):
    """A kind of false positive found in the audit, and what the product does about it."""

    mode: str
    example: str
    response: str


class DetectorMetrics(BaseModel):
    detector: str
    title: str
    report: str
    date: str
    unit: str
    decides: str
    operating_point: dict[str, JsonValue]
    results: list[Measure]
    precision_at_base_rates: list[PrecisionAtBaseRate]
    false_positive_modes: list[FailureMode]
    untested: list[str]


class MetricsResponse(BaseModel):
    detectors: list[DetectorMetrics]

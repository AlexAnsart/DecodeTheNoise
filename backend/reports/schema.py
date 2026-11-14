"""What the method page reads: the probes served, and every committed evaluation report."""

from pydantic import BaseModel

from backend.probes.schema import ProbeInfo

METRICS_FILE = "metrics.json"


class Report(BaseModel):
    """One `metrics.json`, as the evaluation wrote it. Its shape belongs to its detector."""

    # Folder of the report under `reports/`, for example "probes".
    detector: str
    metrics: dict[str, object]


class Metrics(BaseModel):
    # The probes shown in the interface, each with what its levels measured.
    probes: list[ProbeInfo]
    reports: list[Report]

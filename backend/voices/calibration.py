"""What the one-voice check measured to be worth: read from its evaluation report.

The thresholds and the counts the interface quotes come from `reports/voices/metrics.json`,
written by `pipelines/briefs/voices_report.py`. Without that file the check stays off.
"""

import json
import logging
from pathlib import Path

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

REPORT = "voices"
METRICS_FILE = "metrics.json"


class Count(BaseModel):
    groups: int
    flagged: int


class Reference(BaseModel):
    """Where 90% of the measured groups score."""

    independent: tuple[float, float]
    one_brief: tuple[float, float]


class SizeCalibration(BaseModel):
    actors: int
    posts_each: int
    threshold: float
    reference: Reference
    real: Count  # held-out real groups, actors drawn at random
    real_alike: Count  # held-out real groups, the most alike actors
    one_brief: Count  # groups written from one brief


class Calibration(BaseModel):
    embedding_key: str
    sizes: list[SizeCalibration]

    def at(self, size: tuple[int, int]) -> SizeCalibration | None:
        for entry in self.sizes:
            if (entry.actors, entry.posts_each) == size:
                return entry
        return None


def load_calibration(reports_dir: Path) -> Calibration | None:
    """None when the check was never measured, or its report cannot be read."""
    path = reports_dir / REPORT / METRICS_FILE
    if not path.is_file():
        return None
    try:
        return Calibration.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        logger.warning("the report of the one-voice check cannot be read: %s", error)
        return None

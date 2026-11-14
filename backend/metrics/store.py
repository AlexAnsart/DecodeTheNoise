"""Loads the committed evaluation reports once at start-up."""

import logging
from pathlib import Path

from pydantic import ValidationError

from backend.metrics.schema import METRICS_FILE, DetectorMetrics

logger = logging.getLogger(__name__)


def load_metrics(reports_dir: Path) -> dict[str, DetectorMetrics]:
    """Metrics by detector name. A file that does not fit the contract is left out, and so
    is its layer: a detector without a readable report is not shown."""
    found: dict[str, DetectorMetrics] = {}
    for path in sorted(reports_dir.glob(f"*/{METRICS_FILE}")):
        try:
            metrics = DetectorMetrics.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError as error:
            logger.error("%s does not fit the metrics contract: %s", path, error)
            continue
        found[metrics.detector] = metrics
    logger.info("loaded the metrics of %d detectors: %s", len(found), ", ".join(found) or "none")
    return found

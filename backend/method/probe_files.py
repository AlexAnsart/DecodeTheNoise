"""The files of the probe evaluation the method page reads beside the metrics: the agreement
between readings, the prevalence of each label, the thresholds, the audit. Counts and rates
only, served as the evaluation wrote them."""

import json
import logging
from pathlib import Path

from backend.method.labels import PROBE_REPORT
from backend.reports.schema import METRICS_FILE

logger = logging.getLogger(__name__)


def probe_files_of(reports: Path) -> dict[str, object]:
    """Every JSON file of the probe report but the metrics, under its name without `.json`.
    A file that is not a JSON object or list is left out."""
    folder = reports / PROBE_REPORT
    if not folder.is_dir():
        return {}
    found: dict[str, object] = {}
    for path in sorted(folder.glob("*.json")):
        if path.name == METRICS_FILE:
            continue
        try:
            # Python writes NaN and Infinity in JSON and browsers refuse them: they become null.
            content = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda _: None)
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("probe file %s cannot be read: %s", path, error)
            continue
        if isinstance(content, dict | list):
            found[path.stem] = content
    return found

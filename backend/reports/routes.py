"""Serves the evaluation reports: every number the interface shows about a detector is here.

The reports are the `metrics.json` files written by the evaluation code under `reports/`.
Nothing is typed by hand between the measure and the page.
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Request

from backend.probes.scoring import Probes
from backend.reports.schema import METRICS_FILE, Metrics, Report

router = APIRouter(tags=["reports"])

logger = logging.getLogger(__name__)


def _no_value(_constant: str) -> None:
    """Python writes NaN and Infinity in JSON and browsers refuse them: they become null."""
    return None


def read_reports(folder: Path) -> list[Report]:
    """One report per `metrics.json` under `folder`, in path order. No folder, no report."""
    if not folder.is_dir():
        return []
    reports = []
    for path in sorted(folder.rglob(METRICS_FILE)):
        try:
            metrics = json.loads(path.read_text(encoding="utf-8"), parse_constant=_no_value)
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("report %s cannot be read: %s", path, error)
            continue
        if not isinstance(metrics, dict):
            logger.warning("report %s is not a JSON object: skipped", path)
            continue
        reports.append(Report(detector=path.parent.relative_to(folder).as_posix(), metrics=metrics))
    return reports


@router.get("/metrics")
def metrics(request: Request) -> Metrics:
    probes: Probes = request.app.state.probes
    reports_dir: Path = request.app.state.reports_dir
    return Metrics(probes=list(probes.shown()), reports=read_reports(reports_dir))

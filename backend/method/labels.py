"""The labels of the probe campaign as the method page lists them: what each one is for, the
closed question its guide asks, and what became of it once its probe was evaluated."""

import json
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ValidationError

from backend.method.schema import LabelDoc
from backend.reports.schema import METRICS_FILE

logger = logging.getLogger(__name__)

# Folder of the probe campaign's report under `reports/`.
PROBE_REPORT = "probes"
# A label with one probe per answer (`theme:sport`) takes the best state among them.
STATES = ("shown", "review-only", "dropped")


class TaxonomyLabel(Protocol):
    name: str
    family: str
    use: str
    values: tuple[str, ...]


class _Target(BaseModel):
    state: str | None = None


class _ProbeReport(BaseModel):
    targets: dict[str, _Target] = {}


def taxonomy_rows() -> Sequence[TaxonomyLabel]:
    """The label set of the campaign, in the order of its definition. A checkout without the
    campaign's code lists no label."""
    try:
        from pipelines.probes.taxonomy import LABELS
    except ImportError:
        return ()
    return LABELS


def _rank(state: str) -> int:
    return STATES.index(state) if state in STATES else len(STATES)


def states_of(reports: Path) -> dict[str, str]:
    """What became of each label after the evaluation; a label without a probe has none."""
    path = reports / PROBE_REPORT / METRICS_FILE
    if not path.is_file():
        return {}
    try:
        report = _ProbeReport.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        logger.warning("probe report %s cannot be read: %s", path, error)
        return {}
    states: dict[str, str] = {}
    for target, measured in report.targets.items():
        label = target.partition(":")[0]
        known = states.get(label)
        if measured.state and (known is None or _rank(measured.state) < _rank(known)):
            states[label] = measured.state
    return states


def labels_of(questions: dict[str, str], reports: Path) -> list[LabelDoc]:
    states = states_of(reports)
    return [
        LabelDoc(
            name=label.name,
            family=label.family,
            use=label.use,
            values=list(label.values),
            question=questions.get(label.name),
            state=states.get(label.name),
        )
        for label in taxonomy_rows()
    ]

"""The demo build as the method page describes it: its size, and where its posts come from."""

import logging
from pathlib import Path

from pydantic import ValidationError

from backend.map.schema import PROVENANCE_FILE
from backend.map.store import MapBuild
from backend.method.schema import BuildFacts, Provenance

logger = logging.getLogger(__name__)


def build_facts(build: MapBuild) -> BuildFacts:
    manifest = build.manifest
    return BuildFacts(
        name=manifest.build,
        points=manifest.n,
        zones=len(manifest.zones),
        built_at=manifest.built_at,
        embedding_key=manifest.embedding_key,
        dims=manifest.dims,
    )


def read_provenance(folder: Path) -> Provenance | None:
    """What `pipelines.pack` wrote beside the map. A build packed before it did has none."""
    path = folder / PROVENANCE_FILE
    if not path.is_file():
        return None
    try:
        return Provenance.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as error:
        logger.warning("provenance %s cannot be read: %s", path, error)
        return None

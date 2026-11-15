"""`data/MANIFEST.json`: which datasets were fetched, from where, under which licence."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pipelines.ingest.fetch import sha256_of
from pipelines.paths import DATASET_MANIFEST


@dataclass(frozen=True)
class Dataset:
    """One fetched dataset. `folder` is its home under `data/datasets/`."""

    name: str
    source: str
    licence: str
    fetch: str
    folder: Path
    files: tuple[Path, ...]


def record(dataset: Dataset) -> None:
    """Replaces this dataset's entry; the entries of the other datasets are kept as they are."""
    manifest = {"datasets": []}
    if DATASET_MANIFEST.exists():
        manifest = json.loads(DATASET_MANIFEST.read_text(encoding="utf-8"))
    entry = {
        "name": dataset.name,
        "source": dataset.source,
        "licence": dataset.licence,
        "fetched": datetime.now(UTC).date().isoformat(),
        "fetch": dataset.fetch,
        "path": dataset.folder.as_posix(),
        "files": [
            {"name": p.name, "bytes": p.stat().st_size, "sha256": sha256_of(p)}
            for p in dataset.files
        ],
    }
    others = [d for d in manifest["datasets"] if d["name"] != dataset.name]
    DATASET_MANIFEST.write_text(
        json.dumps({"datasets": [*others, entry]}, indent=2) + "\n", encoding="utf-8"
    )

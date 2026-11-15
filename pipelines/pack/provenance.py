"""Says where the items of a build come from: `provenance.json`, written beside the map.

The corpus of a build records its dataset, the revision and the files read. A build drawn as a
sample of other builds records how it was drawn; its dataset is then read in the corpus of each
source that is on disk. The address and the licence of a dataset are those of
`data/MANIFEST.json`, as they are: a licence that is not stated is said to be not stated.

Run alone, for a build packed before this file existed:
    uv run python -m pipelines.pack.provenance --name tweets-2026-500k [--current]
"""

import argparse
import json
import logging
import shutil
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel

from backend.map.schema import MANIFEST_FILE, PROVENANCE_FILE, MapManifest
from backend.method.schema import Provenance
from pipelines.corpus import read_meta
from pipelines.pack.publish import CURRENT
from pipelines.paths import CORPUS_FILE, DATASET_MANIFEST, build_dir, work_dir

log = logging.getLogger("pack.provenance")


class _Dataset(BaseModel):
    name: str
    source: str | None = None
    licence: str | None = None


class _Datasets(BaseModel):
    datasets: list[_Dataset] = []


def _distinct(values: Iterable[str | None]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def provenance_of(work: Path, manifest: Path = DATASET_MANIFEST) -> Provenance:
    meta = read_meta(work / CORPUS_FILE)
    sample = json.loads(meta["sample"]) if "sample" in meta else None
    metas = [meta]
    if sample is not None:
        # The sources of a sample are builds whose working folders sit beside its own.
        corpora = [work.parent / source / CORPUS_FILE for source in sample["sources"]]
        metas = [read_meta(path) for path in corpora if path.is_file()]
    datasets = _distinct(found.get("dataset") for found in metas)
    listed = (
        _Datasets.model_validate_json(manifest.read_text(encoding="utf-8")).datasets
        if manifest.is_file()
        else []
    )
    # An address and a licence are given for one dataset, never guessed for a mix of several.
    entry = next((d for d in listed if [d.name] == datasets), None)
    return Provenance(
        dataset=", ".join(datasets) or None,
        source_url=entry.source if entry else None,
        revision=", ".join(_distinct(found.get("revision") for found in metas)) or None,
        files=_distinct(name for found in metas for name in found.get("files", "").split(",")),
        licence=entry.licence if entry else None,
        sample=sample,
    )


def write_provenance(work: Path, out: Path, manifest: Path = DATASET_MANIFEST) -> Provenance:
    provenance = provenance_of(work, manifest)
    (out / PROVENANCE_FILE).write_text(provenance.model_dump_json(indent=1), encoding="utf-8")
    return provenance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--current", action="store_true", help="also write it into 'current'")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    out = build_dir(args.name)
    provenance = write_provenance(work_dir(args.name), out)
    log.info("%s: %s, %d files", args.name, provenance.dataset, len(provenance.files))
    if args.current:
        current = build_dir(CURRENT)
        served = MapManifest.model_validate_json((current / MANIFEST_FILE).read_text("utf-8"))
        if served.build != args.name:
            raise SystemExit(f"'{CURRENT}' holds {served.build}, not {args.name}: nothing copied")
        shutil.copyfile(out / PROVENANCE_FILE, current / PROVENANCE_FILE)
        log.info("copied into '%s'", CURRENT)


if __name__ == "__main__":
    main()

"""Downloads the IRA tweets published by FiveThirtyEight and records them in the manifest.

Run: uv run python -m pipelines.ingest.fetch [--files 1 2 13]
"""

import argparse
import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx

from pipelines.paths import DATASET_MANIFEST, RAW

log = logging.getLogger("ingest.fetch")

DATASET = "ira-tweets-fivethirtyeight"
SOURCE = "https://github.com/fivethirtyeight/russian-troll-tweets"
RAW_URL = "https://raw.githubusercontent.com/fivethirtyeight/russian-troll-tweets/master/{name}"
ALL_FILES = tuple(range(1, 14))
IRA_DIR = RAW / "ira"


def file_name(index: int) -> str:
    return f"IRAhandle_tweets_{index}.csv"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(index: int) -> Path:
    """Fetches one file unless it is already there. A partial download never keeps the name."""
    target = IRA_DIR / file_name(index)
    if target.exists():
        return target
    partial = target.with_suffix(".part")
    with httpx.stream("GET", RAW_URL.format(name=target.name), timeout=60.0) as response:
        response.raise_for_status()
        with partial.open("wb") as out:
            for chunk in response.iter_bytes(1 << 20):
                out.write(chunk)
    partial.replace(target)
    log.info("fetched %s (%d bytes)", target.name, target.stat().st_size)
    return target


def write_manifest(paths: list[Path]) -> None:
    """Replaces this dataset's entry, listing every file present on disk."""
    manifest = {"datasets": []}
    if DATASET_MANIFEST.exists():
        manifest = json.loads(DATASET_MANIFEST.read_text(encoding="utf-8"))
    entry = {
        "name": DATASET,
        "source": SOURCE,
        "licence": "not stated",
        "fetched": datetime.now(UTC).date().isoformat(),
        "fetch": "uv run python -m pipelines.ingest.fetch",
        "files": [
            {"name": p.name, "bytes": p.stat().st_size, "sha256": sha256_of(p)} for p in paths
        ],
    }
    others = [d for d in manifest["datasets"] if d["name"] != DATASET]
    DATASET_MANIFEST.write_text(
        json.dumps({"datasets": [*others, entry]}, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files", type=int, nargs="*", default=list(ALL_FILES))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    IRA_DIR.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(download, args.files))
    present = sorted(IRA_DIR.glob("IRAhandle_tweets_*.csv"), key=lambda p: p.name)
    write_manifest(present)
    log.info("manifest lists %d files", len(present))


if __name__ == "__main__":
    main()

"""Downloads one published file to disk."""

import logging
from pathlib import Path

import httpx

from pipelines.ingest.fetch import sha256_of

log = logging.getLogger("datasets.download")


def fetch(url: str, target: Path, sha256: str | None = None) -> Path:
    """Fetches the file unless it is there. A partial or altered file never keeps the name."""
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as response:
        response.raise_for_status()
        with partial.open("wb") as out:
            for chunk in response.iter_bytes(1 << 20):
                out.write(chunk)
    if sha256 is not None and sha256_of(partial) != sha256:
        raise ValueError(f"{url} no longer serves the file this project was built on")
    partial.replace(target)
    log.info("fetched %s (%d bytes)", target.name, target.stat().st_size)
    return target

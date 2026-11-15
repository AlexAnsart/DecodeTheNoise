"""Downloads shards of the 2026 sample of X posts published on Hugging Face.

The dataset holds 75.8M posts in 73 Parquet shards (25.7 GB), collected through Nitter by
sweeping a newspaper vocabulary. Nothing is labelled and no licence is stated. A shard holds
the posts found for a run of search terms, so the default takes shards across the whole range.
Writes `data/datasets/tweets-sample-2026/download/`. The full-size vectors of this dataset go
beside it in `embeddings/`, apart from the cache the other corpora share: pass that folder as
`--cache` to `pipelines.embed`.

Run: uv run python -m pipelines.datasets.tweets_2026 [--shards 0 18 36 54 72]
"""

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pipelines.datasets.download import fetch
from pipelines.datasets.manifest import Dataset, record
from pipelines.paths import DATASETS

log = logging.getLogger("datasets.tweets_2026")

NAME = "tweets-sample-2026"
SOURCE = "https://huggingface.co/datasets/SinclairSchneider/tweets_sample_2026"
# A pinned commit: the files behind it cannot change.
REVISION = "254bbe4cea800035ec544cf047d8b3bebc24fe99"
N_SHARDS = 73
DEFAULT_SHARDS = (0, 18, 36, 54, 72)
DOWNLOAD_DIR = DATASETS / NAME / "download"
CARD = "README.md"


def shard_path(index: int) -> str:
    return f"data/train-{index:05d}-of-{N_SHARDS:05d}.parquet"


def download(path: str) -> Path:
    return fetch(f"{SOURCE}/resolve/{REVISION}/{path}", DOWNLOAD_DIR / Path(path).name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards", type=int, nargs="*", default=list(DEFAULT_SHARDS))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(download, [CARD, *map(shard_path, args.shards)]))
    present = tuple(sorted(DOWNLOAD_DIR.glob("*.parquet")))
    record(
        Dataset(
            name=NAME,
            source=SOURCE,
            licence="not stated",
            fetch="uv run python -m pipelines.datasets.tweets_2026",
            folder=DATASETS / NAME,
            files=(DOWNLOAD_DIR / CARD, *present),
        )
    )
    log.info("manifest lists %d shards of %d", len(present), N_SHARDS)


if __name__ == "__main__":
    main()

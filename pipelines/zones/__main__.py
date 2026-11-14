"""Clusters the vectors into zones and finds the words that set each zone apart.

Run: uv run python -m pipelines.zones --name ira-3k
"""

import argparse
import json
import logging

import numpy as np

from backend.map.schema import ZoneInfo
from pipelines import runlog
from pipelines.corpus import read_corpus
from pipelines.paths import CORPUS_FILE, ZONE_OF_POINT_FILE, ZONES_FILE, work_dir
from pipelines.vectors import read_vectors
from pipelines.zones.kmeans import spherical_kmeans, zone_count
from pipelines.zones.words import distinctive_words

log = logging.getLogger("zones")

SEED = 42
NAME_WORDS = 3


def by_size(labels: np.ndarray) -> np.ndarray:
    """Relabels so that zone 0 is the largest: the id is the rank the legend shows."""
    sizes = np.bincount(labels)
    order = np.lexsort((np.arange(len(sizes)), -sizes))
    rank = np.empty(len(sizes), dtype=np.int64)
    rank[order] = np.arange(len(sizes))
    return rank[labels]


def describe(zone_of_point: np.ndarray, texts: list[str]) -> list[ZoneInfo]:
    count = int(zone_of_point.max()) + 1
    grouped: list[list[str]] = [[] for _ in range(count)]
    for zone, text in zip(zone_of_point.tolist(), texts, strict=True):
        grouped[zone].append(text)
    words = distinctive_words(grouped)
    return [
        ZoneInfo(
            id=zone,
            # Its words stand in for a name until the LLM pass gives it one.
            name=" · ".join(words[zone][:NAME_WORDS]),
            words=words[zone],
            size=len(grouped[zone]),
            named=False,
        )
        for zone in range(count)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    work = work_dir(args.name)
    vectors, _ = read_vectors(work)
    texts = [item.text for item in read_corpus(work / CORPUS_FILE)]
    with runlog.timed() as elapsed:
        zone_of_point = by_size(spherical_kmeans(vectors, zone_count(len(vectors)), SEED))
        zones = describe(zone_of_point, texts)
    np.save(work / ZONE_OF_POINT_FILE, zone_of_point.astype(np.uint16))
    payload = [zone.model_dump() for zone in zones]
    (work / ZONES_FILE).write_text(json.dumps(payload, ensure_ascii=False, indent=1), "utf-8")
    runlog.record("zones", args.name, len(vectors), elapsed[0])
    log.info("%d zones over %d points in %.1fs", len(zones), len(vectors), elapsed[0])


if __name__ == "__main__":
    main()

"""Clusters the vectors into zones and finds the words that set each zone apart.

Run: uv run python -m pipelines.zones --name ira-3k
"""

import argparse
import json
import logging

import numpy as np

from pipelines import runlog
from pipelines.corpus import read_corpus
from pipelines.paths import CORPUS_FILE, ZONE_OF_POINT_FILE, ZONES_FILE, work_dir
from pipelines.vectors import read_vectors
from pipelines.zones.describe import by_size, describe
from pipelines.zones.kmeans import spherical_kmeans, zone_count

log = logging.getLogger("zones")

SEED = 42


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

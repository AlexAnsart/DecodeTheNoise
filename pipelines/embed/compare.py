"""Checks that another machine gives the same vectors as the ones already in the cache.

The same weights must embed the corpus offline and a pasted text online, wherever they run.
Point `EMBEDDING_API_BASE` at the endpoint to check (an SSH tunnel to its Ollama is enough):

Run: EMBEDDING_API_BASE=http://localhost:11435/v1 PIPELINE_MACHINE="..." \
     uv run python -m pipelines.embed.compare --name ira-3k --count 100
"""

import argparse
import dataclasses
import logging
import random

import numpy as np

from backend.model_client.embedding import EmbeddingClient, fit_vectors
from backend.settings import get_settings
from pipelines import runlog
from pipelines.corpus import read_corpus
from pipelines.embed.__main__ import ALL_DIMS, store_folder
from pipelines.embed.ollama import model_revision
from pipelines.embed.store import VectorStore
from pipelines.ingest.ira import content_hash
from pipelines.paths import CORPUS_FILE, work_dir

log = logging.getLogger("embed.compare")
SEED = 42


def cosines(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine of each row of `a` to the same row of `b`."""
    dots = np.einsum("ij,ij->i", a, b)
    return dots / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="a build whose texts are in the cache")
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    settings = get_settings()
    revision = model_revision(settings.embedding_api_base, settings.embedding_model)
    key = dataclasses.replace(settings.embedding_key(), revision=revision)
    items = read_corpus(work_dir(args.name) / CORPUS_FILE)
    texts = [item.text for item in random.Random(SEED).sample(items, min(args.count, len(items)))]
    # Opening the store fails if the endpoint serves other weights than the cached ones.
    store = VectorStore(store_folder(key), f"{key.model}@{key.revision}|prefix={key.prefix!r}")
    cached = store.rows([content_hash(text) for text in texts])

    native = dataclasses.replace(key, dims=ALL_DIMS)
    client = EmbeddingClient(settings.embedding_api_base, settings.embedding_api_key, native)
    with runlog.timed() as elapsed:
        fresh = client.embed(texts)
    client.close()

    full = cosines(fresh, cached)
    served = cosines(fit_vectors(fresh, key.dims), fit_vectors(cached, key.dims))
    note = (
        f"cosine to the cached vectors: mean {full.mean():.5f}, min {full.min():.5f} "
        f"({fresh.shape[1]} dims); mean {served.mean():.5f}, min {served.min():.5f} "
        f"({key.dims} dims served)"
    )
    runlog.record("embed-check", args.name, len(texts), elapsed[0], note=note)
    log.info("%d texts, %s", len(texts), note)


if __name__ == "__main__":
    main()

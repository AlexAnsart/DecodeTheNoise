"""Embeds the unique texts of a corpus and writes the vectors the build serves.

Run: uv run python -m pipelines.embed --name ira-3k
"""

import argparse
import dataclasses
import hashlib
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend.model_client.embedding import EmbeddingClient, EmbeddingKey, fit_vectors
from backend.settings import get_settings
from pipelines import runlog
from pipelines.corpus import read_corpus
from pipelines.embed.ollama import model_revision, remember_in_env
from pipelines.embed.store import VectorStore
from pipelines.ingest.ira import content_hash
from pipelines.paths import CORPUS_FILE, EMBEDDINGS, work_dir
from pipelines.vectors import write_vectors

log = logging.getLogger("embed")

# Larger than any model's output: the cache keeps every dimension, the build keeps `key.dims`.
ALL_DIMS = 1 << 16


def store_folder(key: EmbeddingKey) -> Path:
    """One cache per weights and prefix; the number of dimensions kept does not split it."""
    prefix_tag = hashlib.sha256(key.prefix.encode("utf-8")).hexdigest()[:8]
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{key.model}-{key.revision}-{prefix_tag}")
    return EMBEDDINGS / slug


def embed_missing(
    client: EmbeddingClient, store: VectorStore, texts: dict[str, str], batch: int, workers: int
) -> int:
    """Embeds the texts the store lacks and returns how many that was."""
    todo = store.missing(list(texts))
    chunks = [todo[i : i + batch] for i in range(0, len(todo), batch)]
    start = time.perf_counter()
    done = 0
    with ThreadPoolExecutor(workers) as pool:
        results = pool.map(lambda chunk: client.embed([texts[h] for h in chunk]), chunks)
        for chunk, vectors in zip(chunks, results, strict=True):
            store.add(chunk, vectors)
            done += len(chunk)
            if done % (batch * 20) < batch:
                rate = done / (time.perf_counter() - start)
                log.info("%d / %d embedded, %.1f items/s", done, len(todo), rate)
    return len(todo)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    settings = get_settings()
    revision = model_revision(settings.embedding_api_base, settings.embedding_model)
    key = dataclasses.replace(settings.embedding_key(), revision=revision)
    remember_in_env(Path(".env"), "EMBEDDING_REVISION", revision)

    work = work_dir(args.name)
    items = read_corpus(work / CORPUS_FILE)
    hashes = [content_hash(item.text) for item in items]
    texts = dict(zip(hashes, (item.text for item in items), strict=True))
    native = dataclasses.replace(key, dims=ALL_DIMS)
    client = EmbeddingClient(settings.embedding_api_base, settings.embedding_api_key, native)
    store = VectorStore(store_folder(key), f"{key.model}@{key.revision}|prefix={key.prefix!r}")
    with runlog.timed() as elapsed:
        embedded = embed_missing(client, store, texts, args.batch, args.workers)
    client.close()

    write_vectors(work, fit_vectors(store.rows(hashes), key.dims), str(key), store.width)
    runlog.record("embed", args.name, embedded, elapsed[0])
    rate = embedded / elapsed[0] if embedded else 0.0
    log.info("%d items, %d embedded now at %.1f items/s, key %s", len(items), embedded, rate, key)


if __name__ == "__main__":
    main()

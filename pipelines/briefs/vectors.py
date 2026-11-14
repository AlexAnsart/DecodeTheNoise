"""Vectors for benchmark texts, from the same model and prefix as the served builds."""

import dataclasses

import numpy as np

from backend.model_client.embedding import EmbeddingClient, EmbeddingKey, fit_vectors
from backend.settings import get_settings
from pipelines.briefs.bench import BENCH
from pipelines.embed.__main__ import ALL_DIMS, embed_missing, store_folder
from pipelines.embed.ollama import model_revision
from pipelines.embed.store import VectorStore
from pipelines.ingest.ira import content_hash

# The benchmark keeps its own cache: two processes appending to one store would corrupt it,
# and other sessions embed into the shared one.
CACHE = BENCH / "embeddings"


def served_key() -> EmbeddingKey:
    """The key of the model the endpoint serves now, at the served dimension."""
    settings = get_settings()
    revision = model_revision(settings.embedding_api_base, settings.embedding_model)
    return dataclasses.replace(settings.embedding_key(), revision=revision)


def embed(texts: list[str]) -> tuple[np.ndarray, str]:
    """One unit vector per text at the served dimension, and the embedding key they carry.

    Only texts the cache lacks are sent to the model.
    """
    settings = get_settings()
    key = served_key()
    hashes = [content_hash(text) for text in texts]
    native = dataclasses.replace(key, dims=ALL_DIMS)
    client = EmbeddingClient(settings.embedding_api_base, settings.embedding_api_key, native)
    store = VectorStore(
        CACHE / store_folder(key).name, f"{key.model}@{key.revision}|prefix={key.prefix!r}"
    )
    embed_missing(client, store, dict(zip(hashes, texts, strict=True)), batch=64, workers=2)
    client.close()
    return fit_vectors(store.rows(hashes), key.dims), str(key)

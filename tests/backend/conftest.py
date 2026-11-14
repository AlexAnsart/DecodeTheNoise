"""A tiny hand-made map build in a temp folder, and the API wired on it with fakes."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
from analyze_fakes import FakeEmbedder, FakeReader
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.analyze.coordinates import load_coordinates
from backend.analyze.rate_limit import RateLimiter
from backend.analyze.routes import router as analyze_router
from backend.map.schema import BUFFERS_FILE, ITEMS_FILE, MANIFEST_FILE, VECTORS_FILE, MapManifest
from backend.map.store import MapBuild, load_build
from backend.web_reader.context_dev import Page, PageUnreadable
from pipelines.ingest.ira import Item
from pipelines.pack.buffers import pack_buffers
from pipelines.pack.items import write_items

POINTS = 12
DIMS = 4
EMBEDDING_KEY = "test-model@0|prefix=''|dims=4"
ARTICLE_URL = "https://news.example/article"
BROKEN_URL = "https://news.example/gone"
EMPTY_URL = "https://news.example/empty"
ARTICLE_TITLE = "Officials deny the report"
ARTICLE_TEXT = "The ministry said on Monday that the report was false. " * 60


def _unit_rows(seed: int) -> np.ndarray:
    rows = np.random.default_rng(seed).normal(size=(POINTS, DIMS)).astype(np.float32)
    return rows / np.linalg.norm(rows, axis=1, keepdims=True)


def write_tiny_build(folder: Path) -> None:
    """Twelve points with known layouts: pos3[i] = (i, 2i, 3i), pos2[i] = (i, -i)."""
    steps = np.arange(POINTS, dtype=np.float32)
    blob, specs = pack_buffers(
        {
            "pos3": np.stack([steps, 2 * steps, 3 * steps], axis=1),
            "pos2": np.stack([steps, -steps], axis=1),
            "ts": np.zeros(POINTS, dtype=np.float64),
            "neighbours": np.zeros(0, dtype=np.uint32),
        }
    )
    (folder / BUFFERS_FILE).write_bytes(blob)
    manifest = MapManifest(
        build="tiny",
        built_at="2026-11-14T00:00:00Z",
        n=POINTS,
        k=0,
        embedding_key=EMBEDDING_KEY,
        dims=DIMS,
        time_min=None,
        time_max=None,
        columns=[],
        zones=[],
        buffers=specs,
    )
    (folder / MANIFEST_FILE).write_text(manifest.model_dump_json(), encoding="utf-8")
    _unit_rows(seed=7).astype(np.float16).tofile(folder / VECTORS_FILE)
    items = [
        Item(
            f"item{i}",
            "actor",
            f"post number {i}",
            None,
            "English",
            None,
            (),
            "Test",
            "original",
            0,
        )
        for i in range(POINTS)
    ]
    write_items(folder / ITEMS_FILE, items)


@dataclass
class Api:
    client: TestClient
    app: FastAPI
    build: MapBuild
    embedder: FakeEmbedder
    reader: FakeReader


@pytest.fixture
def api(tmp_path: Path) -> Iterator[Api]:
    write_tiny_build(tmp_path)
    build = load_build(tmp_path)
    assert build is not None
    embedder = FakeEmbedder(key=EMBEDDING_KEY, default=build.vectors[3])
    reader = FakeReader(
        pages={
            ARTICLE_URL: Page(ARTICLE_URL, ARTICLE_TITLE, ARTICLE_TEXT, "2026-11-14T09:30:00Z"),
            BROKEN_URL: PageUnreadable("The URL's hostname does not exist."),
            EMPTY_URL: Page(EMPTY_URL, "Empty", "Too short.", "2026-11-14T09:30:00Z"),
        }
    )
    app = FastAPI()
    app.include_router(analyze_router)
    app.state.build = build
    app.state.embedder = embedder
    app.state.coordinates = load_coordinates(build)
    app.state.page_reader = reader
    app.state.analyze_limiter = RateLimiter(limit=100, window=60.0)
    with TestClient(app) as client:
        yield Api(client=client, app=app, build=build, embedder=embedder, reader=reader)
    # Windows cannot remove the temp folder while the database is open.
    build.items.close()

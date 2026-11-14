"""The API. Loads the map build once; no training, layout or clustering happens here."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.analyze.coordinates import load_coordinates
from backend.analyze.rate_limit import RateLimiter
from backend.analyze.routes import REQUESTS_PER_WINDOW, WINDOW_SECONDS
from backend.analyze.routes import router as analyze_router
from backend.health.routes import router as health_router
from backend.items.routes import router as items_router
from backend.map.routes import router as map_router
from backend.map.store import load_build
from backend.model_client.embedding import EmbeddingClient
from backend.search.meaning import QueryEmbedder
from backend.search.routes import router as search_router
from backend.settings import get_settings
from backend.web_reader.context_dev import ContextDevReader

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    client = EmbeddingClient(
        settings.embedding_api_base,
        settings.embedding_api_key,
        settings.embedding_key(),
        timeout=30.0,
    )
    app.state.build = load_build(settings.data_build_dir)
    app.state.embedder = QueryEmbedder(client)
    # The paste box: the layouts to place a text, a reader for links, a limit per client.
    reader = (
        ContextDevReader(settings.context_dev_api_key, settings.context_dev_api_base)
        if settings.context_dev_api_key
        else None
    )
    app.state.coordinates = load_coordinates(app.state.build) if app.state.build else None
    app.state.page_reader = reader
    app.state.analyze_limiter = RateLimiter(REQUESTS_PER_WINDOW, WINDOW_SECONDS)
    yield
    if reader is not None:
        reader.close()
    client.close()
    if app.state.build is not None:
        app.state.build.items.close()


def create_app() -> FastAPI:
    app = FastAPI(title="NoiseMap API", lifespan=lifespan)
    for router in (health_router, map_router, items_router, search_router, analyze_router):
        app.include_router(router)
    return app


app = create_app()

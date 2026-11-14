"""The API. Loads the map build once; no training, layout or clustering happens here."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.health.routes import router as health_router
from backend.items.routes import router as items_router
from backend.map.routes import router as map_router
from backend.map.store import load_build
from backend.model_client.embedding import EmbeddingClient
from backend.search.meaning import QueryEmbedder
from backend.search.routes import router as search_router
from backend.settings import get_settings

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
    yield
    client.close()
    if app.state.build is not None:
        app.state.build.items.close()


def create_app() -> FastAPI:
    app = FastAPI(title="NoiseMap API", lifespan=lifespan)
    for router in (health_router, map_router, items_router, search_router):
        app.include_router(router)
    return app


app = create_app()

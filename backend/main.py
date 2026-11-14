"""The API. The demo build is loaded once and never changes; a workspace is a map that grows
with the items its owner sends. The same map routes serve both.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.accounts.deps import require_workspace
from backend.accounts.limits import BATCHES_PER_MINUTE, CREATIONS_PER_DAY, LIMITS
from backend.accounts.routes import router as accounts_router
from backend.analyze.coordinates import load_coordinates
from backend.analyze.rate_limit import RateLimiter
from backend.analyze.routes import REQUESTS_PER_WINDOW, WINDOW_SECONDS
from backend.analyze.routes import router as analyze_router
from backend.events.routes import router as events_router
from backend.health.routes import router as health_router
from backend.ingest.routes import router as ingest_router
from backend.items.routes import router as items_router
from backend.map.routes import router as map_router
from backend.map.store import load_build
from backend.model_client.embedding import EmbeddingClient
from backend.model_client.llm import ChatClient
from backend.probes.pack import load_probes
from backend.refresh.computing import ComputingProcess
from backend.refresh.layout import warm_up
from backend.reports.routes import router as reports_router
from backend.sample.routes import router as sample_router
from backend.search.meaning import QueryEmbedder
from backend.search.routes import router as search_router
from backend.services import start_services, stop_services
from backend.settings import get_settings
from backend.web_reader.context_dev import ContextDevReader
from backend.workspace.routes import router as workspace_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

MINUTE = 60.0
DAY = 86_400.0

# Read by anyone, on the demo build.
PUBLIC = (health_router, accounts_router, sample_router, reports_router)
# The map routes: the demo build under /api, the caller's workspace under /api/v1.
MAP = (map_router, items_router, search_router, analyze_router)
# What only the owner of a workspace does.
OWNER = (workspace_router, ingest_router, events_router)


def mount(app: FastAPI) -> None:
    for router in (*PUBLIC, *MAP):
        app.include_router(router, prefix="/api")
    for router in (*MAP, *OWNER):
        app.include_router(router, prefix="/api/v1", dependencies=[Depends(require_workspace)])


def set_limiters(app: FastAPI) -> None:
    app.state.analyze_limiter = RateLimiter(REQUESTS_PER_WINDOW, WINDOW_SECONDS)
    app.state.item_limiter = RateLimiter(LIMITS.requests_per_minute, MINUTE)
    app.state.batch_limiter = RateLimiter(BATCHES_PER_MINUTE, MINUTE)
    app.state.creation_limiter = RateLimiter(CREATIONS_PER_DAY, DAY)


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
    set_limiters(app)
    # The probes, read on the demo build and on every workspace.
    app.state.probes = load_probes(settings.probes_dir, str(client.key))
    app.state.reports_dir = settings.reports_dir
    app.state.score_cache = {}
    app.state.sample_cache = {}
    # The workspaces: stores, background jobs, the LLM that names zones and reviews flags.
    chat = (
        ChatClient(settings.llm_api_base, settings.llm_api_key, settings.llm_model)
        if settings.llm_api_key and settings.llm_model
        else None
    )
    services = start_services(
        settings.workspaces_dir,
        client,
        settings.embedding_dims,
        app.state.probes,
        chat,
        settings.llm_model,
        ComputingProcess(),
    )
    # The layout code compiles on first use: asked now, in the computing process, so that the
    # first refresh does not pay for it.
    services.computing.start(warm_up)
    services.hub.attach(asyncio.get_running_loop())
    app.state.services = services
    yield
    stop_services(services)
    if chat is not None:
        chat.close()
    if reader is not None:
        reader.close()
    client.close()
    if app.state.build is not None:
        app.state.build.items.close()


def create_app() -> FastAPI:
    app = FastAPI(title="NoiseMap API", lifespan=lifespan)
    # The key travels in a header, never in a cookie: any origin may call the API with it.
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    mount(app)
    return app


app = create_app()

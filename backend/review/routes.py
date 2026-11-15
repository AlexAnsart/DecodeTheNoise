"""The review asked for now: of one point of a map, or of a selection of points.

Mounted twice, like the other map routes: under `/api` for the demo build, under `/api/v1` for
the caller's workspace. Expected cost of a review that is not in the cache: one LLM call of
about 7,000 tokens in and a few hundred out (measured: docs/review.md), one matrix product of
n points by dims for the context, two item queries. A question already asked costs one lookup.
"""

import logging
from typing import Annotated

import httpx
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request

from backend.accounts.deps import get_services
from backend.accounts.limits import ALL_WORKSPACES, GLOBAL_REVIEWS_PER_DAY, REVIEWS
from backend.analyze.place import beginning
from backend.analyze.rate_limit import RateLimiter, client_address
from backend.map.deps import get_build, get_probes
from backend.map.routes import probe_scores
from backend.map.store import MapBuild
from backend.probes.scoring import Probes
from backend.review.context import actors_of, request_at, texts_of
from backend.review.reader import UNREADABLE
from backend.review.schema import Review, SelectionReview
from backend.review.selection import SelectionRequest, probe_rates, sample
from backend.review.selection_prompt import POST_CHARS, SELECTION_VERSION, SelectionAsk
from backend.services import Services
from backend.workspace.state import Workspace

router = APIRouter(tags=["review"])

logger = logging.getLogger(__name__)

# Reviews one address may ask of the demo each minute. A workspace has its daily limit instead.
REVIEWS_PER_MINUTE = 10
NO_LLM = "No LLM is configured on this server: the review is not available."
LLM_DOWN = "The LLM did not answer. Try again shortly."
NOTHING_TO_ASK = "No probe flags this item and no technique guide is loaded: nothing to review."
NO_POINT = "No point with this index on the map."


def _workspace(request: Request) -> Workspace | None:
    return getattr(request.state, "workspace", None)


def _spend(request: Request, services: Services, workspace: Workspace | None) -> None:
    """Counts one paid review, or refuses it when a limit is reached."""
    accounts = services.accounts
    if workspace is None:
        limiter: RateLimiter = request.app.state.review_limiter
        if not limiter.allow(client_address(request)):
            raise HTTPException(
                status_code=429,
                detail=f"Too many reviews from this address: at most {limiter.limit} a minute. "
                "Try again shortly.",
                headers={"Retry-After": "30"},
            )
    elif accounts.used_today(workspace.id, REVIEWS) >= workspace.limits.reviews_per_day:
        raise HTTPException(429, detail="The daily review limit of this workspace is used.")
    if accounts.used_today(ALL_WORKSPACES, REVIEWS) >= GLOBAL_REVIEWS_PER_DAY:
        raise HTTPException(429, detail="The daily review limit of this server is used.")
    if workspace is not None:
        accounts.use(workspace.id, REVIEWS)
    accounts.use(ALL_WORKSPACES, REVIEWS)


def _keep(services: Services, workspace: Workspace, index: int, text: str, review: Review) -> None:
    """Writes the review on the item of a workspace, and tells whoever watches its map."""
    with workspace.lock:
        with workspace.db_lock, workspace.db:
            # The item was sent again with another text meanwhile: this review is not about it.
            written = workspace.db.execute(
                "UPDATE items SET review = ? WHERE idx = ? AND text = ?",
                (review.model_dump_json(), index, text),
            ).rowcount
        if written:
            workspace.touch()
    if written:
        services.changed(workspace)


@router.post("/map/review/{index}")
def review_point(
    index: int,
    request: Request,
    build: Annotated[MapBuild, Depends(get_build)],
    probes: Annotated[Probes, Depends(get_probes)],
    services: Annotated[Services, Depends(get_services)],
) -> Review:
    """Reviews this point now: the probes that flag it, then the technique screen."""
    if not 0 <= index < build.manifest.n:
        raise HTTPException(status_code=404, detail=NO_POINT)
    reviewer = services.reviewer
    if reviewer.chat is None:
        raise HTTPException(status_code=503, detail=NO_LLM)
    asked = request_at(build, probes, index, "possible", 0.0)
    if asked is None:
        raise HTTPException(status_code=404, detail=NO_POINT)
    if not reviewer.has_something_to_ask(asked):
        return Review(status="skipped", reason=NOTHING_TO_ASK)
    workspace = _workspace(request)
    review = reviewer.known(asked)
    if review is None:
        _spend(request, services, workspace)
        try:
            review = reviewer.item(asked)
        except httpx.HTTPError as error:
            logger.warning("review of point %d failed: %s", index, error)
            return Review(status="failed", reason=LLM_DOWN)
    if workspace is not None and review.status == "done":
        _keep(services, workspace, index, asked.text, review)
    return review


@router.post("/review/selection")
def review_selection(
    body: SelectionRequest,
    request: Request,
    build: Annotated[MapBuild, Depends(get_build)],
    probes: Annotated[Probes, Depends(get_probes)],
    services: Annotated[Services, Depends(get_services)],
) -> SelectionReview:
    """What the probes measure on these points, then what the LLM reads in a sample of them.
    Without an LLM, or when it fails, the measured part is answered alone."""
    n = build.manifest.n
    if any(i < 0 or i >= n for i in body.indices):
        raise HTTPException(status_code=422, detail="indices: a point index is outside the map.")
    chosen = np.unique(np.asarray(body.indices, dtype=np.int64))
    actors = actors_of(build, chosen.tolist())
    measured = SelectionReview(
        status="skipped",
        reason=NO_LLM,
        posts=len(chosen),
        actors=len({actor for actor in actors.values() if actor}),
        rates=probe_rates(probes, probe_scores(request, build, probes), chosen),
    )
    reviewer = services.reviewer
    if reviewer.chat is None:
        return measured
    read = sample(build.vectors, chosen, actors)
    texts = texts_of(build, read)
    shown = [(i, beginning(" ".join(texts[i].split()), POST_CHARS)) for i in read if i in texts]
    ask = SelectionAsk(tuple(shown))
    reading = reviewer.known_selection(ask)
    if reading is None:
        _spend(request, services, _workspace(request))
        try:
            reading = reviewer.selection(ask)
        except httpx.HTTPError as error:
            logger.warning("review of a selection failed: %s", error)
            return measured.model_copy(update={"status": "failed", "reason": LLM_DOWN})
    if reading is None:
        return measured.model_copy(update={"status": "failed", "reason": UNREADABLE})
    return measured.model_copy(
        update={
            "status": "done",
            "reason": None,
            "read": [index for index, _ in ask.posts],
            "statement": reading.statement,
            "techniques": reading.techniques,
            "asks": reading.asks,
            "targets": reading.targets,
            "model": reviewer.model,
            "prompt_version": SELECTION_VERSION,
        }
    )

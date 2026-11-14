"""The paste box: a text or a link lands on the map with its nearest neighbours.

Expected cost of one request (to measure after any change): at most one page read through the
web reader (the only slow and paid part, kept by URL), one embedding of at most 1,200 characters
(kept by text), one matrix product of n points by dims, and a partial sort for ten neighbours.
No database query. A text under the minimum length, or a page that gave no text, costs neither
the embedding nor the product.
"""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from backend.analyze.coordinates import Coordinates
from backend.analyze.place import (
    beginning,
    nearest,
    neighbour_weights,
    weighted_position,
    with_title,
)
from backend.analyze.rate_limit import RateLimiter, client_address
from backend.analyze.schema import (
    EMBED_BUDGET_CHARS,
    MAX_RETURNED_CHARS,
    MIN_TEXT_CHARS,
    NEIGHBOURS,
    AnalyzeRequest,
    AnalyzeResponse,
    Neighbour,
    Source,
)
from backend.map.deps import get_build
from backend.map.store import MapBuild
from backend.search.meaning import QueryEmbedder
from backend.search.routes import get_embedder
from backend.web_reader.context_dev import PageReader, PageUnreadable

router = APIRouter(tags=["analyze"])

REQUESTS_PER_WINDOW = 20
EMPTY_MAP = "The map holds no point yet: there is nothing to place the text among."
WINDOW_SECONDS = 60.0


def enforce_rate_limit(request: Request) -> None:
    limiter: RateLimiter = request.app.state.analyze_limiter
    if not limiter.allow(client_address(request)):
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests from this address: at most {limiter.limit} a minute. "
            "Try again shortly.",
        )


def get_coordinates(
    request: Request, build: Annotated[MapBuild, Depends(get_build)]
) -> Coordinates:
    if build.pos3 is not None and build.pos2 is not None:
        # A workspace map: its layouts are in memory, and change as it grows.
        return Coordinates(pos3=build.pos3, pos2=build.pos2)
    coordinates: Coordinates = request.app.state.coordinates
    return coordinates


def _abstain(source: Source, reason: str, text: str = "") -> AnalyzeResponse:
    return AnalyzeResponse(
        outcome="not enough evidence",
        reason=reason,
        source=source,
        text=text[:MAX_RETURNED_CHARS],
        characters=len(text),
        position3=None,
        position2=None,
        neighbours=[],
        verdicts=[],
    )


@router.post("/analyze", dependencies=[Depends(enforce_rate_limit)])
def analyze(
    body: AnalyzeRequest,
    request: Request,
    build: Annotated[MapBuild, Depends(get_build)],
    embedder: Annotated[QueryEmbedder, Depends(get_embedder)],
    coordinates: Annotated[Coordinates, Depends(get_coordinates)],
) -> AnalyzeResponse:
    if body.url is not None:
        reader: PageReader | None = request.app.state.page_reader
        if reader is None:
            raise HTTPException(
                status_code=503,
                detail="Reading a link is not set up on this server: paste the text instead.",
            )
        try:
            page = reader.read(body.url)
        except PageUnreadable as error:
            unread = Source(kind="url", url=body.url, title=None, read_at=None)
            return _abstain(unread, error.reason)
        source = Source(kind="url", url=page.url, title=page.title, read_at=page.read_at)
        full = page.text
        opening = with_title(page.title, page.text)
        too_short = "The page holds too little text to be placed."
    else:
        source = Source(kind="text", url=None, title=None, read_at=None)
        full = (body.text or "").strip()
        opening = full
        too_short = f"The text is under {MIN_TEXT_CHARS} characters: too short to be placed."
    if len(full) < MIN_TEXT_CHARS:
        return _abstain(source, too_short, full)
    if build.manifest.n == 0:
        return _abstain(source, EMPTY_MAP, full)

    embedded = beginning(opening, EMBED_BUDGET_CHARS)
    try:
        vector = embedder.embed(embedded)
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=503, detail="The embedding model did not answer."
        ) from error
    indices, scores = nearest(build.vectors, vector, NEIGHBOURS)
    weights = neighbour_weights(scores)
    x3, y3, z3 = weighted_position(coordinates.pos3, indices, weights)
    x2, y2 = weighted_position(coordinates.pos2, indices, weights)
    return AnalyzeResponse(
        outcome="placed",
        reason=None,
        source=source,
        text=embedded[:MAX_RETURNED_CHARS],
        characters=len(full),
        position3=(x3, y3, z3),
        position2=(x2, y2),
        neighbours=[
            Neighbour(index=int(i), score=float(s)) for i, s in zip(indices, scores, strict=True)
        ],
        verdicts=[],
    )

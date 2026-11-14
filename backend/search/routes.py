"""Search routes. Each answers with one value per point, as raw bytes in point order."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from backend.map.deps import get_build
from backend.map.store import MapBuild
from backend.search.meaning import QueryEmbedder, scores_to_items, scores_to_vector
from backend.search.text import text_hits

router = APIRouter(prefix="/api", tags=["search"])

MAX_QUERY_CHARS = 500
MAX_SIMILAR_ITEMS = 5000
_OCTETS = "application/octet-stream"

QueryText = Annotated[str, Query(min_length=1, max_length=MAX_QUERY_CHARS)]


class SimilarToItems(BaseModel):
    indices: list[int] = Field(min_length=1, max_length=MAX_SIMILAR_ITEMS)


def get_embedder(request: Request, build: Annotated[MapBuild, Depends(get_build)]) -> QueryEmbedder:
    embedder: QueryEmbedder = request.app.state.embedder
    if embedder.key != build.manifest.embedding_key:
        # A vector from another model, prefix or dimension is never compared to the build's.
        raise HTTPException(
            status_code=503,
            detail="The embedding model of this server is not the one that built the map.",
        )
    return embedder


@router.get("/search/text")
def search_text(q: QueryText, build: Annotated[MapBuild, Depends(get_build)]) -> Response:
    """uint8 per point: 1 where the text of the item holds every word."""
    return Response(text_hits(build, q).tobytes(), media_type=_OCTETS)


@router.get("/similarity")
def similarity(
    q: QueryText,
    build: Annotated[MapBuild, Depends(get_build)],
    embedder: Annotated[QueryEmbedder, Depends(get_embedder)],
) -> Response:
    """float32 per point: cosine between the item and the text."""
    try:
        vector = embedder.embed(q)
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=503, detail="The embedding model did not answer."
        ) from error
    return Response(scores_to_vector(build, vector).tobytes(), media_type=_OCTETS)


@router.post("/similarity/items")
def similarity_to_items(
    body: SimilarToItems, build: Annotated[MapBuild, Depends(get_build)]
) -> Response:
    """float32 per point: cosine between the item and the mean direction of the given points."""
    n = build.manifest.n
    if any(i < 0 or i >= n for i in body.indices):
        raise HTTPException(status_code=422, detail="indices: a point index is outside the map.")
    return Response(scores_to_items(build, body.indices).tobytes(), media_type=_OCTETS)

import numpy as np
import pytest
from conftest import ARTICLE_TEXT, ARTICLE_TITLE, ARTICLE_URL, BROKEN_URL, EMPTY_URL, Api

from backend.analyze.place import neighbour_weights
from backend.analyze.rate_limit import RateLimiter
from backend.analyze.schema import EMBED_BUDGET_CHARS, MAX_TEXT_CHARS, NEIGHBOURS

LONG_ENOUGH = "A text long enough to be placed on the map."


def test_text_is_placed_among_its_nearest_points(api: Api) -> None:
    response = api.client.post("/api/analyze", json={"text": f"  {LONG_ENOUGH}  ", "url": None})

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "placed"
    assert body["reason"] is None
    assert body["source"] == {"kind": "text", "url": None, "title": None, "read_at": None}
    assert body["text"] == LONG_ENOUGH
    assert body["characters"] == len(LONG_ENOUGH)
    assert body["verdicts"] == []
    assert api.embedder.asked == [LONG_ENOUGH]

    # The fake embedder answers the vector of point 3: it is its own nearest neighbour.
    neighbours = body["neighbours"]
    assert len(neighbours) == NEIGHBOURS
    assert neighbours[0]["index"] == 3
    assert neighbours[0]["score"] == pytest.approx(1.0, abs=1e-3)
    scores = [n["score"] for n in neighbours]
    assert scores == sorted(scores, reverse=True)

    # The position is the weighted mean of the neighbours' places: pos3[i] = (i, 2i, 3i).
    weights = neighbour_weights(np.asarray(scores, dtype=np.float32))
    along = float(weights @ np.asarray([n["index"] for n in neighbours], dtype=np.float32))
    assert body["position3"] == pytest.approx([along, 2 * along, 3 * along], rel=1e-4)
    assert body["position2"] == pytest.approx([along, -along], rel=1e-4)


def test_short_text_abstains_without_embedding(api: Api) -> None:
    response = api.client.post("/api/analyze", json={"text": "   too short   "})

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "not enough evidence"
    assert "20 characters" in body["reason"]
    assert body["text"] == "too short"
    assert body["position3"] is None and body["position2"] is None
    assert body["neighbours"] == []
    assert api.embedder.asked == []


def test_link_is_read_and_placed_by_its_title_and_beginning(api: Api) -> None:
    response = api.client.post("/api/analyze", json={"url": ARTICLE_URL})

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "placed"
    assert body["source"] == {
        "kind": "url",
        "url": ARTICLE_URL,
        "title": ARTICLE_TITLE,
        "read_at": "2026-11-14T09:30:00Z",
    }
    assert body["characters"] == len(ARTICLE_TEXT)
    assert body["text"].startswith(f"{ARTICLE_TITLE}\n{ARTICLE_TEXT[:40]}")
    assert len(body["text"]) <= EMBED_BUDGET_CHARS
    assert api.embedder.asked == [body["text"]]
    assert api.reader.asked == [ARTICLE_URL]


def test_unreadable_page_abstains_with_the_reason(api: Api) -> None:
    response = api.client.post("/api/analyze", json={"url": BROKEN_URL})

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "not enough evidence"
    assert body["reason"] == "The URL's hostname does not exist."
    assert body["source"] == {"kind": "url", "url": BROKEN_URL, "title": None, "read_at": None}
    assert body["text"] == "" and body["characters"] == 0
    assert api.embedder.asked == []


def test_page_with_too_little_text_abstains(api: Api) -> None:
    body = api.client.post("/api/analyze", json={"url": EMPTY_URL}).json()

    assert body["outcome"] == "not enough evidence"
    assert body["reason"] == "The page holds too little text to be placed."
    assert body["source"]["title"] == "Empty"
    assert api.embedder.asked == []


def test_link_without_a_reader_is_refused_and_text_still_works(api: Api) -> None:
    api.app.state.page_reader = None

    refused = api.client.post("/api/analyze", json={"url": ARTICLE_URL})
    assert refused.status_code == 503
    assert "paste the text" in refused.json()["detail"]
    assert api.client.post("/api/analyze", json={"text": LONG_ENOUGH}).status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"text": None, "url": None},
        {"text": LONG_ENOUGH, "url": ARTICLE_URL},
        {"url": "ftp://news.example/file"},
        {"url": "not an address"},
        {"text": "x" * (MAX_TEXT_CHARS + 1)},
    ],
)
def test_invalid_requests_are_refused_with_422(api: Api, payload: dict[str, str | None]) -> None:
    response = api.client.post("/api/analyze", json=payload)

    assert response.status_code == 422
    assert api.embedder.asked == [] and api.reader.asked == []


def test_another_embedding_key_is_refused(api: Api) -> None:
    api.embedder.key = "another-model@1|prefix=''|dims=4"

    response = api.client.post("/api/analyze", json={"text": LONG_ENOUGH})

    assert response.status_code == 503
    assert api.embedder.asked == []


def test_requests_beyond_the_limit_get_429_per_client(api: Api) -> None:
    api.app.state.analyze_limiter = RateLimiter(limit=2, window=60.0)
    first = {"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}
    other = {"X-Forwarded-For": "203.0.113.8"}

    codes = [
        api.client.post("/api/analyze", json={"text": LONG_ENOUGH}, headers=first).status_code
        for _ in range(3)
    ]

    assert codes == [200, 200, 429]
    assert (
        api.client.post("/api/analyze", json={"text": LONG_ENOUGH}, headers=other).status_code
        == 200
    )

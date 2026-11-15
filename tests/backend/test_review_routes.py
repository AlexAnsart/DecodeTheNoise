"""The review asked for now, on the demo build and on a workspace: what is read, what is kept,
what is counted and what is refused."""

from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from probe_fakes import FakeProbe, vector_with_logits, write_pack
from review_fakes import ScriptedChat, write_guides
from workspace_fakes import FakeModel, Platform, make_app, probes_in

from backend.accounts.limits import ALL_WORKSPACES, LIMITS, REVIEWS
from backend.analyze.rate_limit import RateLimiter
from backend.review.guides import load_guides
from backend.review.routes import LLM_DOWN, NO_LLM
from backend.services import stop_services

# Far above anything the points of the tiny build reach: no probe flags the demo.
CUT = 1000.0
FLAGGED = "Everybody share this now and tag three friends, they will come for you next!"
QUIET = "The bakery on the corner opens at seven on weekdays, as usual."
SCREEN = {
    "voice": "own",
    "findings": [],
    "techniques": [
        {"key": "fear_appeal", "explanation": "It warns of a harm.", "quote": "post number"},
        {"key": "whataboutism", "explanation": "Not there.", "quote": "what about them"},
    ],
    "asks": None,
    "target": "number",
}


def _platform(root: Path, chat: ScriptedChat | None) -> Platform:
    arrays = write_pack(
        root / "probes",
        [
            FakeProbe("call_amplify", possible_cut=CUT, probable_cut=CUT + 2.0),
            FakeProbe("net", state="review-only", review_cut=CUT),
        ],
    )
    model = FakeModel()
    # Raw outputs of the two probes: above the cuts of the first one, then under every cut.
    model.by_text[FLAGGED] = vector_with_logits(arrays, [CUT + 4.0, 0.0])
    model.by_text[QUIET] = vector_with_logits(arrays, [0.0, 0.0])
    made = make_app(root, model, chat, probes_in(root / "probes"))
    made.services.reviewer.guides = load_guides(write_guides(root / "guides"))
    return made


@pytest.fixture
def chat() -> ScriptedChat:
    return ScriptedChat(item=dict(SCREEN))


@pytest.fixture
def platform(tmp_path: Path, chat: ScriptedChat) -> Iterator[Platform]:
    made = _platform(tmp_path, chat)
    with made.client:
        yield made
    stop_services(made.services)
    made.build.items.close()


def test_a_demo_point_is_reviewed_once_and_kept(platform: Platform, chat: ScriptedChat) -> None:
    index = 3

    first = platform.client.post(f"/api/map/review/{index}")
    again = platform.client.post(f"/api/map/review/{index}")

    assert first.status_code == 200, first.text
    review = first.json()
    assert review["status"] == "done" and review["measured"] is False
    assert (review["model"], review["prompt_version"]) == ("test-llm", "review-v2")
    # The technique whose span is in the item is kept; the other is removed.
    assert [(t["key"], t["name"], t["quote"]) for t in review["techniques"]] == [
        ("fear_appeal", "Fear appeal", "post number")
    ]
    assert (review["voice"], review["asks"], review["target"]) == ("own", None, "number")
    # The same question is not paid twice, and it was counted once.
    assert again.json() == review and chat.reviews() == 1
    assert platform.services.accounts.used_today(ALL_WORKSPACES, REVIEWS) == 1
    system, user, _ = chat.asked[0]
    assert system.startswith("You review one item") and "# Guide: rhetoric" in system
    assert f"<<<\npost number {index}\n>>>" in user
    assert "Nearest items by meaning:\n- post number" in user
    assert "Other items of the same actor:\n- post number" in user


def test_the_demo_review_is_limited_and_needs_an_llm(tmp_path: Path, chat: ScriptedChat) -> None:
    made = _platform(tmp_path, chat)
    made.app.state.review_limiter = RateLimiter(limit=1, window=60.0)
    first, second = 3, 4
    with made.client as client:
        assert client.post(f"/api/map/review/{first}").status_code == 200
        # Asked again, it comes from the cache: it does not count against the limit.
        assert client.post(f"/api/map/review/{first}").status_code == 200
        refused = client.post(f"/api/map/review/{second}")
        assert refused.status_code == 429 and "at most 1 a minute" in refused.json()["detail"]
        assert client.post("/api/map/review/12").status_code == 404
        made.services.reviewer.chat = None
        missing = client.post(f"/api/map/review/{second}")
        assert missing.status_code == 503 and missing.json()["detail"] == NO_LLM
    stop_services(made.services)
    made.build.items.close()


def test_a_workspace_review_is_kept_on_the_item(platform: Platform, chat: ScriptedChat) -> None:
    headers = platform.new_workspace()
    client = platform.client
    client.patch("/api/v1/workspace/settings", json={"review_mode": "off"}, headers=headers)
    for item_id, text in (("p1", FLAGGED), ("p2", QUIET)):
        sent = client.post("/api/v1/items", json={"id": item_id, "text": text}, headers=headers)
        assert sent.status_code == 200, sent.text
    platform.settle()
    assert chat.reviews() == 0
    before = client.get("/api/v1/workspace", headers=headers).json()
    chat.item = {
        "voice": "own",
        "findings": [
            {
                "probe": "call_amplify",
                "reading": "supported",
                "explanation": "It asks to share.",
                "quote": "share this now",
            }
        ],
        "techniques": [
            {"key": "fear_appeal", "explanation": "A harm to come.", "quote": "come for you next"}
        ],
        "asks": "share this now and tag three friends",
        "target": None,
    }

    review = client.post("/api/v1/map/review/0", headers=headers).json()

    assert review["status"] == "done"
    assert [(f["probe"], f["label"], f["reading"]) for f in review["findings"]] == [
        ("call_amplify", "Call amplify", "supported")
    ]
    assert [t["key"] for t in review["techniques"]] == ["fear_appeal"]
    assert review["asks"] == "share this now and tag three friends"
    # Kept on the item, counted for the workspace, and the map moved for whoever watches it.
    card = client.get("/api/v1/map/reading/0", headers=headers).json()
    assert card["review"] == review
    after = client.get("/api/v1/workspace", headers=headers).json()
    assert after["usage"]["reviews_today"] == before["usage"]["reviews_today"] + 1
    assert after["version"] > before["version"]
    # The other item has no flag: it is screened, with the daily limit of the workspace.
    platform.services.accounts.use(after["id"], REVIEWS, LIMITS.reviews_per_day)
    refused = client.post("/api/v1/map/review/1", headers=headers)
    assert refused.status_code == 429 and "daily review limit" in refused.json()["detail"]
    assert client.post("/api/v1/map/review/2", headers=headers).status_code == 404


def test_a_flagged_item_is_reviewed_in_the_background_with_the_same_method(
    platform: Platform, chat: ScriptedChat
) -> None:
    headers = platform.new_workspace()
    chat.item = {
        "findings": [
            {"probe": "call_amplify", "reading": "supported", "explanation": "x", "quote": "tag"}
        ],
        "techniques": [{"key": "fear_appeal", "explanation": "x", "quote": "come for you next"}],
    }

    platform.client.post("/api/v1/items", json={"id": "p1", "text": FLAGGED}, headers=headers)
    platform.settle()
    stored = platform.client.get("/api/v1/items/p1", headers=headers).json()["item"]["review"]
    asked = platform.client.post("/api/v1/map/review/0", headers=headers).json()

    assert stored["status"] == "done" and stored["prompt_version"] == "review-v2"
    assert [t["key"] for t in stored["techniques"]] == ["fear_appeal"]
    # Asked for by hand afterwards, the same question comes from the cache.
    assert asked == stored and chat.reviews() == 1


def test_a_failed_llm_call_answers_a_failed_review(platform: Platform) -> None:
    class Down:
        def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
            raise httpx.ConnectError("no route to the router")

    platform.services.reviewer.chat = Down()

    review = platform.client.post("/api/map/review/3").json()

    assert (review["status"], review["reason"]) == ("failed", LLM_DOWN)


def test_a_selection_is_measured_then_read(platform: Platform, chat: ScriptedChat) -> None:
    chat.selection = {
        "statement": "The posts  are numbered.",
        "techniques": [
            {
                "key": "fear_appeal",
                "explanation": "They count.",
                "examples": [{"post": 1, "quote": "post number"}, {"post": 2, "quote": "number"}],
            },
            {"key": "whataboutism", "explanation": "x", "examples": [{"post": 1, "quote": "post"}]},
        ],
        "asks": {"post": 2, "quote": "post"},
        "targets": [{"post": 1, "quote": "number"}, {"post": 7, "quote": "post"}],
    }
    body = {"indices": [0, 1, 2, 3, 4, 5, 5]}

    answer = platform.client.post("/api/review/selection", json=body)
    again = platform.client.post("/api/review/selection", json=body)

    assert answer.status_code == 200, answer.text
    review = answer.json()
    assert (review["status"], review["posts"], review["actors"]) == ("done", 6, 1)
    assert (review["model"], review["prompt_version"]) == ("test-llm", "selection-v1")
    assert review["measured"] is False
    # Every item of the tiny build has the same actor: two posts of it are read, no more.
    assert len(review["read"]) == 2 and set(review["read"]) <= {0, 1, 2, 3, 4, 5}
    assert review["statement"] == "The posts are numbered."
    assert [t["key"] for t in review["techniques"]] == ["fear_appeal"]
    examples = review["techniques"][0]["examples"]
    assert [example["index"] for example in examples] == review["read"]
    assert (review["asks"], review["targets"]) == ("post", ["number"])
    # Measured by the probes alone: the shown probe, never the review-only one.
    assert [(rate["key"], rate["flagged"]) for rate in review["rates"]] == [("call_amplify", 0)]
    assert again.json() == review and chat.reviews() == 1
    numbered = chat.asked[0][1]
    assert "Posts of the selection (2 read):\n[1] post number" in numbered

    outside = platform.client.post("/api/review/selection", json={"indices": [0, 12]})
    assert outside.status_code == 422
    assert platform.client.post("/api/review/selection", json={"indices": []}).status_code == 422


def test_without_an_llm_a_selection_keeps_its_measured_part(platform: Platform) -> None:
    platform.services.reviewer.chat = None

    review = platform.client.post("/api/review/selection", json={"indices": [0, 1, 2]}).json()

    assert (review["status"], review["reason"]) == ("skipped", NO_LLM)
    assert (review["posts"], review["actors"]) == (3, 1)
    assert [rate["key"] for rate in review["rates"]] == ["call_amplify"]
    assert review["read"] == [] and review["statement"] is None

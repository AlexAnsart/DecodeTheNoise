"""Probes on a workspace: scores in the answer and on the map, the review of flagged items."""

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from probe_fakes import FakeProbe, vector_with_logits, write_pack
from workspace_fakes import FakeChat, FakeModel, Platform, make_app, probes_in

from backend.services import stop_services

FLAGGED = "Everybody share this now and tag three friends, do it today!"
QUIET = "The bakery on the corner opens at seven on weekdays, as usual."


@pytest.fixture
def platform(tmp_path: Path) -> Iterator[Platform]:
    arrays = write_pack(
        tmp_path / "probes",
        [
            FakeProbe("call_amplify", possible_cut=0.0, probable_cut=2.0),
            FakeProbe("quiet_only", possible_cut=0.0, state="review-only"),
        ],
    )
    model = FakeModel()
    # Raw outputs of the two probes: far above the probable cut, then far under every cut.
    model.by_text[FLAGGED] = vector_with_logits(arrays, [4.0, -6.0])
    model.by_text[QUIET] = vector_with_logits(arrays, [-6.0, -6.0])
    made = make_app(tmp_path, model, FakeChat(), probes_in(tmp_path / "probes"))
    with made.client:
        yield made
    stop_services(made.services)
    made.build.items.close()


def send(platform: Platform, headers: dict[str, str], item_id: str, text: str) -> dict:
    response = platform.client.post(
        "/api/v1/items", json={"id": item_id, "text": text}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_a_flagged_post_carries_its_reading_and_is_reviewed(platform: Platform) -> None:
    headers = platform.new_workspace()

    flagged = send(platform, headers, "p1", FLAGGED)
    quiet = send(platform, headers, "p2", QUIET)

    reading = flagged["item"]["probes"]
    assert [(r["key"], r["level"]) for r in reading] == [("call_amplify", "probable")]
    assert reading[0]["score"] > 0.8 and reading[0]["reliability"]["precision"] > 0
    # The review-only probe is never shown, flagged or not.
    assert set(flagged["item"]["scores"]) == {"call_amplify"}
    # The review runs in the background: it is waiting, or already done by the stand-in.
    assert flagged["item"]["review"]["status"] in ("queued", "done")
    assert quiet["item"]["probes"] == [] and quiet["item"]["review"]["status"] == "none"

    platform.settle()
    after = platform.client.get("/api/v1/items/p1", headers=headers).json()
    review = after["item"]["review"]
    assert review["status"] == "done" and review["measured"] is False
    found = [(f["probe"], f["reading"]) for f in review["findings"]]
    assert found == [("call_amplify", "supported")]
    info = platform.client.get("/api/v1/workspace", headers=headers).json()
    assert info["usage"]["reviews_today"] == 1
    assert [probe["key"] for probe in info["probes"]] == ["call_amplify"]


def test_the_map_gives_scores_and_readings_for_both_sources(platform: Platform) -> None:
    headers = platform.new_workspace()
    send(platform, headers, "p1", FLAGGED)
    send(platform, headers, "p2", QUIET)
    platform.settle()
    client = platform.client

    scores = np.frombuffer(
        client.get("/api/v1/map/scores/call_amplify", headers=headers).content, dtype=np.float32
    )
    card = client.get("/api/v1/map/reading/0", headers=headers).json()
    demo_scores = client.get("/api/map/scores/call_amplify").content
    demo_card = client.get("/api/map/reading/3").json()

    assert scores[0] > 0.8 > 0.5 > scores[1]
    assert card["probes"][0]["level"] == "probable" and card["review"]["status"] == "done"
    assert len(demo_scores) == 12 * 4
    assert demo_card["review"] is None and set(demo_card["scores"]) == {"call_amplify"}
    assert [p["key"] for p in client.get("/api/map").json()["probes"]] == ["call_amplify"]
    assert client.get("/api/map/scores/quiet_only").status_code == 404
    assert client.get("/api/map/reading/12").status_code == 404
    assert [p["key"] for p in client.get("/api/metrics").json()["probes"]] == ["call_amplify"]


def test_review_off_sends_nothing_to_the_llm(platform: Platform) -> None:
    headers = platform.new_workspace()
    platform.client.patch(
        "/api/v1/workspace/settings", json={"review_mode": "off"}, headers=headers
    )

    body = send(platform, headers, "p1", FLAGGED)
    platform.settle()

    assert body["item"]["probes"][0]["level"] == "probable"
    assert body["item"]["review"]["status"] == "none"
    assert platform.chat.asked == []

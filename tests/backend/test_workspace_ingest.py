"""Following the embedding of a batch: what waits, how long it should take, what went wrong."""

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from workspace_fakes import FakeChat, FakeModel, Platform, make_app

from backend.ingest import background
from backend.ingest.embedder import CHUNK
from backend.probes.pack import EMPTY
from backend.services import stop_services

LONG = "A post long enough to be placed on the map, number {}."


@pytest.fixture
def platform(tmp_path: Path) -> Iterator[Platform]:
    made = make_app(tmp_path, FakeModel(), FakeChat(), EMPTY)
    with made.client:
        yield made
    stop_services(made.services)
    made.build.items.close()


def batch(platform: Platform, headers: dict[str, str], count: int, start: int = 0) -> dict:
    items = [{"id": f"p{i}", "text": LONG.format(i)} for i in range(start, start + count)]
    response = platform.client.post("/api/v1/items/batch", json={"items": items}, headers=headers)
    assert response.status_code == 202, response.text
    return response.json()


def test_a_batch_counts_down_and_says_when_it_is_done(platform: Platform) -> None:
    headers = platform.new_workspace()
    workspace = platform.services.workspaces.loaded()[0]

    # 0 to 12 waiting opens a batch; 5 more join it; placing them all closes it.
    with workspace.lock:
        assert workspace.set_pending(12) == 0 and workspace.batch_total == 12
        assert workspace.set_pending(7) == 0 and workspace.batch_total == 12
        assert workspace.set_pending(12) == 0 and workspace.batch_total == 17
        assert workspace.set_pending(0) == 17 and workspace.batch_total == 0

    batch(platform, headers, 12)
    platform.settle()
    info = platform.client.get("/api/v1/workspace", headers=headers).json()
    assert (info["points"], info["pending"], info["ingest"]["batch"]) == (12, 0, 0)
    assert info["ingest"]["rate"] > 0 and info["ingest"]["eta_seconds"] is None


def test_the_time_left_counts_the_workspaces_that_take_turns(platform: Platform) -> None:
    platform.new_workspace()
    platform.new_workspace()
    services = platform.services
    mine, other = services.workspaces.loaded()
    services.embedder.rate = 8.0

    with mine.lock, other.lock:
        mine.set_pending(40)
        other.set_pending(1_000)
        busy = services.ingest_state(mine, [mine, other])
        other.set_pending(16)
        light = services.ingest_state(mine, [mine, other])
        mine.set_pending(0)
        idle = services.ingest_state(mine, [mine, other])
        other.set_pending(0)

    # While its 40 posts are embedded, the other workspace gets as many turns: 40 of its own.
    turns = -(-40 // CHUNK) * CHUNK
    assert (busy.batch, busy.ahead, busy.eta_seconds) == (40, turns, (40 + turns) // 8)
    assert (light.ahead, light.eta_seconds) == (16, 7)
    assert (idle.batch, idle.ahead, idle.eta_seconds) == (0, 0, None)


def test_a_silent_model_is_said_and_tried_again(
    platform: Platform, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The retry is set an hour away: the test plays it by hand.
    monkeypatch.setattr(background, "RETRY_SECONDS", (3_600,))
    headers = platform.new_workspace()
    platform.model.failing = 1_000

    accepted = batch(platform, headers, 10)
    platform.settle(delayed=False)
    stuck = platform.client.get("/api/v1/workspace", headers=headers).json()

    assert accepted["accepted"] == 10
    assert (stuck["points"], stuck["pending"], stuck["ingest"]["batch"]) == (0, 10, 10)
    assert "did not answer" in stuck["ingest"]["error"] and "3600 s" in stuck["ingest"]["error"]
    one = platform.client.post(
        "/api/v1/items", json={"id": "single", "text": LONG.format(99)}, headers=headers
    )
    assert one.status_code == 503 and "stored" in one.json()["detail"]

    platform.model.failing = 0
    assert platform.services.jobs is not None
    platform.services.jobs.ingest.submit(stuck["id"])
    platform.settle(delayed=False)
    after = platform.client.get("/api/v1/workspace", headers=headers).json()

    assert (after["points"], after["pending"]) == (11, 0)
    assert after["ingest"]["error"] is None


def test_every_group_embedded_leaves_a_line_in_the_log(
    platform: Platform, caplog: pytest.LogCaptureFixture
) -> None:
    headers = platform.new_workspace()
    caplog.set_level(logging.INFO, logger="backend.ingest")

    batch(platform, headers, CHUNK + 2)
    platform.settle()
    batch(platform, headers, 2)
    platform.settle()

    lines = [record.getMessage() for record in caplog.records]
    received = [line for line in lines if "received" in line]
    placed = [line for line in lines if "posts placed," in line]
    assert f"batch of {CHUNK + 2} received: {CHUNK + 2} new" in received[0]
    assert "2 unchanged" in received[1]
    assert f"{CHUNK} posts placed, 0 from the cache, {CHUNK} embedded" in placed[0]
    assert "2 posts placed" in placed[1] and "0 waiting" in placed[1]
    assert any(f"batch of {CHUNK + 2} posts placed in" in line for line in lines)


def test_a_batch_holds_a_thousand_posts_at_most(platform: Platform) -> None:
    headers = platform.new_workspace()
    items = [{"id": f"p{i}", "text": "short"} for i in range(1_001)]

    refused = platform.client.post("/api/v1/items/batch", json={"items": items}, headers=headers)
    taken = platform.client.post(
        "/api/v1/items/batch", json={"items": items[:1_000]}, headers=headers
    )

    assert refused.status_code == 422
    assert taken.status_code == 202 and taken.json()["accepted"] == 1_000

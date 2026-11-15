"""The workspace API end to end: a key, posts sent one by one and in batches, the map they build."""

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from workspace_fakes import FakeChat, FakeModel, Platform, make_app, unit

from backend.map.schema import NO_NEIGHBOUR
from backend.probes.pack import EMPTY
from backend.services import stop_services
from backend.workspace import state as workspace_state
from backend.workspace.schema import Limits
from pipelines.pack.buffers import unpack_buffer

LONG = "A post long enough to be placed on the map, number {}."


@pytest.fixture
def platform(tmp_path: Path) -> Iterator[Platform]:
    made = make_app(tmp_path, FakeModel(), FakeChat(), EMPTY)
    with made.client:
        yield made
    stop_services(made.services)
    made.build.items.close()


def post(platform: Platform, headers: dict[str, str], **item: object) -> dict:
    response = platform.client.post("/api/v1/items", json=item, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_a_workspace_needs_its_key(platform: Platform) -> None:
    assert platform.client.get("/api/v1/workspace").status_code == 401
    wrong = {"Authorization": "Bearer nm_not-a-key"}
    assert platform.client.get("/api/v1/workspace", headers=wrong).status_code == 401

    headers = platform.new_workspace()
    info = platform.client.get("/api/v1/workspace", headers=headers).json()
    assert (info["items"], info["points"], info["pending"]) == (0, 0, 0)
    assert info["limits"]["items"] == 1_000 and info["limits"]["batch_items"] == 1_000
    assert info["ingest"] == {
        "batch": 0,
        "ahead": 0,
        "rate": None,
        "eta_seconds": None,
        "error": None,
    }
    assert platform.client.get("/api/config").json()["limits"] == info["limits"]
    assert info["refresh"]["next_at"] == workspace_state.FIRST_REFRESH


def test_one_post_is_placed_and_answered_at_once(platform: Platform) -> None:
    headers = platform.new_workspace()

    body = post(
        platform,
        headers,
        id="p1",
        text=LONG.format(1),
        actor_id="ann",
        created_at="2026-11-14T09:30:00+02:00",
        kind="original",
        meta={"campaign": "launch"},
    )

    assert (body["id"], body["stored"], body["outcome"], body["index"]) == ("p1", True, "placed", 0)
    assert body["item"] == {
        "lang": None,
        "probes": [],
        "scores": {},
        "review": body["item"]["review"],
    }
    assert body["item"]["review"]["status"] == "none"
    assert body["context"]["neighbours"] == []
    assert body["context"]["zone"] is None
    assert body["context"]["actor"]["items"] == 1
    assert body["workspace"]["points"] == 1
    assert platform.model.calls == [[LONG.format(1)]]

    card = platform.client.post("/api/v1/map/items", json={"indices": [0]}, headers=headers).json()
    assert card["items"][0]["item_id"] == "p1"
    assert card["items"][0]["created_at"] == 1794641400000
    assert card["items"][0]["attrs"] == {"kind": "original", "campaign": "launch"}


def test_short_text_is_stored_but_abstains(platform: Platform) -> None:
    headers = platform.new_workspace()

    body = post(platform, headers, id="p1", text="too short https://example.org/a-long-link")

    assert body["outcome"] == "not enough evidence"
    assert "too short" in body["reason"]
    assert (body["index"], body["item"], body["context"]) == (None, None, None)
    assert (body["workspace"]["items"], body["workspace"]["points"]) == (1, 0)
    assert platform.model.calls == []


def test_unknown_fields_and_naive_dates_are_refused(platform: Platform) -> None:
    headers = platform.new_workspace()
    client = platform.client

    extra = client.post(
        "/api/v1/items", json={"id": "p", "text": "x", "author": "a"}, headers=headers
    )
    naive = client.post(
        "/api/v1/items",
        json={"id": "p", "text": LONG.format(1), "created_at": "2026-11-14T09:30:00"},
        headers=headers,
    )

    assert extra.status_code == 422 and naive.status_code == 422


def test_the_same_id_updates_and_keeps_its_point(platform: Platform) -> None:
    headers = platform.new_workspace()
    post(platform, headers, id="p1", text=LONG.format(1))
    post(platform, headers, id="p2", text=LONG.format(2))

    same = post(platform, headers, id="p1", text=LONG.format(1))
    changed = post(platform, headers, id="p1", text=LONG.format(3))

    assert same["index"] == 0 and changed["index"] == 0
    assert changed["workspace"]["items"] == 2 and changed["workspace"]["points"] == 2
    # The unchanged post costs no embedding; the changed one is embedded again.
    assert platform.model.calls == [[LONG.format(1)], [LONG.format(2)], [LONG.format(3)]]
    found = platform.client.get("/api/v1/search/text?q=number 3", headers=headers).content
    assert list(found) == [1, 0]


def test_analysing_without_storing_leaves_the_workspace_as_it_was(platform: Platform) -> None:
    headers = platform.new_workspace()
    post(platform, headers, id="p1", text=LONG.format(1))

    response = platform.client.post(
        "/api/v1/items?store=false", json={"id": "probe", "text": LONG.format(1)}, headers=headers
    )

    body = response.json()
    assert (body["stored"], body["outcome"], body["index"]) == (False, "placed", None)
    assert body["context"]["neighbours"][0]["id"] == "p1"
    assert body["context"]["neighbours"][0]["similarity"] == pytest.approx(1.0, abs=1e-3)
    assert body["workspace"]["items"] == 1
    assert platform.client.get("/api/v1/items/probe", headers=headers).status_code == 404


def test_context_counts_who_says_the_same_thing(platform: Platform) -> None:
    headers = platform.new_workspace()
    texts = {
        "copy": "Sign the petition now and share it with everyone you know, friends!",
        "copy2": "Sign the petition now and share it with everyone you know, people!",
        "reworded": "Everybody should put their name on this appeal and pass it around.",
        "other": "The weather was fine over the lake this morning, with a light wind.",
    }
    platform.model.by_text = {
        texts["copy"]: unit([1, 0, 0, 0]),
        texts["copy2"]: unit([1, 0.05, 0, 0]),
        texts["reworded"]: unit([1, 0, 0.3, 0]),
        texts["other"]: unit([0, 0, 0, 1]),
    }
    post(platform, headers, id="a", text=texts["copy2"], actor_id="bob")
    post(platform, headers, id="b", text=texts["reworded"], actor_id="cat")
    post(platform, headers, id="c", text=texts["other"], actor_id="dan")

    context = post(platform, headers, id="d", text=texts["copy"], actor_id="ann")["context"]

    nearest = context["neighbours"]
    assert [n["id"] for n in nearest] == ["a", "b", "c"]
    assert nearest[0]["word_overlap"] > 0.7 > 0.2 > nearest[1]["word_overlap"]
    assert nearest[0]["similarity"] > 0.99 and nearest[1]["similarity"] > 0.95
    # Two other items sit at or above 0.9, written by two other actors.
    assert context["same_statement"]["items"] == 2
    assert context["same_statement"]["actors"] == 2
    assert context["actor"]["similar_actors"] == []
    assert "not enough evidence" in context["actor"]["reason"]


def test_a_batch_is_embedded_in_the_background(platform: Platform) -> None:
    headers = platform.new_workspace()
    items = [
        {"id": f"p{i}", "text": LONG.format(i), "actor_id": f"actor{i % 3}"} for i in range(12)
    ]
    items.append({"id": "bad", "text": LONG.format(99), "kind": "tweet"})
    items.append({"text": "no id at all, but long enough to be a post"})

    response = platform.client.post("/api/v1/items/batch", json={"items": items}, headers=headers)

    assert response.status_code == 202
    body = response.json()
    assert (body["accepted"], body["updated"], body["unchanged"]) == (12, 0, 0)
    assert [r["id"] for r in body["rejected"]] == ["bad", None]
    assert "kind" in body["rejected"][0]["reason"]

    platform.settle()
    info = platform.client.get("/api/v1/workspace", headers=headers).json()
    assert (info["items"], info["points"], info["pending"], info["actors"]) == (12, 12, 0, 3)
    one = platform.client.get("/api/v1/items/p7", headers=headers).json()
    assert one["outcome"] == "placed" and len(one["context"]["neighbours"]) == 10


def test_the_map_routes_serve_the_workspace(platform: Platform) -> None:
    headers = platform.new_workspace()
    for i in range(5):
        post(platform, headers, id=f"p{i}", text=LONG.format(i), actor_id="ann", source="feed")

    manifest = platform.client.get("/api/v1/map", headers=headers).json()
    blob = platform.client.get("/api/v1/map/buffers", headers=headers).content

    assert manifest["live"] is True and manifest["n"] == 5 and manifest["k"] == 10
    assert {c["key"] for c in manifest["columns"]} == {"zone", "actor", "source"}
    specs = manifest["buffers"]
    assert specs["pos3"]["length"] == 15 and specs["neighbours"]["length"] == 50
    from backend.map.schema import BufferSpec

    neighbours = unpack_buffer(blob, BufferSpec(**specs["neighbours"])).reshape(5, 10)
    assert (neighbours[:, :4] != NO_NEIGHBOUR).all() and (neighbours[:, 4:] == NO_NEIGHBOUR).all()
    # The demo build is untouched, and read without a key.
    assert platform.client.get("/api/map").json()["n"] == 12
    hits = platform.client.get("/api/v1/search/text?q=number 4", headers=headers).content
    assert list(hits) == [0, 0, 0, 0, 1]
    likeness = platform.client.post(
        "/api/v1/similarity/items", json={"indices": [2]}, headers=headers
    ).content
    assert np.frombuffer(likeness, dtype=np.float32)[2] == pytest.approx(1.0, abs=1e-3)


def test_a_refresh_lays_the_points_out_and_names_the_zones(platform: Platform) -> None:
    headers = platform.new_workspace()
    items = [{"id": f"p{i}", "text": LONG.format(i)} for i in range(25)]
    platform.client.post("/api/v1/items/batch", json={"items": items}, headers=headers)

    platform.settle()

    info = platform.client.get("/api/v1/workspace", headers=headers).json()
    assert info["refresh"]["epoch"] == 1 and info["refresh"]["running"] is False
    assert info["refresh"]["next_at"] == 100
    assert info["zones"] == 3
    manifest = platform.client.get("/api/v1/map", headers=headers).json()
    assert [zone["named"] for zone in manifest["zones"]] == [True, True, True]
    assert all(zone["name"].startswith("Zone number") for zone in manifest["zones"])
    assert sum(zone["size"] for zone in manifest["zones"]) == 25
    placed = post(platform, headers, id="late", text=LONG.format(100))
    assert placed["context"]["zone"]["named"] is True
    assert info["usage"]["names_today"] == 3


def test_a_full_workspace_refuses_new_items(
    platform: Platform, monkeypatch: pytest.MonkeyPatch
) -> None:
    small = Limits(
        items=2, batch_items=10, requests_per_minute=100, reviews_per_day=5, text_chars=100
    )
    monkeypatch.setattr(workspace_state, "LIMITS", small)
    headers = platform.new_workspace()
    post(platform, headers, id="p1", text=LONG.format(1))
    post(platform, headers, id="p2", text=LONG.format(2))

    refused = platform.client.post(
        "/api/v1/items", json={"id": "p3", "text": LONG.format(3)}, headers=headers
    )
    again = platform.client.post(
        "/api/v1/items", json={"id": "p1", "text": LONG.format(1)}, headers=headers
    )

    assert refused.status_code == 409 and "full" in refused.json()["detail"]
    assert again.status_code == 200


def test_settings_emptying_and_a_new_key(platform: Platform) -> None:
    headers = platform.new_workspace()
    post(platform, headers, id="p1", text=LONG.format(1))
    client = platform.client

    patched = client.patch(
        "/api/v1/workspace/settings",
        json={"review_mode": "off", "refresh_every": 50},
        headers=headers,
    ).json()
    assert patched["settings"] == {
        "review_mode": "off",
        "review_min_score": 0.8,
        "refresh_every": 50,
    }
    assert (
        client.patch(
            "/api/v1/workspace/settings", json={"refresh_every": 5}, headers=headers
        ).status_code
        == 422
    )

    emptied = client.delete("/api/v1/workspace/items", headers=headers).json()
    assert (emptied["items"], emptied["points"]) == (0, 0)
    assert client.get("/api/v1/map", headers=headers).json()["n"] == 0

    rotated = client.post("/api/v1/workspace/key", headers=headers).json()["api_key"]
    assert client.get("/api/v1/workspace", headers=headers).status_code == 401
    kept = client.get("/api/v1/workspace", headers={"Authorization": f"Bearer {rotated}"}).json()
    assert kept["settings"]["refresh_every"] == 50


def test_a_workspace_is_read_back_from_its_files(tmp_path: Path) -> None:
    first = make_app(tmp_path, FakeModel(), None, EMPTY)
    with first.client:
        headers = first.new_workspace()
        for i in range(6):
            post(first, headers, id=f"p{i}", text=LONG.format(i), actor_id="ann")
        before = first.client.get("/api/v1/items/p3", headers=headers).json()
    stop_services(first.services)
    first.build.items.close()

    second = make_app(tmp_path, FakeModel(), None, EMPTY)
    with second.client:
        after = second.client.get("/api/v1/items/p3", headers=headers).json()
        info = second.client.get("/api/v1/workspace", headers=headers).json()
    stop_services(second.services)
    second.build.items.close()

    assert (info["items"], info["points"], info["actors"]) == (6, 6, 1)
    assert after["index"] == before["index"]
    assert [n["id"] for n in after["context"]["neighbours"]] == [
        n["id"] for n in before["context"]["neighbours"]
    ]
    assert after["context"]["position"] == pytest.approx(before["context"]["position"], abs=1e-2)
    # Nothing was embedded again: the vectors came from the file.
    assert second.model.calls == []


def test_the_sample_is_in_the_format_the_api_takes(platform: Platform) -> None:
    headers = platform.new_workspace()

    sample = platform.client.get("/api/sample?count=6").json()

    assert sample["source"] == "tiny" and len(sample["items"]) == 6
    sent = platform.client.post(
        "/api/v1/items/batch", json={"items": sample["items"]}, headers=headers
    )
    assert sent.json()["accepted"] == 6 and sent.json()["rejected"] == []


def test_the_embedding_is_returned_when_asked_for(platform: Platform) -> None:
    headers = platform.new_workspace()
    item = {"id": "p1", "text": LONG.format(1)}

    plain = platform.client.post("/api/v1/items", json=item, headers=headers).json()
    asked = platform.client.get("/api/v1/items/p1?vector=true", headers=headers).json()

    assert plain["vector"] is None
    assert len(asked["vector"]) == 4
    assert sum(value * value for value in asked["vector"]) == pytest.approx(1.0, abs=1e-3)


def test_buffers_are_those_of_the_manifest_that_was_read(platform: Platform) -> None:
    headers = platform.new_workspace()
    post(platform, headers, id="p1", text=LONG.format(1))
    client = platform.client
    manifest = client.get("/api/v1/map", headers=headers).json()

    post(platform, headers, id="p2", text=LONG.format(2))
    then = client.get(f"/api/v1/map/buffers?v={manifest['version']}", headers=headers)
    now = client.get("/api/v1/map/buffers", headers=headers)
    gone = client.get("/api/v1/map/buffers?v=1", headers=headers)

    # One point then, two now: each answer has the size its own manifest describes.
    assert manifest["n"] == 1 and manifest["buffers"]["pos3"]["length"] == 3
    assert len(now.content) > len(then.content)
    assert gone.status_code == 409


def test_the_demo_buffers_are_served_compressed_when_the_file_is_there(platform: Platform) -> None:
    import gzip

    raw = platform.build.buffers_path.read_bytes()
    plain = platform.client.get("/api/map/buffers", headers={"Accept-Encoding": "identity"})
    (platform.build.folder / "map.bin.gz").write_bytes(gzip.compress(raw))

    packed = platform.client.get("/api/map/buffers", headers={"Accept-Encoding": "gzip"})
    refused = platform.client.get("/api/map/buffers", headers={"Accept-Encoding": "identity"})

    assert "content-encoding" not in plain.headers and plain.content == raw
    # The client library decompresses: the bytes are the same, the header says how they came.
    assert packed.headers["content-encoding"] == "gzip" and packed.content == raw
    assert "content-encoding" not in refused.headers and refused.content == raw

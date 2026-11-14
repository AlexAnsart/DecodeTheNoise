"""The one-voice check on hand-made builds: actors with a voice, actors without, too few."""

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.map.schema import BUFFERS_FILE, ITEMS_FILE, MANIFEST_FILE, VECTORS_FILE, MapManifest
from backend.map.store import MapBuild, load_build
from backend.voices.calibration import Calibration, load_calibration
from backend.voices.reading import read_selection
from backend.voices.routes import calibration_at
from backend.voices.routes import router as voices_router
from backend.voices.score import measured_size, read_voices
from pipelines.ingest.ira import Item
from pipelines.pack.buffers import pack_buffers
from pipelines.pack.items import write_items

DIMS = 16
KEY = "test-model@0|prefix=''|dims=16"
METRICS = {
    "embedding_key": KEY,
    "sizes": [
        {
            "actors": actors,
            "posts_each": posts,
            "threshold": 3.0,
            "reference": {"independent": [9.0, 19.0], "one_brief": [-2.0, 3.0]},
            "real": {"groups": 73, "flagged": 0},
            "real_alike": {"groups": 73, "flagged": 3},
            "one_brief": {"groups": 53, "flagged": 50},
        }
        for actors, posts in ((6, 6), (4, 4))
    ],
}


def write_build(folder: Path, actors: int, posts: int, own_voice: float, kind: str) -> MapBuild:
    """`actors` actors of `posts` posts; `own_voice` is how far each actor sits from the rest."""
    rng = np.random.default_rng(3)
    who = np.repeat(np.arange(actors), posts)
    vectors = rng.normal(size=(actors, DIMS))[who] * own_voice + rng.normal(size=(len(who), DIMS))
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    blob, specs = pack_buffers({"ts": np.zeros(len(who), dtype=np.float64)})
    folder.mkdir(parents=True, exist_ok=True)
    (folder / BUFFERS_FILE).write_bytes(blob)
    manifest = MapManifest(
        build="voices", built_at="2026-11-14T00:00:00Z", n=len(who), k=0, embedding_key=KEY,
        dims=DIMS, time_min=None, time_max=None, columns=[], zones=[], buffers=specs,
    )  # fmt: skip
    (folder / MANIFEST_FILE).write_text(manifest.model_dump_json(), encoding="utf-8")
    vectors.astype(np.float16).tofile(folder / VECTORS_FILE)
    items = [
        Item(
            f"item{i}", f"actor{a}", f"post number {i}", None, "English", None, (), "Test", kind, 0
        )
        for i, a in enumerate(who)
    ]
    write_items(folder / ITEMS_FILE, items)
    build = load_build(folder)
    assert build is not None
    return build


@pytest.fixture
def calibration() -> Calibration:
    return Calibration.model_validate(METRICS)


def test_actors_with_a_voice_read_as_separate_voices(
    tmp_path: Path, calibration: Calibration
) -> None:
    build = write_build(tmp_path, actors=8, posts=6, own_voice=3.0, kind="original")
    answer = read_selection(build, calibration, list(range(48)))
    assert answer.outcome == "separate voices"
    assert answer.confidence is None and answer.pairs == []
    assert answer.score is not None and answer.score > 3.0
    assert answer.authorship is not None and answer.authorship.found > 0.8
    assert answer.read is not None and (answer.read.actors, answer.read.posts_each) == (6, 6)


def test_interchangeable_actors_read_as_one_voice_with_evidence(
    tmp_path: Path, calibration: Calibration
) -> None:
    build = write_build(tmp_path, actors=8, posts=6, own_voice=0.0, kind="original")
    answer = read_selection(build, calibration, list(range(48)))
    assert answer.outcome == "one voice" and answer.confidence == "possible"
    assert answer.score is not None and answer.score < 3.0
    assert 1 <= len(answer.pairs) <= 3
    assert all(pair.a.actor != pair.b.actor for pair in answer.pairs)
    assert answer.reliability is not None and answer.reliability.caught == 50
    assert answer.reference is not None and answer.reference.independent == (9.0, 19.0)
    # The same selection always gives the same answer.
    assert read_selection(build, calibration, list(range(48))).score == answer.score


def test_the_smaller_measured_size_is_read_when_the_larger_does_not_fit(
    tmp_path: Path, calibration: Calibration
) -> None:
    build = write_build(tmp_path, actors=4, posts=6, own_voice=3.0, kind="original")
    answer = read_selection(build, calibration, list(range(24)))
    assert answer.read is not None and (answer.read.actors, answer.read.posts_each) == (4, 4)
    assert answer.authorship is not None and answer.authorship.chance == 0.25


def test_too_few_actors_is_not_enough_evidence(tmp_path: Path, calibration: Calibration) -> None:
    build = write_build(tmp_path, actors=8, posts=6, own_voice=3.0, kind="original")
    answer = read_selection(build, calibration, list(range(12)))  # two actors
    assert answer.outcome == "not enough evidence"
    assert answer.reason is not None and "4 actors with 4 posts" in answer.reason
    assert "2 such actors" in answer.reason and answer.score is None


def test_reposts_are_not_counted(tmp_path: Path, calibration: Calibration) -> None:
    build = write_build(tmp_path, actors=8, posts=6, own_voice=0.0, kind="repost")
    answer = read_selection(build, calibration, list(range(48)))
    assert answer.outcome == "not enough evidence" and answer.selection.items == 0


def test_the_check_stays_off_when_it_was_not_measured(
    tmp_path: Path, calibration: Calibration
) -> None:
    build = write_build(tmp_path, actors=8, posts=6, own_voice=0.0, kind="original")
    assert read_selection(build, None, list(range(48))).outcome == "not enough evidence"
    other = calibration.model_copy(update={"embedding_key": "another-model"})
    answer = read_selection(build, other, list(range(48)))
    assert answer.outcome == "not enough evidence"
    assert answer.reason is not None and "another embedding model" in answer.reason


def test_score_separates_a_voice_from_none() -> None:
    rng = np.random.default_rng(0)
    who = np.repeat(np.arange(6), 6)
    apart = rng.normal(size=(6, DIMS))[who] * 3 + rng.normal(size=(36, DIMS))
    alike = rng.normal(size=(36, DIMS))
    with_voice = read_voices(apart, who, (6, 6), rng)
    without = read_voices(alike, who, (6, 6), rng)
    assert with_voice is not None and without is not None
    assert with_voice.score > 5 > abs(without.score)
    assert measured_size(who) == (6, 6)
    assert measured_size(who[:20]) is None  # three actors with enough posts
    assert read_voices(alike[:12], who[:12], (4, 4), rng) is None


def test_route_answers_and_refuses_a_point_outside_the_map(tmp_path: Path) -> None:
    build = write_build(tmp_path / "build", actors=8, posts=6, own_voice=0.0, kind="original")
    reports = tmp_path / "reports"
    (reports / "voices").mkdir(parents=True)
    (reports / "voices" / "metrics.json").write_text(json.dumps(METRICS), encoding="utf-8")
    assert load_calibration(reports) is not None and load_calibration(tmp_path) is None
    calibration_at.cache_clear()
    app = FastAPI()
    app.state.build = build
    app.state.reports_dir = reports
    app.include_router(voices_router, prefix="/api")
    client = TestClient(app)

    answer = client.post("/api/voices", json={"indices": list(range(48))})
    assert answer.status_code == 200 and answer.json()["outcome"] == "one voice"
    assert client.post("/api/voices", json={"indices": [48]}).status_code == 422
    assert client.post("/api/voices", json={"indices": []}).status_code == 422

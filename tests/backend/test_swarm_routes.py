"""The swarm layer is served with its evaluation report, or not at all."""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.metrics.routes import router as metrics_router
from backend.metrics.store import load_metrics
from backend.swarms.routes import load_swarms
from backend.swarms.routes import router as swarms_router

SWARMS = {
    "detector": "coposting-v1",
    "window_seconds": 60,
    "min_events": 3,
    "report": "reports/swarms/2026-11-14-coposting.md",
    "swarms": [
        {
            "id": 1,
            "name": "Swarm 1",
            "confidence": "probable",
            "n_actors": 2,
            "n_events": 5,
            "first_at": 1_000,
            "last_at": 9_000,
            "actors": [
                {"actor_id": "aaaaaaaaaaaa", "n_events": 5, "n_partners": 1},
                {"actor_id": "bbbbbbbbbbbb", "n_events": 5, "n_partners": 1},
            ],
            "events": [
                {
                    "at": 1_000,
                    "text": "the same words",
                    "actor_ids": ["aaaaaaaaaaaa", "bbbbbbbbbbbb"],
                    "spread_seconds": 0,
                }
            ],
            "weeks": [{"start": 0, "events": 5}],
        }
    ],
    "actors": {
        "aaaaaaaaaaaa": {"swarm": 1, "confidence": "probable", "n_events": 5, "n_partners": 1},
        "bbbbbbbbbbbb": {"swarm": 1, "confidence": "probable", "n_events": 5, "n_partners": 1},
    },
}

METRICS = {
    "detector": "swarms",
    "title": "Coordinated posting",
    "report": "reports/swarms/2026-11-14-coposting.md",
    "date": "2026-11-14",
    "unit": "account",
    "decides": "Whether an account posts the same text as others within a minute, repeatedly.",
    "operating_point": {"window_seconds": 60, "min_events": 3},
    "results": [
        {
            "name": "Recall",
            "kind": "recall",
            "set": "held-out accounts",
            "n": 100,
            "value": 0.5,
            "low": 0.4,
            "high": 0.6,
        },
        {"name": "Baseline", "kind": "baseline", "set": "held-out", "n": 100, "value": 0.9},
    ],
    "precision_at_base_rates": [{"prevalence": 0.01, "precision": 0.8, "low": 0.5, "high": 0.9}],
    "false_positive_modes": [
        {"mode": "share buttons", "example": "a prefilled text", "response": "an abstain band"}
    ],
    "untested": ["another platform"],
}


def client(build: Path, reports: Path) -> TestClient:
    app = FastAPI()
    app.include_router(swarms_router)
    app.include_router(metrics_router)
    app.state.swarms = load_swarms(build)
    app.state.metrics = load_metrics(reports)
    return TestClient(app)


def write(folder: Path, name: str, content: object) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(content), encoding="utf-8")


def test_layer_comes_with_its_measured_reliability(tmp_path: Path) -> None:
    write(tmp_path / "build", "swarms.json", SWARMS)
    write(tmp_path / "reports" / "swarms", "metrics.json", METRICS)
    api = client(tmp_path / "build", tmp_path / "reports")

    layer = api.get("/api/swarms").json()
    assert layer["swarms"] == [
        {
            "id": 1,
            "name": "Swarm 1",
            "confidence": "probable",
            "n_actors": 2,
            "n_events": 5,
            "first_at": 1_000,
            "last_at": 9_000,
        }
    ]
    assert layer["actors"]["aaaaaaaaaaaa"] == SWARMS["actors"]["aaaaaaaaaaaa"]
    assert layer["reliability"]["results"][0]["value"] == 0.5
    # A rate measured without an interval keeps none.
    assert layer["reliability"]["results"][1]["low"] is None

    one = api.get("/api/swarms/1").json()
    assert one["events"][0]["text"] == "the same words"
    assert api.get("/api/swarms/2").status_code == 404
    assert [d["detector"] for d in api.get("/api/metrics").json()["detectors"]] == ["swarms"]


def test_swarms_without_a_report_are_not_served(tmp_path: Path) -> None:
    write(tmp_path / "build", "swarms.json", SWARMS)
    (tmp_path / "reports").mkdir()
    api = client(tmp_path / "build", tmp_path / "reports")

    assert api.get("/api/swarms").status_code == 404
    assert api.get("/api/swarms/1").status_code == 404
    assert api.get("/api/metrics").json() == {"detectors": []}


def test_a_build_without_the_layer_serves_none(tmp_path: Path) -> None:
    (tmp_path / "build").mkdir()
    write(tmp_path / "reports" / "swarms", "metrics.json", METRICS)
    api = client(tmp_path / "build", tmp_path / "reports")

    assert api.get("/api/swarms").status_code == 404
    assert len(api.get("/api/metrics").json()["detectors"]) == 1


def test_a_report_off_contract_is_left_out(tmp_path: Path) -> None:
    write(tmp_path / "reports" / "swarms", "metrics.json", {"detector": "swarms"})

    assert load_metrics(tmp_path / "reports") == {}

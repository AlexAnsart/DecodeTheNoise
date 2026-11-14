import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from probe_fakes import PACK_EMBEDDING_KEY, FakeProbe, write_pack

from backend.probes.pack import EMPTY, Probes, load_probes
from backend.reports.routes import read_reports, router


def _client(reports_dir: Path, probes: Probes) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.probes = probes
    app.state.reports_dir = reports_dir
    return TestClient(app)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_metrics_lists_the_shown_probes_and_every_report(tmp_path: Path) -> None:
    listed = [
        FakeProbe("calls", possible_cut=-1.0, probable_cut=2.0),
        FakeProbe("hidden", possible_cut=0.0, probable_cut=1.0, state="review-only"),
    ]
    write_pack(tmp_path / "pack", listed)
    reports = tmp_path / "reports"
    _write(reports / "probes" / "metrics.json", json.dumps({"run": "v1", "targets": {}}))
    _write(reports / "swarms" / "planted" / "metrics.json", '{"recall": 0.5, "interval": NaN}')
    _write(reports / "probes" / "2026-11-14-v1.md", "# Report")
    _write(reports / "broken" / "metrics.json", "{not json")
    _write(reports / "list" / "metrics.json", "[1, 2, 3]")

    response = _client(reports, load_probes(tmp_path / "pack", PACK_EMBEDDING_KEY)).get(
        "/api/metrics"
    )

    assert response.status_code == 200
    # NaN is not JSON: a browser would refuse the whole answer.
    assert "NaN" not in response.text
    body = response.json()
    assert [probe["key"] for probe in body["probes"]] == ["calls"]
    assert body["probes"][0]["probable"]["precision"] == 0.9
    assert body["reports"] == [
        {"detector": "probes", "metrics": {"run": "v1", "targets": {}}},
        {"detector": "swarms/planted", "metrics": {"recall": 0.5, "interval": None}},
    ]


def test_without_reports_or_probes_the_answer_is_empty(tmp_path: Path) -> None:
    body = _client(tmp_path / "absent", EMPTY).get("/api/metrics").json()

    assert body == {"probes": [], "reports": []}
    assert read_reports(tmp_path / "absent") == []

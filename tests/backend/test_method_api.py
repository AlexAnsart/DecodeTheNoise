import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import write_tiny_build
from method_fakes import COMMIT, MethodApi, method_api, post, write, write_posts

from backend.map.schema import PROVENANCE_FILE
from backend.map.store import load_build
from backend.method import labels
from backend.method.schema import Provenance

CALLS_GUIDE = """# Calls

Version: 2

## `call_vote`

**Question.** Does the author ask the readers to vote for or against someone?

YES when the post names who to vote for.

## `call_join`

**Question.** Does the author ask the readers to join a group?
"""
TAXONOMY = (
    SimpleNamespace(name="call_vote", family="calls", use="probe", values=("yes", "no", "unclear")),
    SimpleNamespace(name="theme", family="subject", use="descriptor", values=("sport", "other")),
    SimpleNamespace(name="irony", family="format", use="auxiliary", values=("yes", "no")),
)
PROVENANCE = Provenance(
    dataset="tweets-sample-2026",
    source_url="https://huggingface.co/datasets/SinclairSchneider/tweets_sample_2026",
    revision="254bbe4",
    files=["train-00000-of-00073.parquet"],
    licence="not stated",
    sample={"seed": "demo-sample-v1", "items": 12},
)


@pytest.fixture
def api(tmp_path: Path) -> MethodApi:
    return method_api(tmp_path)


def _fill(api: MethodApi, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(labels, "taxonomy_rows", lambda: TAXONOMY)
    guides = api.docs / "probes" / "guides"
    write(guides / "calls.md", CALLS_GUIDE)
    write(guides / "common.md", "# Rules common to every label\n\n1. Judge the text.")
    write(api.docs / "probes" / "report.md", "# Probe campaign\n\n![x](figures/test-v1.png)")
    write(api.docs / "probes" / "journal.md", "No heading here.")
    (api.docs / "probes" / "figures").mkdir()
    (api.docs / "probes" / "figures" / "test-v1.png").write_bytes(b"\x89PNG fake")
    write(api.docs / "probes" / "figures" / "notes.txt", "not a figure")
    targets = {
        "call_vote": {"state": "review-only"},
        "theme:other": {"state": "dropped"},
        "theme:sport": {"state": "shown"},
    }
    probe_reports = api.reports / "probes"
    write(probe_reports / "metrics.json", json.dumps({"run": "v1", "targets": targets}))
    write(probe_reports / "agreement.json", '{"call_vote": {"kappa": 0.8, "low": NaN}}')
    write(probe_reports / "prevalence.json", "[1, 2]")
    write(probe_reports / "broken.json", "{not json")
    write(probe_reports / "scalar.json", "3")


def test_every_part_is_read_from_its_file(
    api: MethodApi, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fill(api, monkeypatch)
    build_folder = tmp_path / "build"
    build_folder.mkdir()
    write_tiny_build(build_folder)
    write(build_folder / PROVENANCE_FILE, PROVENANCE.model_dump_json())
    build = load_build(build_folder)
    api.app.state.build = build
    write_posts(api, [(post("tiny:0", "Vote for her", {"call_vote": "yes"}), [0.0, 0.0])])

    response = api.client.get("/api/method")
    build.items.close()

    assert response.status_code == 200
    # NaN is not JSON: a browser would refuse the whole answer.
    assert "NaN" not in response.text
    body = response.json()
    assert body["commit"] == COMMIT
    assert body["repository"] == "https://github.com/AlexAnsart/DecodeTheNoise"
    assert body["build"]["name"] == "tiny"
    assert body["build"]["points"] == 12
    assert body["provenance"] == PROVENANCE.model_dump()
    assert [guide["name"] for guide in body["guides"]] == ["common", "calls"]
    assert body["guides"][1]["markdown"] == CALLS_GUIDE
    assert body["guides"][1]["path"] == "docs/probes/guides/calls.md"
    assert [(doc["name"], doc["title"]) for doc in body["documents"]] == [
        ("report", "Probe campaign"),
        ("journal", "journal"),
    ]
    assert body["figures"] == ["test-v1.png"]
    assert body["probe_files"] == {
        "agreement": {"call_vote": {"kappa": 0.8, "low": None}},
        "prevalence": [1, 2],
    }
    by_name = {label["name"]: label for label in body["labels"]}
    assert list(by_name) == ["call_vote", "theme", "irony"]
    assert by_name["call_vote"]["question"] == (
        "Does the author ask the readers to vote for or against someone?"
    )
    assert by_name["call_vote"]["state"] == "review-only"
    # A label with one probe per answer takes the best state among them.
    assert by_name["theme"]["state"] == "shown"
    assert by_name["theme"]["values"] == ["sport", "other"]
    assert by_name["irony"] == {
        "name": "irony",
        "family": "format",
        "use": "auxiliary",
        "values": ["yes", "no"],
        "question": None,
        "state": None,
    }
    assert body["labelled"]["posts"] == 1
    assert body["labelled"]["round_kinds"] == {"m1": "annotation"}
    # No review runs on this app.
    assert body["review"] is None


def test_with_nothing_on_disk_the_answer_is_empty_not_an_error(
    api: MethodApi, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(labels, "taxonomy_rows", lambda: ())

    response = api.client.get("/api/method")

    assert response.status_code == 200
    assert response.json() == {
        "commit": COMMIT,
        "repository": "https://github.com/AlexAnsart/DecodeTheNoise",
        "build": None,
        "provenance": None,
        "labels": [],
        "guides": [],
        "documents": [],
        "figures": [],
        "probe_files": {},
        "review": None,
        "labelled": None,
    }


def test_the_review_is_described_by_the_review_that_runs(
    api: MethodApi, monkeypatch: pytest.MonkeyPatch
) -> None:
    guides_module = pytest.importorskip("backend.review.guides")
    pytest.importorskip("backend.review.method")
    _fill(api, monkeypatch)
    write(
        api.docs / "probes" / "guides" / "rhetoric.md",
        "# Rhetoric\n\n## `fear_appeal`\n\n**Question.** Does the post try to frighten?\n",
    )
    guides = guides_module.load_guides(api.docs / "probes" / "guides")
    api.app.state.services = SimpleNamespace(reviewer=SimpleNamespace(guides=guides, model=""))

    review = api.client.get("/api/method").json()["review"]

    assert review["model"] is None
    assert review["prompt_version"]
    assert review["selection_prompt_version"]
    assert [technique["key"] for technique in review["techniques"]] == ["fear_appeal"]
    assert review["techniques"][0]["question"] == "Does the post try to frighten?"
    # The prompts are the ones sent: they hold the guide, word for word.
    assert "Does the post try to frighten?" in review["system"]
    assert "Does the post try to frighten?" in review["selection_system"]
    assert review["neighbours"] > 0
    assert review["selection_posts"] > 0


def test_a_figure_is_served_only_when_it_is_listed(
    api: MethodApi, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fill(api, monkeypatch)
    write(api.docs / "secret.png", "outside the figures")

    served = api.client.get("/api/method/figures/test-v1.png")

    assert served.status_code == 200
    assert served.content == b"\x89PNG fake"
    assert served.headers["content-type"] == "image/png"
    assert "max-age" in served.headers["cache-control"]
    for name in ("notes.txt", "missing.png", "..%2F..%2Fsecret.png", "%2E%2E%5Csecret.png"):
        assert api.client.get(f"/api/method/figures/{name}").status_code == 404

"""The export of the labelled posts, on a hand-made campaign: three rounds in a temp folder."""

import json
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

from pipelines.vectors import write_vectors

# The campaign's own code reads the rounds. A checkout without it has nothing to export.
pytest.importorskip("pipelines.probes.report")

from pipelines.method.labelled import export  # noqa: E402
from pipelines.probes.dataset import build_vectors  # noqa: E402

MODEL_KEY = "test-model@0|prefix=''|dims=4"
ROUNDS = Path("data") / "probes" / "rounds"
VOTE = {"key": "tiny:2", "split": "test", "stratum": "random", "text": "Vote for her"}
MATCH = {"key": "tiny:0", "split": "train", "stratum": "enrich:theme:search", "text": "A match"}
UNREAD = {"key": "tiny:1", "split": "train", "stratum": "random", "text": "Nobody read this"}


def _lines(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _reading(key: str, batch: str, labels: dict[str, str], evidence: dict[str, str]) -> dict:
    return {"key": key, "batch_id": batch, "n": 1, "labels": labels, "evidence": evidence}


def _round(name: str, items: list[dict], drawn_at: int) -> Path:
    folder = ROUNDS / name
    _lines(folder / "items.jsonl", items)
    os.utime(folder / "items.jsonl", (drawn_at, drawn_at))
    return folder / "labels"


@pytest.fixture
def campaign(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[np.ndarray]:
    """Every path of the pipelines is relative: the campaign lives under the temp folder."""
    monkeypatch.chdir(tmp_path)
    build_vectors.cache_clear()
    vectors = np.random.default_rng(3).normal(size=(3, 4)).astype(np.float32)
    work = Path("data") / "work" / "tiny"
    work.mkdir(parents=True)
    write_vectors(work, vectors, MODEL_KEY, native_dims=4)

    pilot = _round("p1", [VOTE], drawn_at=1_000)
    _lines(pilot / "calls" / "a.jsonl", [_reading("tiny:2", "p1-calls-a-001", {}, {})])

    main = _round("m1", [VOTE, UNREAD, MATCH], drawn_at=2_000)
    yes, no = {"call_vote": "yes"}, {"call_vote": "no"}
    quote = {"call_vote": "Vote for her"}
    _lines(
        main / "calls" / "a.jsonl",
        [
            _reading("tiny:2", "m1-calls-a-001", yes, quote),
            _reading("tiny:0", "m1-calls-a-001", no, {}),
        ],
    )
    _lines(main / "calls" / "b.jsonl", [_reading("tiny:2", "m1-calls-b-004", yes, quote)])
    (main / "calls" / "settled.json").write_text(json.dumps({"tiny:2": yes, "tiny:0": no}))
    _lines(main / "subject" / "a.jsonl", [_reading("tiny:0", "m1-subject-a-002", {}, {})])
    (main / "subject" / "settled.json").write_text(json.dumps({"tiny:0": {"theme": "sport"}}))

    again = {**VOTE, "stratum": "audit:call_vote"}
    audit = _round("a1_calls", [again], drawn_at=3_000)
    _lines(audit / "calls" / "a.jsonl", [_reading("tiny:2", "a1_calls-calls-a-001", no, {})])
    # Settled by mistake: a second reading must still settle nothing.
    (audit / "calls" / "settled.json").write_text(json.dumps({"tiny:2": no}))
    yield vectors
    # The vectors are memory-mapped: released, so that the temp folder can be removed.
    build_vectors.cache_clear()


def _rows(path: Path) -> list[tuple]:
    con = sqlite3.connect(path)
    rows = con.execute(
        "SELECT id, split, round, kind, stratum, answers, readings, vector "
        "FROM posts JOIN readings USING (n) JOIN vectors USING (n) ORDER BY n"
    ).fetchall()
    con.close()
    return rows


def test_the_export_holds_every_post_read_but_the_pilot(campaign: np.ndarray) -> None:
    out = Path("out") / "labelled.sqlite"

    summary = export(out)

    assert summary.posts == 3
    assert summary.rounds == ["m1", "a1_calls"]
    assert summary.round_kinds == {"m1": "annotation", "a1_calls": "second reader"}
    assert summary.kinds == {"annotation": 2, "second reader": 1}
    assert summary.splits == {"test": 2, "train": 1}
    assert summary.labels == ["call_vote", "theme"]
    vote, match, second = _rows(out)
    assert vote[:5] == ("tiny:2", "test", "m1", "annotation", "random")
    assert json.loads(vote[5]) == {"call_vote": "yes"}
    assert [reading["reader"] for reading in json.loads(vote[6])] == [
        "m1-calls-a-001",
        "m1-calls-b-004",
    ]
    assert json.loads(vote[6])[0]["quotes"] == {"call_vote": "Vote for her"}
    # The answers of two families are the answers of one post.
    assert match[0] == "tiny:0"
    assert json.loads(match[5]) == {"call_vote": "no", "theme": "sport"}
    assert second[:5] == ("tiny:2", "test", "a1_calls", "second reader", "audit:call_vote")
    assert json.loads(second[5]) == {}
    assert json.loads(second[6])[0]["answers"] == {"call_vote": "no"}
    # Each post keeps the vector of its row in its build.
    stored = [np.frombuffer(row[7], dtype=np.float16) for row in (vote, match, second)]
    expected = campaign.astype(np.float16)[[2, 0, 2]]
    assert np.array_equal(np.stack(stored), expected)


def test_the_export_is_written_again_when_the_campaign_goes_on(campaign: np.ndarray) -> None:
    out = Path("out") / "labelled.sqlite"
    export(out)
    readings = ROUNDS / "m1" / "labels" / "calls" / "a.jsonl"
    more = _reading("tiny:1", "m1-calls-a-009", {"call_vote": "no"}, {})
    readings.write_text(readings.read_text() + json.dumps(more) + "\n", encoding="utf-8")

    summary = export(out)

    assert summary.posts == 4
    assert [row[0] for row in _rows(out)] == ["tiny:2", "tiny:1", "tiny:0", "tiny:2"]
    assert [path.name for path in out.parent.iterdir()] == ["labelled.sqlite"]

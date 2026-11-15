"""The posts the annotators read, as one file: written by `pipelines.method.labelled`, read by
the explorer of the method page (`backend/method/explorer.py`).

One row per post read in a round: its text, why it was drawn, the settled answers, every
reading with the spans it quoted, and the vector of the post. The vector is what lets a probe
be compared with the annotation post by post, with the probes the server has now.
"""

import json
import sqlite3
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from backend.method.schema import LabelledSummary, Reading

# The kinds of round. A second reader read posts of other rounds again: its readings are kept
# apart, in rows of their own, and settle no answer.
ANNOTATION = "annotation"
SECOND_READER = "second reader"

# The readings and the vectors are kept out of `posts`: a filter scans short rows, and only the
# posts of the page shown have their readings read.
SCHEMA = """
CREATE TABLE posts(
    n INTEGER PRIMARY KEY, id TEXT NOT NULL, text TEXT NOT NULL, split TEXT NOT NULL,
    round TEXT NOT NULL, kind TEXT NOT NULL, stratum TEXT NOT NULL, answers TEXT NOT NULL);
CREATE TABLE readings(n INTEGER PRIMARY KEY, readings TEXT NOT NULL);
CREATE TABLE vectors(n INTEGER PRIMARY KEY, vector BLOB NOT NULL);
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""
# A post with its readings: n, id, text, split, round, kind, stratum, answers, readings.
POSTS = (
    "SELECT posts.n, id, text, split, round, kind, stratum, answers, readings "
    "FROM posts JOIN readings USING (n)"
)


@dataclass(frozen=True)
class LabelledRecord:
    id: str
    text: str
    split: str
    round: str
    kind: str
    stratum: str
    answers: dict[str, str]
    readings: list[Reading]


def summarise(records: Sequence[LabelledRecord]) -> LabelledSummary:
    return LabelledSummary(
        posts=len(records),
        labels=sorted({label for record in records for label in record.answers}),
        splits=dict(Counter(record.split for record in records)),
        rounds=list(dict.fromkeys(record.round for record in records)),
        round_kinds={record.round: record.kind for record in records},
        kinds=dict(Counter(record.kind for record in records)),
    )


def _post_row(n: int, record: LabelledRecord) -> tuple[object, ...]:
    answers = json.dumps(record.answers, ensure_ascii=False)
    return (
        n,
        record.id,
        record.text,
        record.split,
        record.round,
        record.kind,
        record.stratum,
        answers,
    )


def _readings_json(record: LabelledRecord) -> str:
    return json.dumps([reading.model_dump() for reading in record.readings], ensure_ascii=False)


def write_labelled(
    path: Path, records: Sequence[LabelledRecord], vectors: np.ndarray, embedding_key: str
) -> LabelledSummary:
    """Writes the file beside its place, then swaps it in: a reader never sees half a file.
    `vectors` holds one row per record, in the same order."""
    if len(vectors) != len(records):
        raise ValueError(f"{len(records)} posts for {len(vectors)} vectors")
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(path.name + ".new")
    staged.unlink(missing_ok=True)
    summary = summarise(records)
    stored = np.ascontiguousarray(vectors, dtype=np.float16)
    meta = {
        "embedding_key": embedding_key,
        "dims": str(stored.shape[1]),
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "summary": summary.model_dump_json(),
    }
    con = sqlite3.connect(staged)
    with con:
        con.executescript(SCHEMA)
        con.executemany(
            "INSERT INTO posts VALUES (?,?,?,?,?,?,?,?)",
            (_post_row(n, record) for n, record in enumerate(records)),
        )
        con.executemany(
            "INSERT INTO readings VALUES (?,?)",
            ((n, _readings_json(record)) for n, record in enumerate(records)),
        )
        con.executemany(
            "INSERT INTO vectors VALUES (?,?)", ((n, row.tobytes()) for n, row in enumerate(stored))
        )
        con.executemany("INSERT INTO meta VALUES (?, ?)", list(meta.items()))
    con.close()
    staged.replace(path)
    return summary

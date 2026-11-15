"""The explorer over the posts the annotators read: a page of them under filters, and the
whole file as JSON lines.

Expected cost of a page: one scan of the short rows (tens of thousands), one product of their
vectors by the probes when a probe is asked for, a read of the posts shown.
"""

import json
import sqlite3
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backend.method.filters import PageQuery, by_probe, candidates
from backend.method.labelled import POSTS
from backend.method.schema import LabelledPage, LabelledPost, LabelledSummary
from backend.probes.pack import Probes

# Posts sent at once by the download: a line at a time would cost a thread switch per post.
LINES_PER_CHUNK = 500
# The columns of `POSTS` after the row number, up to the two that are stored as JSON.
_PLAIN = ("id", "text", "split", "round", "kind", "stratum")


@dataclass(frozen=True)
class _Facts:
    stamp: tuple[int, int]
    summary: LabelledSummary
    embedding_key: str
    dims: int


def _post(row: tuple, scores: dict[str, float]) -> LabelledPost:
    plain = dict(zip(_PLAIN, row[1:7], strict=True))
    return LabelledPost(
        **plain, answers=json.loads(row[7]), readings=json.loads(row[8]), scores=scores
    )


def _line(row: tuple) -> str:
    # The answers and the readings are stored as JSON already: they are not parsed to be
    # written again.
    opening = json.dumps(dict(zip(_PLAIN, row[1:7], strict=True)), ensure_ascii=False)[:-1]
    return f'{opening}, "answers": {row[7]}, "readings": {row[8]}}}\n'


class LabelledStore:
    """Reads the file on demand. Nothing stays open between two requests, so the file can be
    replaced while the server runs; what is kept of it is read again when it changed."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._facts: _Facts | None = None
        self._vectors: tuple[tuple[int, int], np.ndarray] | None = None

    def _open(self) -> sqlite3.Connection:
        # A download is read by the worker threads in turn, never by two at once.
        return sqlite3.connect(
            f"file:{self._path.as_posix()}?mode=ro", uri=True, check_same_thread=False
        )

    def _current(self) -> _Facts | None:
        if not self._path.is_file():
            return None
        stat = self._path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        with self._lock:
            if self._facts is None or self._facts.stamp != stamp:
                con = self._open()
                meta = dict(con.execute("SELECT key, value FROM meta"))
                con.close()
                self._facts = _Facts(
                    stamp,
                    LabelledSummary.model_validate_json(meta["summary"]),
                    meta["embedding_key"],
                    int(meta["dims"]),
                )
            return self._facts

    def _vectors_of(self, facts: _Facts) -> np.ndarray:
        """One float32 row per post, in row order. Read once per file: 15 MB for 30,000 posts."""
        with self._lock:
            if self._vectors is None or self._vectors[0] != facts.stamp:
                con = self._open()
                blobs = [row[0] for row in con.execute("SELECT vector FROM vectors ORDER BY n")]
                con.close()
                stored = np.frombuffer(b"".join(blobs), dtype=np.float16)
                matrix = stored.reshape(len(blobs), facts.dims).astype(np.float32)
                self._vectors = (facts.stamp, matrix)
            return self._vectors[1]

    def summary(self) -> LabelledSummary | None:
        facts = self._current()
        return facts.summary if facts else None

    def embedding_key(self) -> str | None:
        """The model the vectors of the file were made with: the probes of a server on another
        model do not read them."""
        facts = self._current()
        return facts.embedding_key if facts else None

    def page(self, probes: Probes, query: PageQuery, scored: bool = True) -> LabelledPage:
        """The posts the filters keep. With a probe, the posts it scores highest come first.
        `scored` is false when the probes do not read the vectors of this file: no score is
        shown then, and no probe can be asked for."""
        facts = self._current()
        if facts is None or (query.label and query.label not in facts.summary.labels):
            return LabelledPage(total=0, posts=[])
        con = self._open()
        try:
            rows = candidates(con, query, facts.summary.labels)
            ns = np.array([row[0] for row in rows], dtype=np.int64)
            if query.probe and len(ns):
                vectors = self._vectors_of(facts)[ns]
                settled = [row[1] for row in rows]
                ns = ns[by_probe(probes, query.probe, query.level, vectors, settled)]
            shown = [int(n) for n in ns[query.offset : query.offset + query.limit]]
            marks = ",".join("?" * len(shown))
            by_n = {row[0]: row for row in con.execute(f"{POSTS} WHERE n IN ({marks})", shown)}
        finally:
            con.close()
        maps: list[dict[str, float]] = [{} for _ in shown]
        if scored and shown:
            scores = probes.scores(self._vectors_of(facts)[shown])
            maps = [probes.score_map(row) for row in scores]
        posts = [_post(by_n[n], found) for n, found in zip(shown, maps, strict=True)]
        return LabelledPage(total=len(ns), posts=posts)

    def lines(self) -> Iterator[str]:
        """Every post as one JSON object per line, without its vector, some hundreds of posts
        at a time."""
        if not self._path.is_file():
            return
        con = self._open()
        try:
            cursor = con.execute(f"{POSTS} ORDER BY n")
            while rows := cursor.fetchmany(LINES_PER_CHUNK):
                yield "".join(_line(row) for row in rows)
        finally:
            con.close()

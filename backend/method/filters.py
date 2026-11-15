"""Which labelled posts a page of the explorer keeps: plain filters in SQL, then a probe
compared with the settled answer on its own label."""

import sqlite3
from dataclasses import dataclass
from typing import Literal

import numpy as np

from backend.probes.pack import Probes

UNCLEAR = "unclear"
YES = "yes"
MAX_WORDS = 6
# How a probe is compared with the annotation. A probe flags a post from the lowest level it
# has: a score of 0.5 where it has a `possible` level. `flagged`: it flags a post that has an
# answer on its label. `agreed`: it flags a post answered yes. `false alarm`: it flags a post
# answered no. `missed`: it leaves a post answered yes.
Level = Literal["flagged", "agreed", "false alarm", "missed"]


@dataclass(frozen=True)
class PageQuery:
    label: str | None = None
    answer: str | None = None
    split: str | None = None
    round: str | None = None
    kind: str | None = None
    probe: str | None = None
    level: Level | None = None
    words: tuple[str, ...] = ()
    offset: int = 0
    limit: int = 25


def _like(word: str) -> str:
    escaped = word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def candidates(
    con: sqlite3.Connection, query: PageQuery, labels: list[str]
) -> list[tuple[int, str | None]]:
    """Rows the plain filters keep, in row order, each with its settled answer on the label of
    the probe asked for (null without a probe). `labels` are the label names of the file: a
    name is only put in a JSON path once it is known to be one of them."""
    own = query.probe.partition(":")[0] if query.probe else None
    select, params = "NULL", []
    if own in labels:
        select, params = "json_extract(answers, ?)", [f'$."{own}"']
    where: list[str] = []
    plain = (("split", query.split), ("round", query.round), ("kind", query.kind))
    for column, value in plain:
        if value:
            where.append(f"{column} = ?")
            params.append(value)
    if query.label:
        params.append(f'$."{query.label}"')
        if query.answer:
            where.append("json_extract(answers, ?) = ?")
            params.append(query.answer)
        else:
            where.append("json_extract(answers, ?) IS NOT NULL")
    for word in query.words[:MAX_WORDS]:
        where.append("text LIKE ? ESCAPE '\\'")
        params.append(_like(word))
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    return con.execute(f"SELECT n, {select} FROM posts {clause} ORDER BY n", params).fetchall()


def by_probe(
    probes: Probes,
    probe: str,
    level: Level | None,
    vectors: np.ndarray,
    settled: list[str | None],
) -> np.ndarray:
    """Positions, among the candidate rows, of those at the level asked, the posts the probe
    scores highest first. `vectors` and `settled` hold one entry per candidate."""
    column = probes.column(probe)
    every = probes.scores(vectors)
    scores, flagged = every[:, column], probes.flags(every)[:, column]
    # A probe of a label with answers of its own reads one of them: `theme:sport`.
    positive = probe.partition(":")[2] or YES
    answered = np.array([value is not None and value != UNCLEAR for value in settled], dtype=bool)
    yes = np.array([value == positive for value in settled], dtype=bool)
    keep = {
        None: np.ones(len(settled), dtype=bool),
        "flagged": flagged & answered,
        "agreed": flagged & yes,
        "false alarm": flagged & answered & ~yes,
        "missed": ~flagged & yes,
    }[level]
    kept = np.flatnonzero(keep)
    return kept[np.argsort(-scores[kept], kind="stable")]

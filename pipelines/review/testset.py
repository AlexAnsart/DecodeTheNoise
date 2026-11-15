"""The posts the review is measured on: the random test sample of the probe campaign.

Read-only. The campaign drew these posts uniformly from the test split (split by account) and
settled each answer from two readings, with a third where the two differed. They are the only
posts a rate is read on: the other test rounds were drawn by the score of a probe.
"""

import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from pipelines.paths import CORPUS_FILE, work_dir
from pipelines.probes.dataset import load_labelled, vectors_for
from pipelines.probes.pool import SPLITS
from pipelines.probes.sample import RANDOM, read_items, read_jsonl, round_dir
from pipelines.probes.taxonomy import NO, YES

ROUND = "m1"
SPLIT = "test"
# Agreement between two annotators per label, published by the campaign.
AGREEMENT = Path("reports") / "probes" / "agreement.json"
READINGS = ("a", "b", "c")


@dataclass(frozen=True)
class Post:
    key: str
    text: str
    # The settled answer per technique, true for yes. A technique left unclear has no entry.
    answers: Mapping[str, bool]


class _Agreement(BaseModel):
    n: int
    kappa: float | None


def load_posts(techniques: Sequence[str]) -> list[Post]:
    labelled = load_labelled((ROUND,))
    texts = {item.key: item.text for item in read_items(ROUND)}
    posts = []
    for row, key in enumerate(labelled.keys):
        if SPLITS[labelled.split[row]] != SPLIT or labelled.stratum[row] != RANDOM:
            continue
        answers = {
            name: labelled.answers[name][row] == YES
            for name in techniques
            if name in labelled.answers and labelled.answers[name][row] in (YES, NO)
        }
        posts.append(Post(key=key, text=texts[key], answers=answers))
    return posts


def reference_kappas(techniques: Sequence[str]) -> dict[str, float | None]:
    """Cohen's kappa between two annotators on each technique; None where none was measured."""
    found = json.loads(AGREEMENT.read_text(encoding="utf-8")) if AGREEMENT.is_file() else {}
    return {
        name: _Agreement.model_validate(found[name]).kappa if name in found else None
        for name in techniques
    }


def post_vectors(keys: Sequence[str]) -> tuple[np.ndarray, str]:
    """One vector per post, and the key of the embedding model that made them."""
    return vectors_for(list(keys))


def count_accounts(keys: Sequence[str]) -> int:
    """How many accounts wrote the posts: the groups the split was made on."""
    rows_of: dict[str, list[int]] = {}
    for key in keys:
        build, row = key.rsplit(":", 1)
        rows_of.setdefault(build, []).append(int(row))
    accounts: set[str] = set()
    for build, rows in rows_of.items():
        path = work_dir(build) / CORPUS_FILE
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        for start in range(0, len(rows), 500):
            chunk = rows[start : start + 500]
            marks = ",".join("?" * len(chunk))
            query = f"SELECT actor_id FROM items WHERE idx IN ({marks})"  # noqa: S608
            accounts.update(actor for (actor,) in con.execute(query, chunk))
        con.close()
    return len(accounts)


def annotator_quotes(families: Sequence[str]) -> dict[tuple[str, str], list[str]]:
    """The spans the annotators quoted for a yes, by (post, label): what an audit reads."""
    quotes: dict[tuple[str, str], list[str]] = {}
    for family in families:
        for reading in READINGS:
            path = round_dir(ROUND) / "labels" / family / f"{reading}.jsonl"
            for row in read_jsonl(path) if path.is_file() else []:
                for label, quote in row.get("evidence", {}).items():
                    quotes.setdefault((row["key"], label), []).append(quote)
    return quotes

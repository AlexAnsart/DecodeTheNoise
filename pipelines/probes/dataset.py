"""The labelled posts of the campaign, joined to their vectors.

Labels come from the settled answers of each round (`merge`). A post answered `unclear` on a
label is left out for that label only. Vectors are read from the builds, row by row.
"""

import json
from dataclasses import dataclass
from functools import cache

import numpy as np

from pipelines.paths import VECTORS_FILE, VECTORS_META, work_dir
from pipelines.probes.pool import SPLITS
from pipelines.probes.sample import read_items, round_dir
from pipelines.probes.taxonomy import FAMILIES, UNCLEAR, YES, Label


@dataclass(frozen=True)
class Labelled:
    keys: tuple[str, ...]
    split: np.ndarray  # index into SPLITS
    stratum: tuple[str, ...]
    answers: dict[str, np.ndarray]  # label name -> one answer per post, "" when not annotated

    def rows(self, label: Label, split: str | None = None) -> np.ndarray:
        """Posts with a settled answer on `label`, in `split` when given."""
        values = self.answers[label.name]
        mask = (values != "") & (values != UNCLEAR)
        if split is not None:
            mask &= self.split == SPLITS.index(split)
        return np.flatnonzero(mask)

    def target(self, label: Label, rows: np.ndarray) -> np.ndarray:
        return (self.answers[label.name][rows] == YES).astype(np.int8)


def load_labelled(rounds: tuple[str, ...]) -> Labelled:
    """One entry per post over the rounds; a post belongs to one round only."""
    items = [item for name in rounds for item in read_items(name)]
    index = {item.key: i for i, item in enumerate(items)}
    answers: dict[str, np.ndarray] = {}
    for name in rounds:
        for family in FAMILIES:
            path = round_dir(name) / "labels" / family / "settled.json"
            if not path.exists():
                continue
            for key, row in json.loads(path.read_text(encoding="utf-8")).items():
                for label_name, value in row.items():
                    # Not `setdefault`: it would build a new column for every answer read.
                    if label_name not in answers:
                        answers[label_name] = np.full(len(items), "", dtype="U24")
                    answers[label_name][index[key]] = value
    split = np.array([SPLITS.index(item.split) for item in items], dtype=np.int8)
    stratum = tuple(item.stratum for item in items)
    return Labelled(tuple(item.key for item in items), split, stratum, answers)


@cache
def build_vectors(build: str) -> tuple[np.ndarray, str]:
    """The vectors of one build, memory-mapped, and the key of the model that made them."""
    work = work_dir(build)
    meta = json.loads((work / VECTORS_META).read_text(encoding="utf-8"))
    table = np.memmap(work / VECTORS_FILE, dtype=np.float16, mode="r")
    return table.reshape(int(meta["n"]), int(meta["dims"])), str(meta["key"])


def vectors_for(keys: tuple[str, ...] | list[str]) -> tuple[np.ndarray, str]:
    """One float32 unit vector per post, and the single model key they share."""
    out: list[np.ndarray] = []
    model_keys = set()
    for key in keys:
        build, idx = key.rsplit(":", 1)
        table, model_key = build_vectors(build)
        out.append(np.asarray(table[int(idx)], dtype=np.float32))
        model_keys.add(model_key)
    if len(model_keys) != 1:
        raise ValueError(f"vectors of several models: {sorted(model_keys)}")
    return np.stack(out), model_keys.pop()

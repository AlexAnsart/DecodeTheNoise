"""The answers of the model, kept as they came: one JSON line per paid call.

An answer is stored under the review's own cache key and a run number. Run 1 is the answer the
evaluation counts; run 2 is the same question asked again, to see whether the answer holds.
"""

import json
from pathlib import Path

from pydantic import BaseModel


class _Line(BaseModel):
    key: str
    run: int
    post: str
    raw: str


class Answers:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._raw: dict[tuple[str, int], str] = {}
        if path.is_file():
            # A post may hold a Unicode line separator: only "\n" ends a line here.
            for text in path.read_text(encoding="utf-8").split("\n"):
                if text:
                    line = _Line.model_validate_json(text)
                    self._raw[line.key, line.run] = line.raw

    def __len__(self) -> int:
        return len(self._raw)

    def get(self, key: str, run: int) -> str | None:
        return self._raw.get((key, run))

    def keep(self, key: str, run: int, post: str, raw: str) -> None:
        self._raw[key, run] = raw
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(_Line(key=key, run=run, post=post, raw=raw).model_dump()) + "\n")

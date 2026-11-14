"""Append-only cache of full-size vectors keyed by content hash.

Embedding is the slow step, so a run that stops half-way keeps what it paid for: the next run
embeds only the hashes that are missing. Vectors are written before their hashes, so the hash
file never names a row that is not on disk.
"""

import json
from pathlib import Path

import numpy as np

HASHES_FILE = "hashes.txt"
VECTORS_FILE = "vectors.f16"
META_FILE = "meta.json"


class VectorStore:
    def __init__(self, folder: Path, key: str) -> None:
        self._folder = folder
        self._key = key
        self._width = 0
        self._rows: dict[str, int] = {}
        folder.mkdir(parents=True, exist_ok=True)
        meta_path = folder / META_FILE
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta["key"] != key:
                raise ValueError(f"store {folder} holds vectors of {meta['key']}, not {key}")
            self._width = int(meta["width"])
            self._load()

    def _load(self) -> None:
        hashes = (self._folder / HASHES_FILE).read_text(encoding="ascii").split()
        on_disk = (self._folder / VECTORS_FILE).stat().st_size // (self._width * 2)
        self._rows = {h: row for row, h in enumerate(hashes[:on_disk])}

    @property
    def width(self) -> int:
        return self._width

    def missing(self, hashes: list[str]) -> list[str]:
        return [h for h in dict.fromkeys(hashes) if h not in self._rows]

    def add(self, hashes: list[str], vectors: np.ndarray) -> None:
        if self._width == 0:
            self._width = int(vectors.shape[1])
            meta = {"key": self._key, "width": self._width}
            (self._folder / META_FILE).write_text(json.dumps(meta), encoding="utf-8")
        start = len(self._rows)
        with (self._folder / VECTORS_FILE).open("r+b" if start else "wb") as out:
            # A crash between the two writes leaves orphan rows: overwrite them.
            out.seek(start * self._width * 2)
            out.write(vectors.astype(np.float16).tobytes())
            out.truncate()
        with (self._folder / HASHES_FILE).open("a" if start else "w", encoding="ascii") as out:
            out.write("".join(h + "\n" for h in hashes))
        self._rows.update({h: start + i for i, h in enumerate(hashes)})

    def rows(self, hashes: list[str]) -> np.ndarray:
        """Full-size vectors for `hashes`, in that order, as float32."""
        stored = np.memmap(self._folder / VECTORS_FILE, dtype=np.float16, mode="r")
        table = stored.reshape(-1, self._width)
        return np.asarray(table[[self._rows[h] for h in hashes]], dtype=np.float32)

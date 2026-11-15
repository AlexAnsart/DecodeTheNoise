"""The map build contract: written by `pipelines.pack`, served by the API, read by the front end.

A build is a folder holding `map.json` (this manifest), `map.bin` (the buffers, concatenated),
`items.sqlite` (item content, one row per point) and `vectors.f16` (one unit vector per point).
Point order is the same in all four. `provenance.json` beside them says where the items come
from (shape: `backend/method/schema.py`); a build made before it existed has none.
"""

from typing import Literal

from pydantic import BaseModel

from backend.probes.schema import ProbeInfo, ProbeReading
from backend.review.schema import Review

MANIFEST_FILE = "map.json"
BUFFERS_FILE = "map.bin"
# The same bytes compressed, served to the browsers that accept it: a large map loads faster.
BUFFERS_GZIP_FILE = "map.bin.gz"
ITEMS_FILE = "items.sqlite"
VECTORS_FILE = "vectors.f16"
PROVENANCE_FILE = "provenance.json"

# Code of a point that has no value in a categorical column.
NO_VALUE = 0xFFFF
# Neighbour slot left empty.
NO_NEIGHBOUR = 0xFFFFFFFF

Dtype = Literal["float32", "float64", "uint8", "uint16", "uint32"]


class BufferSpec(BaseModel):
    """One typed array inside `map.bin`. `offset` is in bytes and a multiple of 8."""

    dtype: Dtype
    offset: int
    length: int  # number of elements, not bytes


class ColumnInfo(BaseModel):
    """A categorical attribute: one uint16 code per point indexing `names` (NO_VALUE for none)."""

    key: str
    label: str
    names: list[str]
    buffer: str


class ZoneInfo(BaseModel):
    """A cluster of the map. `named` is false while `name` is only its distinctive words."""

    id: int
    name: str
    words: list[str]
    size: int
    named: bool


class MapManifest(BaseModel):
    """Required buffers: `pos3` (float32, n*3), `pos2` (float32, n*2), `ts` (float64, n,
    milliseconds, 0 when undated), `neighbours` (uint32, n*k), and one buffer per column."""

    build: str
    built_at: str
    n: int
    k: int
    embedding_key: str
    dims: int
    time_min: int | None
    time_max: int | None
    columns: list[ColumnInfo]
    zones: list[ZoneInfo]
    buffers: dict[str, BufferSpec]
    # A workspace map grows: `version` changes with every point, layout, name or review, and
    # the buffers are fetched again. A build made offline keeps 0 and never changes.
    live: bool = False
    version: int = 0
    # Probes that can be read on this map (`GET map/scores/{key}`: one float32 per point,
    # NaN where the probe does not read the point). Filled by the server, not by the build.
    probes: list[ProbeInfo] = []


class PointReading(BaseModel):
    """What the probes and the review say of one point, for its card."""

    index: int
    # The probes that flagged the point, strongest first.
    probes: list[ProbeReading]
    # One score per probe shown, flagged or not.
    scores: dict[str, float]
    # Null on a map built offline: only workspace items are reviewed.
    review: Review | None

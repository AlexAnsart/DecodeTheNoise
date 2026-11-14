"""Lays typed arrays end to end for `map.bin` and codes categorical columns. Pure."""

from collections import Counter
from collections.abc import Sequence

import numpy as np

from backend.map.schema import NO_VALUE, BufferSpec

# A typed-array view in the browser needs an offset that is a multiple of its element size.
ALIGNMENT = 8
ACTOR_NAME_CHARS = 6


def pack_buffers(arrays: dict[str, np.ndarray]) -> tuple[bytes, dict[str, BufferSpec]]:
    """The concatenated little-endian bytes, and where each array sits in them."""
    blob = bytearray()
    specs: dict[str, BufferSpec] = {}
    for name, array in arrays.items():
        blob.extend(b"\0" * (-len(blob) % ALIGNMENT))
        data = np.ascontiguousarray(array).astype(array.dtype.newbyteorder("<"), copy=False)
        specs[name] = BufferSpec(dtype=str(array.dtype), offset=len(blob), length=int(array.size))
        blob.extend(data.tobytes())
    return bytes(blob), specs


def unpack_buffer(blob: bytes, spec: BufferSpec) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.dtype(spec.dtype), count=spec.length, offset=spec.offset)


def encode_column(values: Sequence[str | None]) -> tuple[np.ndarray, list[str]]:
    """One uint16 code per value and the names the codes index, most frequent name first."""
    counts = Counter(v for v in values if v is not None)
    names = sorted(counts, key=lambda name: (-counts[name], name))
    if len(names) >= NO_VALUE:
        raise ValueError(f"{len(names)} distinct values do not fit a uint16 column")
    code = {name: i for i, name in enumerate(names)}
    codes = np.fromiter((NO_VALUE if v is None else code[v] for v in values), np.uint16)
    return codes, names


def actor_names(actor_ids: Sequence[str]) -> dict[str, str]:
    """A short display name per actor id, lengthened only if two ids start the same."""
    distinct = sorted(set(actor_ids))
    chars = ACTOR_NAME_CHARS
    while len({a[:chars] for a in distinct}) < len(distinct):
        chars += 1
    return {a: f"acct-{a[:chars]}" for a in distinct}

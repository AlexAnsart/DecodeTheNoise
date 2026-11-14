"""The layouts of the build, read once from `map.bin` through the manifest's buffer specs.

The server needs them only to place a pasted text among its neighbours.
"""

from dataclasses import dataclass

import numpy as np

from backend.map.store import MapBuild


@dataclass(frozen=True)
class Coordinates:
    pos3: np.ndarray  # (n, 3) float32
    pos2: np.ndarray  # (n, 2) float32


def _read(build: MapBuild, name: str, width: int) -> np.ndarray:
    spec = build.manifest.buffers[name]
    flat = np.fromfile(
        build.buffers_path,
        dtype=np.dtype(spec.dtype).newbyteorder("<"),
        count=spec.length,
        offset=spec.offset,
    )
    return flat.reshape(build.manifest.n, width).astype(np.float32)


def load_coordinates(build: MapBuild) -> Coordinates:
    return Coordinates(pos3=_read(build, "pos3", 3), pos2=_read(build, "pos2", 2))

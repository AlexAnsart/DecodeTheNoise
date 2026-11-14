"""Assembles the folder the server loads: `map.json`, `map.bin`, `items.sqlite`, `vectors.f16`.

Run: uv run python -m pipelines.pack --name ira-3k [--current]
"""

import argparse
import json
import logging
from datetime import UTC, datetime

import numpy as np

from backend.map.schema import (
    BUFFERS_FILE,
    ITEMS_FILE,
    MANIFEST_FILE,
    VECTORS_FILE,
    ColumnInfo,
    MapManifest,
    ZoneInfo,
)
from pipelines import runlog
from pipelines.corpus import read_corpus
from pipelines.ingest.ira import Item
from pipelines.pack.buffers import actor_names, encode_column, pack_buffers
from pipelines.pack.items import write_items
from pipelines.pack.publish import CURRENT, publish_as_current
from pipelines.paths import (
    CORPUS_FILE,
    LAYOUT_FILE,
    NEIGHBOURS_FILE,
    ZONE_OF_POINT_FILE,
    ZONES_FILE,
    build_dir,
    work_dir,
)
from pipelines.vectors import read_vectors

log = logging.getLogger("pack")


def columns_of(
    items: list[Item], zones: list[ZoneInfo], zone_of_point: np.ndarray
) -> tuple[list[ColumnInfo], dict[str, np.ndarray]]:
    """The categorical columns in legend order, and one uint16 buffer of codes for each."""
    shown = actor_names([item.actor_id for item in items])
    coded = {
        "category": ("Account category", encode_column([item.category for item in items])),
        "actor": ("Account", encode_column([shown[item.actor_id] for item in items])),
        "post_type": ("Post type", encode_column([item.post_type for item in items])),
        "lang": ("Language", encode_column([item.lang for item in items])),
    }
    columns = [
        ColumnInfo(key="zone", label="Zone", names=[z.name for z in zones], buffer="col_zone")
    ]
    buffers = {"col_zone": zone_of_point.astype(np.uint16)}
    for key, (label, (codes, names)) in coded.items():
        columns.append(ColumnInfo(key=key, label=label, names=names, buffer=f"col_{key}"))
        buffers[f"col_{key}"] = codes
    return columns, buffers


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--current", action="store_true", help="also copy the build to 'current'")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    work, out = work_dir(args.name), build_dir(args.name)
    out.mkdir(parents=True, exist_ok=True)

    with runlog.timed() as elapsed:
        items = read_corpus(work / CORPUS_FILE)
        vectors, key = read_vectors(work)
        layout = np.load(work / LAYOUT_FILE)
        neighbours = np.load(work / NEIGHBOURS_FILE).astype(np.uint32)
        zones = [
            ZoneInfo.model_validate(z) for z in json.loads((work / ZONES_FILE).read_text("utf-8"))
        ]
        columns, column_buffers = columns_of(items, zones, np.load(work / ZONE_OF_POINT_FILE))
        ts = np.array([item.created_at or 0 for item in items], dtype=np.float64)
        blob, specs = pack_buffers(
            {
                "pos3": layout["pos3"].astype(np.float32),
                "pos2": layout["pos2"].astype(np.float32),
                "ts": ts,
                "neighbours": neighbours,
                **column_buffers,
            }
        )
        dated = ts[ts > 0]
        manifest = MapManifest(
            build=args.name,
            built_at=datetime.now(UTC).isoformat(timespec="seconds"),
            n=len(items),
            k=int(neighbours.shape[1]),
            embedding_key=key,
            dims=int(vectors.shape[1]),
            time_min=int(dated.min()) if len(dated) else None,
            time_max=int(dated.max()) if len(dated) else None,
            columns=columns,
            zones=zones,
            buffers=specs,
        )
        (out / BUFFERS_FILE).write_bytes(blob)
        (out / MANIFEST_FILE).write_text(manifest.model_dump_json(indent=1), encoding="utf-8")
        vectors.astype(np.float16).tofile(out / VECTORS_FILE)
        write_items(out / ITEMS_FILE, items)
    runlog.record("pack", args.name, len(items), elapsed[0])
    log.info("packed %d points into %s (%.1f MB of buffers)", len(items), out, len(blob) / 1e6)
    if args.current:
        publish_as_current(out)
        log.info("'%s' now holds %s", CURRENT, args.name)


if __name__ == "__main__":
    main()

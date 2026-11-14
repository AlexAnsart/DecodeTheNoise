"""A workspace as a map build: the manifest and the buffers the demo serves from files, made
from memory. Kept until the workspace changes."""

from datetime import UTC, datetime

import numpy as np

from backend.map.schema import NO_VALUE, ColumnInfo, MapManifest
from backend.map.store import MapBuild
from backend.workspace.state import Workspace
from pipelines.pack.buffers import encode_column, pack_buffers

# Versions of a map kept for readers that are between the manifest and the buffers.
KEPT_BUILDS = 4
# Categorical columns of a workspace map, in legend order, after the zone.
_COLUMNS = (("actor", "Actor"), ("kind", "Post type"), ("lang", "Language"), ("source", "Source"))


def _columns(workspace: Workspace, n: int) -> tuple[list[ColumnInfo], dict[str, np.ndarray]]:
    with workspace.db_lock:
        rows = workspace.db.execute(
            "SELECT coalesce(actor_name, actor_id), kind, lang, source FROM items "
            "WHERE idx IS NOT NULL ORDER BY idx"
        ).fetchall()[:n]
    sizes = np.bincount(
        workspace.zone[:n][workspace.zone[:n] != NO_VALUE], minlength=len(workspace.zones)
    )
    workspace.zones = tuple(
        zone.model_copy(update={"size": int(sizes[zone.id])}) for zone in workspace.zones
    )
    names = [zone.name for zone in workspace.zones]
    columns = [ColumnInfo(key="zone", label="Zone", names=names, buffer="col_zone")]
    buffers = {"col_zone": workspace.zone[:n]}
    for position, (key, label) in enumerate(_COLUMNS):
        codes, values = encode_column([row[position] for row in rows])
        # A column nobody filled would only add an empty entry to the menus.
        if values:
            columns.append(ColumnInfo(key=key, label=label, names=values, buffer=f"col_{key}"))
            buffers[f"col_{key}"] = codes
    return columns, buffers


def build_of(workspace: Workspace) -> MapBuild:
    with workspace.lock:
        cached = workspace.cached_build
        if cached is not None and cached.manifest.version == workspace.version:
            return cached
        n = workspace.n
        columns, column_buffers = _columns(workspace, n)
        ts = workspace.ts[:n]
        blob, specs = pack_buffers(
            {
                "pos3": workspace.pos3[:n],
                "pos2": workspace.pos2[:n],
                "ts": ts,
                "neighbours": workspace.knn.index[:n],
                **column_buffers,
            }
        )
        dated = ts[ts > 0]
        manifest = MapManifest(
            build=workspace.id,
            built_at=datetime.now(UTC).isoformat(timespec="seconds"),
            n=n,
            k=workspace.knn.k,
            embedding_key=workspace.embedding_key,
            dims=workspace.dims,
            time_min=int(dated.min()) if len(dated) else None,
            time_max=int(dated.max()) if len(dated) else None,
            columns=columns,
            zones=list(workspace.zones),
            buffers=specs,
            live=True,
            version=workspace.version,
        )
        build = MapBuild(
            folder=workspace.folder,
            manifest=manifest,
            vectors=workspace.vectors[:n],
            items=workspace.db,
            items_lock=workspace.db_lock,
            blob=blob,
            pos3=workspace.pos3[:n].copy(),
            pos2=workspace.pos2[:n].copy(),
        )
        workspace.cached_build = build
        workspace.recent_builds[manifest.version] = build
        for version in list(workspace.recent_builds)[:-KEPT_BUILDS]:
            del workspace.recent_builds[version]
        return build


def build_at(workspace: Workspace, version: int) -> MapBuild | None:
    """The map as it was served at `version`, while it is still kept."""
    with workspace.lock:
        return workspace.recent_builds.get(version)

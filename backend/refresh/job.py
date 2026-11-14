"""Refreshes a workspace: lays its points out again and clusters them into zones; the new
zones are then named by another job. Between two refreshes a new point only sits beside its
neighbours."""

import logging
import time

from backend.refresh.layout import lay_out
from backend.refresh.naming import current_layout
from backend.refresh.zones import make_zones
from backend.services import Services
from backend.workspace.files import Layout, save_layout
from backend.workspace.state import FIRST_REFRESH, Workspace

logger = logging.getLogger(__name__)


def _compute(services: Services, workspace: Workspace) -> tuple[int, Layout] | None:
    """The new layout of the points there are now, computed outside the lock: the zones
    here (a fraction of a second), the two layouts in the computing process."""
    with workspace.lock:
        n, epoch = workspace.n, workspace.epoch
        if n < FIRST_REFRESH:
            return None
        vectors = workspace.vectors[:n].copy()
        laid_out = epoch > 0
        previous3 = workspace.pos3[:n].copy() if laid_out else None
        previous2 = workspace.pos2[:n].copy() if laid_out else None
        zones, centres = workspace.zones, workspace.centres
        with workspace.db_lock:
            texts = [
                row[0]
                for row in workspace.db.execute(
                    "SELECT text FROM items WHERE idx IS NOT NULL AND idx < ? ORDER BY idx", (n,)
                )
            ]
    zoning = make_zones(vectors, texts, zones, centres)
    layout = Layout(
        epoch=epoch + 1,
        pos3=services.computing.run(lay_out, vectors, 3, previous3),
        pos2=services.computing.run(lay_out, vectors, 2, previous2),
        zone=zoning.zone,
        centres=zoning.centres,
        zones=zoning.zones,
    )
    return epoch, layout


def refresh_workspace(services: Services, workspace_id: str) -> None:
    workspace = services.workspaces.get(workspace_id)
    if workspace is None:
        return
    with workspace.lock:
        workspace.refresh_queued = False
        workspace.refreshing = True
    services.hub.publish(workspace.id, services.describe(workspace).model_dump_json())
    started = time.monotonic()
    try:
        computed = _compute(services, workspace)
        if computed is not None:
            epoch, layout = computed
            with workspace.lock:
                # Emptied while the layout was computed: the result describes points that
                # are gone.
                if workspace.epoch == epoch and workspace.n >= len(layout.pos3):
                    workspace.apply_layout(layout)
                    save_layout(workspace.folder, current_layout(workspace))
                    workspace.touch()
                    logger.info(
                        "workspace %s: epoch %d, %d points, %d zones in %.1fs",
                        workspace.id,
                        layout.epoch,
                        len(layout.pos3),
                        len(layout.zones),
                        time.monotonic() - started,
                    )
    finally:
        with workspace.lock:
            workspace.refreshing = False
    services.changed(workspace)
    # Naming waits on the LLM: it has its own thread, so the next refresh is not held back.
    if services.jobs is not None:
        services.jobs.names.submit(workspace.id)

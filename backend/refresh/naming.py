"""Names the zones of a workspace that have none yet, one LLM call per zone, each name shown
as soon as it comes. Runs after a refresh, in a thread of its own."""

import logging

import httpx
import numpy as np

from backend.accounts.limits import ALL_WORKSPACES, GLOBAL_NAMES_PER_DAY, NAMES, NAMES_PER_DAY
from backend.ingest.rows import rows_at
from backend.services import Services
from backend.workspace.files import Layout, save_layout
from backend.workspace.state import Workspace
from pipelines.zones.naming import SAMPLES_PER_ZONE, name_zone, representative, tell_apart

logger = logging.getLogger(__name__)

# A zone of one or two posts is an odd post, not a subject: it keeps its words.
MIN_NAMED_SIZE = 3


def current_layout(workspace: Workspace) -> Layout:
    covered = workspace.points_covered
    centres = workspace.centres
    return Layout(
        epoch=workspace.epoch,
        pos3=workspace.pos3[:covered].copy(),
        pos2=workspace.pos2[:covered].copy(),
        zone=workspace.zone[:covered].copy(),
        centres=centres if centres is not None else np.zeros((0, workspace.dims), np.float32),
        zones=workspace.zones,
    )


def _within_budget(services: Services, workspace: Workspace) -> bool:
    accounts = services.accounts
    return (
        accounts.used_today(workspace.id, NAMES) < NAMES_PER_DAY
        and accounts.used_today(ALL_WORKSPACES, NAMES) < GLOBAL_NAMES_PER_DAY
    )


def _samples(workspace: Workspace, zone_id: int) -> list[str]:
    """The texts that say the zone best: the nearest to its mean direction."""
    with workspace.lock:
        n = workspace.n
        members = np.flatnonzero(workspace.zone[:n] == zone_id)
        if len(members) == 0:
            return []
        chosen = representative(workspace.vectors[:n], members, SAMPLES_PER_ZONE)
        with workspace.db_lock:
            rows = rows_at(workspace.db, chosen)
    return [rows[index].text for index in chosen if index in rows]


def _apply(workspace: Workspace, epoch: int, zone_id: int, name: str) -> bool:
    """Gives the zone its name, unless another refresh replaced the zones meanwhile."""
    with workspace.lock:
        if workspace.epoch != epoch or zone_id >= len(workspace.zones):
            return False
        zones = list(workspace.zones)
        zones[zone_id] = zones[zone_id].model_copy(update={"name": name, "named": True})
        # Two zones can receive the same name: the later one adds a word of its own.
        labels = tell_apart([zone.name for zone in zones], [zone.words for zone in zones])
        workspace.zones = tuple(
            zone.model_copy(update={"name": label}) if zone.named else zone
            for zone, label in zip(zones, labels, strict=True)
        )
        save_layout(workspace.folder, current_layout(workspace))
        workspace.touch()
        return True


def name_zones(services: Services, workspace_id: str) -> None:
    chat = services.chat
    workspace = services.workspaces.get(workspace_id)
    if chat is None or workspace is None:
        return
    with workspace.lock:
        epoch = workspace.epoch
        waiting = [
            zone for zone in workspace.zones if not zone.named and zone.size >= MIN_NAMED_SIZE
        ]
    for zone in waiting:
        if not _within_budget(services, workspace):
            logger.info("workspace %s: the daily naming budget is used", workspace.id)
            return
        samples = _samples(workspace, zone.id)
        if not samples:
            continue
        try:
            name = name_zone(chat, services.llm_model, services.name_cache, zone.words, samples)
        except httpx.HTTPError as error:
            # The zone keeps its words; the next refresh asks again.
            logger.warning("zone %d of %s was not named: %s", zone.id, workspace.id, error)
            return
        services.accounts.use(workspace.id, NAMES)
        services.accounts.use(ALL_WORKSPACES, NAMES)
        if name is None:
            continue
        if not _apply(workspace, epoch, zone.id, name):
            return
        services.changed(workspace)

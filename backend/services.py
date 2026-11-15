"""What the workspace features share: the stores, the models, the probes, the background jobs.

Built once at start-up and handed to the routes and the jobs; nothing here is a global.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from backend.accounts.limits import NAMES, REVIEWS
from backend.accounts.store import AccountStore
from backend.events.hub import Hub
from backend.ingest.embedder import CHUNK, EmbeddingModel, ItemEmbedder
from backend.ingest.schema import Counts
from backend.probes.pack import Probes
from backend.refresh.computing import Computing
from backend.review.cache import REVIEWS_FILE, ReviewCache
from backend.review.engine import Reviewer
from backend.review.guides import NO_GUIDES, Guides
from backend.review.measures import NO_MEASURES, Measures
from backend.workspace.registry import Workspaces
from backend.workspace.schema import IngestState, RefreshState, Usage, WorkspaceInfo
from backend.workspace.state import Workspace
from pipelines.zones.naming import CachedName

if TYPE_CHECKING:
    from backend.jobs.workers import Jobs

ACCOUNTS_FILE = "accounts.sqlite"
EMBEDDINGS_FILE = "embeddings.sqlite"


class Chat(Protocol):
    """The LLM, as the zone naming and the review use it."""

    def complete(self, system: str, user: str) -> str: ...


def counts_of(workspace: Workspace) -> Counts:
    return Counts(
        items=workspace.items,
        points=workspace.n,
        pending=workspace.pending,
        limit=workspace.limits.items,
        next_refresh_at=workspace.next_refresh_at(),
    )


@dataclass
class Services:
    accounts: AccountStore
    workspaces: Workspaces
    embedder: ItemEmbedder
    probes: Probes
    hub: Hub
    # None when no LLM is configured: zones keep their words and nothing is reviewed.
    chat: Chat | None
    llm_model: str
    # Where layouts are computed: another process, so that the requests never wait for one.
    computing: Computing
    # The LLM review: its guides, what its readings measured to be worth, the reviews kept.
    reviewer: Reviewer
    jobs: Jobs | None = None
    # Zone names already asked, by a hash of the question: the same question is never paid twice.
    name_cache: dict[str, CachedName] = field(default_factory=dict)

    def ingest_state(self, workspace: Workspace, others: list[Workspace]) -> IngestState:
        """The time left is what is ahead at the speed the model was measured at on this
        server. The jobs take turns, one chunk each: while this workspace works through its
        own posts, each other workspace that waits gets as many chunks."""
        pending, rate = workspace.pending, self.embedder.rate
        turns = math.ceil(pending / CHUNK) * CHUNK
        ahead = sum(min(other.pending, turns) for other in others if other.id != workspace.id)
        return IngestState(
            batch=workspace.batch_total,
            ahead=ahead,
            rate=round(rate, 2) if rate else None,
            eta_seconds=math.ceil((pending + ahead) / rate) if pending and rate else None,
            error=workspace.ingest_error,
        )

    def describe(self, workspace: Workspace) -> WorkspaceInfo:
        others = self.workspaces.loaded()
        with workspace.lock:
            return WorkspaceInfo(
                id=workspace.id,
                created_at=workspace.created_at,
                version=workspace.version,
                items=workspace.items,
                points=workspace.n,
                pending=workspace.pending,
                actors=len(workspace.actors.ids),
                zones=len(workspace.zones),
                limits=workspace.limits,
                usage=Usage(
                    reviews_today=self.accounts.used_today(workspace.id, REVIEWS),
                    names_today=self.accounts.used_today(workspace.id, NAMES),
                ),
                ingest=self.ingest_state(workspace, others),
                refresh=RefreshState(
                    epoch=workspace.epoch,
                    points_covered=workspace.points_covered,
                    next_at=workspace.next_refresh_at(),
                    running=workspace.refreshing,
                ),
                settings=workspace.settings,
                probes=list(self.probes.shown()),
                embedding_key=workspace.embedding_key,
            )

    def changed(self, workspace: Workspace) -> None:
        """Tells whoever watches the workspace, and starts a refresh when one is due."""
        self.hub.publish(workspace.id, self.describe(workspace).model_dump_json())
        with workspace.lock:
            due = workspace.refresh_due() and not workspace.refresh_queued
            if due:
                workspace.refresh_queued = True
        if due and self.jobs is not None:
            self.jobs.refresh.submit(workspace.id)


def start_services(
    root: Path,
    model: EmbeddingModel,
    dims: int,
    probes: Probes,
    chat: Chat | None,
    llm_model: str,
    computing: Computing,
    guides: Guides = NO_GUIDES,
    measures: Measures = NO_MEASURES,
) -> Services:
    """Opens the stores under `root` and starts the background jobs."""
    from backend.ingest.background import resume
    from backend.jobs.workers import Jobs

    accounts = AccountStore(root / ACCOUNTS_FILE)
    embedder = ItemEmbedder(model, root / EMBEDDINGS_FILE)
    services = Services(
        accounts=accounts,
        workspaces=Workspaces(root, accounts, embedder.key, dims),
        embedder=embedder,
        probes=probes,
        hub=Hub(),
        chat=chat,
        llm_model=llm_model,
        computing=computing,
        reviewer=Reviewer(chat, llm_model, guides, measures, ReviewCache(root / REVIEWS_FILE)),
    )
    services.jobs = Jobs(services)
    services.workspaces.on_load = lambda workspace: resume(services, workspace)
    return services


def stop_services(services: Services) -> None:
    if services.jobs is not None:
        services.jobs.stop()
    services.computing.close()
    services.reviewer.cache.close()
    services.workspaces.close()
    services.embedder.close()
    services.accounts.close()

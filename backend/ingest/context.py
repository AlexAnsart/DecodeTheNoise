"""What the rest of a workspace says about one item: where it lands, what resembles it, who
writes alike. Measures only: nothing here is a verdict.

Expected cost: one product of the workspace's vectors by the item's, a partial sort, and one
database read for the few neighbours shown. The caller holds the workspace's lock.
"""

import numpy as np

from backend.analyze.place import neighbour_weights, strongest
from backend.ingest.overlap import word_overlap
from backend.ingest.rows import rows_at, to_datetime
from backend.ingest.schema import (
    EXCERPT_CHARS,
    MIN_ACTOR_ITEMS,
    SAME_STATEMENT_SIMILARITY,
    SIMILAR_ACTORS,
    ActorContext,
    ItemContext,
    NeighbourOut,
    SameStatement,
    SimilarActor,
    ZoneRef,
)
from backend.map.schema import NO_VALUE
from backend.workspace.state import NO_ACTOR, Workspace


def _neighbours(
    workspace: Workspace, text: str, order: np.ndarray, top: np.ndarray
) -> list[NeighbourOut]:
    with workspace.db_lock:
        rows = rows_at(workspace.db, [int(i) for i in order])
    out = []
    for index, similarity in zip(order.tolist(), top.tolist(), strict=True):
        row = rows.get(index)
        if row is None:
            continue
        out.append(
            NeighbourOut(
                id=row.item_id,
                index=index,
                actor_id=row.actor_id,
                created_at=to_datetime(row.created_at),
                similarity=round(float(similarity), 4),
                word_overlap=round(word_overlap(text, row.text), 4),
                excerpt=" ".join(row.text.split())[:EXCERPT_CHARS],
            )
        )
    return out


def _same_statement(workspace: Workspace, scores: np.ndarray, own_actor: int) -> SameStatement:
    close = scores >= SAME_STATEMENT_SIMILARITY
    actors = np.unique(workspace.actor_row[: len(scores)][close])
    dated = workspace.ts[: len(scores)][close]
    dated = dated[dated > 0]
    return SameStatement(
        min_similarity=SAME_STATEMENT_SIMILARITY,
        items=int(close.sum()),
        actors=int(np.count_nonzero((actors != NO_ACTOR) & (actors != own_actor))),
        first=to_datetime(float(dated.min())) if len(dated) else None,
        last=to_datetime(float(dated.max())) if len(dated) else None,
    )


def _zone(workspace: Workspace, code: int) -> ZoneRef | None:
    if code == NO_VALUE or code >= len(workspace.zones):
        return None
    zone = workspace.zones[code]
    share = float(np.count_nonzero(workspace.zone[: workspace.n] == code)) / max(workspace.n, 1)
    return ZoneRef(
        id=zone.id, name=zone.name, named=zone.named, words=zone.words, share=round(share, 4)
    )


def _actor(workspace: Workspace, actor_id: str | None) -> ActorContext | None:
    row = workspace.actors.rows.get(actor_id) if actor_id else None
    if actor_id is None or row is None:
        return None
    actors = workspace.actors
    items = int(actors.counts[row])
    similar = actors.similar(row, SIMILAR_ACTORS, MIN_ACTOR_ITEMS)
    return ActorContext(
        id=actor_id,
        items=items,
        first_seen=to_datetime(float(actors.first[row])),
        last_seen=to_datetime(float(actors.last[row])),
        similar_actors=[
            SimilarActor(id=other, similarity=round(score, 4), items=count)
            for other, score, count in similar
        ],
        reason=(
            f"Under {MIN_ACTOR_ITEMS} items: not enough evidence to compare this actor."
            if items < MIN_ACTOR_ITEMS
            else None
        ),
    )


def context_of(
    workspace: Workspace,
    vector: np.ndarray,
    text: str,
    index: int | None,
    actor_id: str | None,
    neighbours: int,
) -> ItemContext:
    """`index` is the item's own point, or None for a text that is not stored."""
    n = workspace.n
    scores = workspace.vectors[:n] @ vector
    if index is not None:
        scores[index] = -np.inf
    order, top = strongest(scores, max(neighbours, workspace.knn.k))
    if index is not None:
        position, code = workspace.pos3[index], int(workspace.zone[index])
    elif len(order):
        position = neighbour_weights(top) @ workspace.pos3[order]
        centres = workspace.centres
        code = int(np.argmax(centres @ vector)) if centres is not None else NO_VALUE
    else:
        position, code = np.zeros(3, dtype=np.float32), NO_VALUE
    own_actor = workspace.actors.rows.get(actor_id, NO_ACTOR) if actor_id else NO_ACTOR
    return ItemContext(
        position=(float(position[0]), float(position[1]), float(position[2])),
        zone=_zone(workspace, code),
        neighbours=_neighbours(workspace, text, order[:neighbours], top[:neighbours]),
        same_statement=_same_statement(workspace, scores, own_actor),
        actor=_actor(workspace, actor_id),
    )

"""The groups the interchangeable-actors test is run on, one loader per arm.

- `organic`: real actors of the 2026 sample that posted on one subject in one month.
- `organic-alike`: in each of those pools, the actors that resemble each other most.
- `shared`, `solo`, `persona`: synthetic twins of those subjects, one per way of running accounts.
- `ira-*`: accounts of one IRA team in one zone of the map in one month. Humans under a brief.
- `ira-RightTroll-untagged`: the same groups, read without their hashtags and links.
"""

import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from pipelines.briefs.bench import POOLS_EXTRA_FILE, POOLS_FILE, POSTS_FILE, read_jsonl
from pipelines.briefs.interchange import style_features
from pipelines.briefs.vectors import embed, served_key
from pipelines.paths import CORPUS_FILE, ZONE_OF_POINT_FILE, work_dir
from pipelines.vectors import read_vectors

IRA_BUILD = "ira-120k"
IRA_TEAMS = ("RightTroll", "NewsFeed")
UNTAGGED_TEAM = "RightTroll"
_TAG_OR_LINK = re.compile(r"#\w+|https?://\S+")
MIN_POSTS = 6
MIN_ACTORS = 6


@dataclass(frozen=True)
class Group:
    arm: str
    name: str
    actors: np.ndarray  # who wrote each post
    vectors: np.ndarray  # unit vectors, one row per post
    style: np.ndarray  # surface features, one row per post, not yet standardised
    texts: tuple[str, ...] = ()


def _group(arm: str, name: str, rows: list[tuple[str, str]], vectors: np.ndarray) -> Group:
    return Group(
        arm=arm,
        name=name,
        actors=np.array([actor for actor, _ in rows]),
        vectors=vectors,
        style=np.array([style_features(text) for _, text in rows]),
        texts=tuple(text for _, text in rows),
    )


def _embedded(arm_of: dict[str, str], rows: dict[str, list[tuple[str, str]]]) -> list[Group]:
    """One embedding call for every post of these groups, then one Group per name."""
    names = sorted(rows)
    vectors, _ = embed([text for name in names for _, text in rows[name]])
    groups, start = [], 0
    for name in names:
        stop = start + len(rows[name])
        groups.append(_group(arm_of[name], name, rows[name], vectors[start:stop]))
        start = stop
    return groups


def organic_groups() -> list[Group]:
    """Every real pool: those the synthetic subjects come from, and the extra ones."""
    rows: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for path in (POOLS_FILE, POOLS_EXTRA_FILE):
        for row in read_jsonl(path):
            rows[str(row["pool"])].append((str(row["actor"]), str(row["text"])))
    return _embedded(dict.fromkeys(rows, "organic"), rows)


def most_alike(group: Group, actors: int = MIN_ACTORS) -> Group:
    """The actors whose mean vectors sit closest to the group's: the hardest real negatives."""
    names = np.unique(group.actors)
    centre = group.vectors.mean(axis=0)
    means = np.stack([group.vectors[group.actors == name].mean(axis=0) for name in names])
    closeness = (means @ centre) / np.linalg.norm(means, axis=1)
    keep = np.isin(group.actors, names[np.argsort(closeness)[-actors:]])
    texts = tuple(text for text, kept in zip(group.texts, keep, strict=True) if kept)
    return Group(
        "organic-alike",
        group.name,
        group.actors[keep],
        group.vectors[keep],
        group.style[keep],
        texts,
    )


def twin_groups() -> list[Group]:
    rows: dict[str, list[tuple[str, str]]] = defaultdict(list)
    arm_of: dict[str, str] = {}
    for row in read_jsonl(POSTS_FILE):
        if row["set"] == "twin":
            name = f"{row['topic']}-{row['mode']}"
            rows[name].append((str(row["actor"]), str(row["text"])))
            arm_of[name] = str(row["mode"])
    return _embedded(arm_of, rows)


def ira_groups(work: Path | None = None) -> list[Group]:
    """Own English posts of one team, one zone, one month; groups too small are left out."""
    work = work or work_dir(IRA_BUILD)
    zone = np.load(work / ZONE_OF_POINT_FILE)
    vectors, key = read_vectors(work)
    if key != str(served_key()):
        raise ValueError(f"{IRA_BUILD} holds vectors of {key}, not of {served_key()}")
    con = sqlite3.connect(f"file:{(work / CORPUS_FILE).as_posix()}?mode=ro", uri=True)
    query = (
        "select idx, actor_id, category, created_at, text from items "
        "where post_type != 'repost' and lang = 'English' and created_at is not null"
    )
    members: dict[tuple[str, int, str], list[tuple[int, str, str]]] = defaultdict(list)
    for idx, actor, team, created_at, text in con.execute(query):
        if team in IRA_TEAMS:
            month = datetime.fromtimestamp(created_at / 1000, UTC).strftime("%Y-%m")
            members[(team, int(zone[idx]), month)].append((idx, actor, text))
    con.close()
    groups = []
    untagged: dict[str, list[tuple[str, str]]] = {}
    for (team, zone_id, month), posts in sorted(members.items()):
        counts = defaultdict(int)
        for _, actor, _ in posts:
            counts[actor] += 1
        kept = [p for p in posts if counts[p[1]] >= MIN_POSTS]
        if len({actor for _, actor, _ in kept}) >= MIN_ACTORS:
            rows = [(actor, text) for _, actor, text in kept]
            name = f"{team}-z{zone_id}-{month}"
            groups.append(_group(f"ira-{team}", name, rows, vectors[[idx for idx, _, _ in kept]]))
            if team == UNTAGGED_TEAM:
                untagged[name] = [(actor, without_tags(text)) for actor, text in rows]
    # The same groups with hashtags and links removed: does a per-account tag carry the gap?
    arm = f"ira-{UNTAGGED_TEAM}-untagged"
    return [*groups, *_embedded(dict.fromkeys(untagged, arm), untagged)]


def without_tags(text: str) -> str:
    return " ".join(_TAG_OR_LINK.sub(" ", text).split())

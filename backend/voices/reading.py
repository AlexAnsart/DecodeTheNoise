"""Reads a selection of the map: do its actors speak with one voice?

Three answers, never two: `one voice` (a level, "possible"), `separate voices`, and
`not enough evidence` when too few actors have enough posts, or when the check was not measured
for this map's embedding model.
"""

import hashlib
import json
from dataclasses import dataclass

import numpy as np

from backend.map.store import MapBuild
from backend.voices.calibration import REPORT, Calibration, SizeCalibration
from backend.voices.schema import (
    Authorship,
    GroupSize,
    Pair,
    PairSide,
    Read,
    ReferenceRanges,
    Reliability,
    Selection,
    VoicesAnswer,
)
from backend.voices.score import DRAWS, SIZES, cosine, eligible, measured_size, read_voices

_VARIABLES = 500
_ENGLISH = ("en", "english")
PAIRS = 3
# Posts compared to find the closest pairs: enough to show evidence, bounded in memory.
PAIR_POSTS = 300
PAIR_TEXT_CHARS = 400
OTHER_LANGUAGE_SHARE = 0.2


@dataclass(frozen=True)
class OwnPost:
    index: int
    actor: str
    text: str
    lang: str | None


def own_posts(build: MapBuild, indices: list[int]) -> list[OwnPost]:
    """The posts of the selection an actor wrote: no repost, no item without an actor."""
    # Only a workspace stores the kind of a post in a column; the demo keeps it in `attrs`.
    kind = "kind" if build.manifest.live else "NULL"
    posts: list[OwnPost] = []
    with build.items_lock:
        for start in range(0, len(indices), _VARIABLES):
            part = indices[start : start + _VARIABLES]
            marks = ",".join("?" * len(part))
            query = (
                f"SELECT idx, actor_id, text, lang, repost_of, attrs, {kind} FROM items "
                f"WHERE idx IN ({marks})"
            )
            for index, actor, text, lang, repost_of, attrs, post_kind in build.items.execute(
                query, part
            ):
                repost = repost_of or "repost" in (post_kind, json.loads(attrs).get("post_type"))
                if actor and not repost:
                    posts.append(OwnPost(index, actor, text, lang))
    return sorted(posts, key=lambda post: post.index)


def closest_pairs(
    posts: list[OwnPost], vectors: np.ndarray, rng: np.random.Generator
) -> list[Pair]:
    """The posts by different actors that say the most alike: what "one voice" rests on."""
    rows = np.arange(len(posts))
    if len(rows) > PAIR_POSTS:
        rows = np.sort(rng.choice(rows, PAIR_POSTS, replace=False))
    actors = np.array([posts[i].actor for i in rows])
    similarity = np.triu(cosine(vectors[rows]), k=1)
    similarity[actors[:, None] == actors[None, :]] = 0.0
    labels: dict[str, str] = {}
    used: set[int] = set()
    pairs: list[Pair] = []
    for flat in np.argsort(similarity, axis=None)[::-1]:
        a, b = divmod(int(flat), len(rows))
        if len(pairs) == PAIRS or similarity[a, b] <= 0:
            break
        if a in used or b in used:
            continue
        used.update((a, b))
        sides = []
        for row in (a, b):
            post = posts[rows[row]]
            label = labels.setdefault(post.actor, f"Actor {chr(ord('A') + len(labels))}")
            sides.append(PairSide(index=post.index, actor=label, text=post.text[:PAIR_TEXT_CHARS]))
        pairs.append(Pair(similarity=round(float(similarity[a, b]), 3), a=sides[0], b=sides[1]))
    return pairs


def _reliability(size: SizeCalibration) -> Reliability:
    return Reliability(
        false_alarms=size.real.flagged,
        real_groups=size.real.groups,
        hard_false_alarms=size.real_alike.flagged,
        hard_real_groups=size.real_alike.groups,
        caught=size.one_brief.flagged,
        one_brief_groups=size.one_brief.groups,
        report=REPORT,
    )


def _caveats(posts: list[OwnPost]) -> list[str]:
    known = [post.lang.lower() for post in posts if post.lang]
    other = sum(lang not in _ENGLISH for lang in known)
    if known and other / len(known) > OTHER_LANGUAGE_SHARE:
        return [
            f"The check was measured on English posts; {other / len(known):.0%} of these posts "
            "are marked as another language."
        ]
    return []


def read_selection(
    build: MapBuild, calibration: Calibration | None, indices: list[int]
) -> VoicesAnswer:
    posts = own_posts(build, indices)
    actors = np.array([post.actor for post in posts])
    selection = Selection(items=len(posts), actors=len(set(actors.tolist())))
    needed = GroupSize(actors=SIZES[-1][0], posts_each=SIZES[-1][1])

    def not_enough(reason: str) -> VoicesAnswer:
        return VoicesAnswer(
            outcome="not enough evidence", reason=reason, selection=selection, needed=needed
        )

    if calibration is None:
        return not_enough("This check has no measured threshold on this server: it stays off.")
    if calibration.embedding_key != build.manifest.embedding_key:
        return not_enough(
            "This check was measured with another embedding model than this map's: it stays off."
        )
    size = measured_size(actors) if len(actors) else None
    measured = calibration.at(size) if size else None
    if size is None or measured is None:
        enough = len(eligible(actors, needed.posts_each)) if len(actors) else 0
        return not_enough(
            f"This check needs at least {needed.actors} actors with {needed.posts_each} posts "
            f"each. This selection has {enough} such actor{'' if enough == 1 else 's'}, among "
            f"{selection.actors} actor{'' if selection.actors == 1 else 's'} and "
            f"{selection.items} post{'' if selection.items == 1 else 's'} of their own."
        )

    # The same selection always gives the same answer.
    digest = hashlib.sha256(",".join(map(str, sorted(indices))).encode("ascii")).hexdigest()
    rng = np.random.default_rng(int(digest[:16], 16))
    vectors = build.vectors[[post.index for post in posts]]
    voices = read_voices(vectors, actors, size, rng)
    if voices is None:  # cannot happen once a size was found; kept for the type
        return not_enough("Too few actors have enough posts.")
    one_voice = voices.score < measured.threshold
    able = np.isin(actors, eligible(actors, size[1]))
    able_posts = [post for post, keep in zip(posts, able, strict=True) if keep]
    return VoicesAnswer(
        outcome="one voice" if one_voice else "separate voices",
        confidence="possible" if one_voice else None,
        selection=selection,
        needed=needed,
        read=Read(
            actors=voices.actors,
            posts_each=voices.posts_each,
            eligible_actors=voices.eligible_actors,
            draws=DRAWS,
        ),
        score=round(voices.score, 2),
        threshold=measured.threshold,
        authorship=Authorship(found=round(voices.attribution, 3), chance=round(1 / size[0], 3)),
        reference=ReferenceRanges(
            independent=measured.reference.independent, one_brief=measured.reference.one_brief
        ),
        reliability=_reliability(measured),
        pairs=closest_pairs(able_posts, vectors[able], rng) if one_voice else [],
        caveats=_caveats(able_posts),
    )

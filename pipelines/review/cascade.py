"""The cascade on the technique labels that have a probe: the probe flags, the review reads.

Three numbers per probe: the precision after the probe, the precision after the review, and
the share of the probe's true positives the review keeps.
"""

from collections.abc import Collection, Mapping, Sequence

import numpy as np
from pydantic import BaseModel

from backend.probes.pack import Probes
from backend.probes.schema import ProbeInfo
from pipelines.review.counts import Rate, wilson


class CascadeMeasure(BaseModel):
    # Test posts with a settled answer that the probe flags, and those of them annotated yes.
    flagged: int
    flagged_yes: int
    after_probe: Rate | None
    # The flagged posts the review read (a uniform draw of them), and those annotated yes.
    read: int
    read_yes: int
    # Of the posts read, those the review answered "supported".
    kept: int
    kept_yes: int
    after_review: Rate | None
    true_positives_kept: Rate | None
    # On the same posts, what the screen names when no probe is listed.
    screen_kept_yes: int
    true_positives_screen_names: Rate | None


def flagging(
    probes: Probes, vectors: np.ndarray, keys: Sequence[str], techniques: Collection[str]
) -> dict[str, tuple[ProbeInfo, ...]]:
    """For each post a technique probe flags, those probes, strongest first: what the product
    lists when it sends the post to the review."""
    scores = probes.scores(vectors)
    flags = probes.flags(scores)
    columns = [column for column, info in enumerate(probes.infos) if info.key in techniques]
    found: dict[str, tuple[ProbeInfo, ...]] = {}
    for row, key in enumerate(keys):
        hits = sorted((c for c in columns if flags[row, c]), key=lambda c: -scores[row, c])
        if hits:
            found[key] = tuple(probes.infos[c] for c in hits)
    return found


def cascade_measure(
    flagged: Mapping[str, bool], supported: Mapping[str, bool], screened: Mapping[str, bool]
) -> CascadeMeasure:
    """`flagged`: the posts the probe flags, true when annotated yes. `supported`: those of
    them the review read, true when it answered "supported". `screened`: the same posts,
    true when the screen named the technique without the probe listed."""
    read = {post: flagged[post] for post in supported}
    kept = [post for post, answer in supported.items() if answer]
    flagged_yes, read_yes = sum(flagged.values()), sum(read.values())
    kept_yes = sum(read[post] for post in kept)
    screen_kept_yes = sum(read[post] for post in supported if screened[post])
    return CascadeMeasure(
        flagged=len(flagged),
        flagged_yes=flagged_yes,
        after_probe=wilson(flagged_yes, len(flagged)),
        read=len(read),
        read_yes=read_yes,
        kept=len(kept),
        kept_yes=kept_yes,
        after_review=wilson(kept_yes, len(kept)),
        true_positives_kept=wilson(kept_yes, read_yes),
        screen_kept_yes=screen_kept_yes,
        true_positives_screen_names=wilson(screen_kept_yes, read_yes),
    )

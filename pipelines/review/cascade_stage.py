"""The cascade stage of the evaluation: reads the posts the technique probes flag, with those
probes listed, and measures each probe followed by the review."""

from collections.abc import Callable, Mapping

from backend.probes.pack import load_probes
from backend.probes.schema import PACK_FILE, ProbePack
from backend.review.prompt import ReviewRequest
from backend.settings import get_settings
from pipelines.review.ask import Reading
from pipelines.review.cascade import cascade_measure, flagging
from pipelines.review.counts import wilson
from pipelines.review.draw import draw
from pipelines.review.metrics import UNTESTED, Cascade
from pipelines.review.testset import Post, post_vectors

# Flagged posts read with their probes listed: what the budget leaves, with room for retries.
CASCADE_POSTS = 80

Ask = Callable[[Mapping[str, ReviewRequest], int], dict[str, Reading]]


def cascade_stage(
    posts: Mapping[str, Post],
    marked: Mapping[str, frozenset[str]],
    ask: Ask,
    limit: int,
    seed: int,
) -> Cascade | str:
    """Untested without a probe pack that fits the vectors, or when no probe flags a post.

    `marked` holds what the screen named on each post, without any probe listed: the stage
    also counts how often listing the probe changes the answer.
    """
    folder = get_settings().probes_dir
    if not (folder / PACK_FILE).is_file():
        return UNTESTED
    keys = sorted(posts)
    vectors, model_key = post_vectors(keys)
    techniques = {name for post in posts.values() for name in post.answers}
    flagged = flagging(load_probes(folder, model_key), vectors, keys, techniques)
    if not flagged:
        return UNTESTED
    readings = ask(
        {
            key: ReviewRequest(text=posts[key].text, probes=flagged[key])
            for key in draw(flagged, min(CASCADE_POSTS, limit), seed)
        },
        1,
    )
    supported = {
        post: {finding.probe: finding.reading == "supported" for finding in reading.review.findings}
        for post, reading in readings.items()
        if reading.review.status == "done"
    }
    measures, same = {}, []
    for name in sorted({info.key for infos in flagged.values() for info in infos}):
        by_probe = {
            post: posts[post].answers[name]
            for post, infos in flagged.items()
            if name in posts[post].answers and any(info.key == name for info in infos)
        }
        # A post whose screen answer could not be read is left out: the two are compared.
        read = {
            post: found[name]
            for post, found in supported.items()
            if post in by_probe and post in marked
        }
        screened = {post: name in marked[post] for post in read}
        measures[name] = cascade_measure(by_probe, read, screened)
        same += [screened[post] == kept for post, kept in read.items()]
    pack = ProbePack.model_validate_json((folder / PACK_FILE).read_text(encoding="utf-8"))
    return Cascade(
        pack_run=pack.run,
        pack_exported_at=pack.exported_at,
        posts=len(posts),
        posts_flagged=len(flagged),
        posts_read=len(supported),
        probes=measures,
        same_as_screen=wilson(sum(same), len(same)),
    )

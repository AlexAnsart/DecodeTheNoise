"""Draws train posts likely to carry a label, so that a rare label gets positives to learn from.

Two sources per label. With a first probe: the posts it scores highest, plus a slice just below,
where it hesitates. Without one: the posts closest to the positives already found and to the
YES examples of the guide. Only the train split is searched, and annotators are not told why a
post was drawn. The bias this adds stays in train: calibration and test are never enriched.

One round per family is written (`<name>_<family>`), to be annotated by that family's pass only.

Run: uv run --group pipelines python -m pipelines.probes.enrich --name e1 --run v0 --rounds m1
"""

import argparse
import logging
import re

import numpy as np

from backend.model_client.embedding import EmbeddingClient
from backend.settings import get_settings
from pipelines.probes.batches import GUIDES
from pipelines.probes.dataset import Labelled, load_labelled, vectors_for
from pipelines.probes.pool import load_pool
from pipelines.probes.sample import RoundItem, drawn_keys, fetch_texts, keys_of, write_items
from pipelines.probes.score import load_probes, pool_vectors, split_rows
from pipelines.probes.taxonomy import AUXILIARY, BY_NAME, LABELS, LLM_TEST, YES, Label
from pipelines.probes.train import SEED

log = logging.getLogger("probes.enrich")

SEARCHED = 500_000  # train posts searched, drawn at random
TOP, TOP_DRAWN = 300, 70
BELOW, BELOW_DRAWN = 3000, 30
_YES_EXAMPLE = re.compile(r'^- YES: "(.+)"(?: →.*)?$', re.MULTILINE)


def guide_examples(label: Label) -> list[str]:
    """The YES examples of the label's section in its guide."""
    guide = (GUIDES / f"{label.family}.md").read_text(encoding="utf-8")
    section = guide.split(f"## `{label.name}`", 1)[1].split("\n## ", 1)[0]
    return [text.replace('\\"', '"') for text in _YES_EXAMPLE.findall(section)]


def embed(texts: list[str]) -> np.ndarray:
    """Unit vectors of the served size, from the model and the prefix the corpus was made with."""
    settings = get_settings()
    client = EmbeddingClient(
        settings.embedding_api_base, settings.embedding_api_key, settings.embedding_key()
    )
    vectors = client.embed(texts)
    client.close()
    return vectors


def seed_scores(label: Label, positives: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """Cosine of each searched post to its closest seed: a known positive or a guide example.

    The closest seed, not the mean of the seeds: the examples of a label can be far apart.
    """
    examples = guide_examples(label)
    seeds = [positives] if len(positives) else []
    if examples:
        seeds.append(embed(examples))
    return (vectors @ np.concatenate(seeds).T).max(axis=1)


def pick(scores: np.ndarray, rng: np.random.Generator, free: np.ndarray) -> np.ndarray:
    """Positions drawn among the highest scores and just below, never one already drawn."""
    ranked = np.argsort(-scores)
    ranked = ranked[free[ranked]]
    top = rng.choice(ranked[:TOP], size=min(TOP_DRAWN, len(ranked[:TOP])), replace=False)
    below = rng.choice(ranked[TOP:BELOW], size=BELOW_DRAWN, replace=False)
    return np.r_[top, below]


def enrichable() -> list[str]:
    """Yes/no labels that train a probe or a descriptor."""
    return [lab.name for lab in LABELS if lab.binary and lab.use not in (AUXILIARY, LLM_TEST)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--run", help="probes to search with; without it, every label uses seeds")
    parser.add_argument("--rounds", nargs="*", default=[], help="rounds holding known positives")
    parser.add_argument("--labels", nargs="*", default=enrichable())
    parser.add_argument(
        "--enough",
        type=int,
        default=10**9,
        help="skip a label that already has this many train positives",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    rng = np.random.default_rng(SEED + sum(map(ord, args.name)))
    pool = load_pool()
    probes = load_probes(args.run) if args.run else None
    labelled = load_labelled(tuple(args.rounds)) if args.rounds else None
    rows = np.sort(rng.choice(split_rows(pool, "train"), size=SEARCHED, replace=False))
    keys = np.array(keys_of(pool, rows))
    taken = drawn_keys()
    free = np.array([key not in taken for key in keys])
    vectors = pool_vectors(pool, rows)
    logits = probes.logits(vectors) if probes else None
    drawn: dict[str, dict[str, str]] = {}  # family -> post key -> stratum
    for name in args.labels:
        label = BY_NAME[name]
        have = len(known_positives(labelled, label))
        if have >= args.enough:
            log.info("%-26s skipped: %d train positives", name, have)
            continue
        if probes and name in probes.names:
            scores, source = logits[:, probes.names.index(name)], "probe"
        else:
            scores, source = seed_scores(label, known_positives(labelled, label), vectors), "seed"
        picked = pick(scores, rng, free)
        free[picked] = False
        family = drawn.setdefault(label.family, {})
        family.update({key: f"enrich:{name}:{source}" for key in keys[picked]})
        log.info("%-26s %s: %d posts", name, source, len(picked))
    for family, posts in drawn.items():
        texts = fetch_texts(list(posts))
        items = [RoundItem(key, "train", stratum, texts[key]) for key, stratum in posts.items()]
        write_items(f"{args.name}_{family}", items)
        log.info("round %s_%s: %d posts", args.name, family, len(items))


def known_positives(labelled: Labelled | None, label: Label) -> np.ndarray:
    """Vectors of the train posts already answered yes on the label."""
    if labelled is None or label.name not in labelled.answers:
        return np.empty(0)
    rows = labelled.rows(label, "train")
    yes = rows[labelled.answers[label.name][rows] == YES]
    return vectors_for([labelled.keys[i] for i in yes])[0] if len(yes) else np.empty(0)


if __name__ == "__main__":
    main()

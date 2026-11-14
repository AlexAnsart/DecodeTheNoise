"""Organic pools: real accounts of the 2026 sample that posted several times on one word.

A pool is the posts found for one search term in one month, by the actors with at least
`MIN_POSTS` of them. It is the real-data side of the benchmark: the negatives of the
interchangeable-actors test, and the subjects the synthetic briefs are written on.

Run: uv run --group pipelines python -m pipelines.briefs.pools
"""

import logging
import random
import re
from collections import Counter, defaultdict
from collections.abc import Iterator

import pyarrow.parquet as pq

from pipelines.briefs.bench import POOLS_EXTRA_FILE, POOLS_FILE, SEED, write_jsonl
from pipelines.datasets.tweets_2026 import DOWNLOAD_DIR
from pipelines.ingest.ira import hashed, text_without_urls
from pipelines.ingest.tweets_2026 import parse_date

log = logging.getLogger("briefs.pools")

COLUMNS = ("search_term", "username", "date", "text", "is-retweet")
MIN_CHARS = 60
MIN_POSTS = 6
MIN_ACTORS = 8
# Above this mean, a pool is a handful of accounts posting one template all month.
MAX_MEAN_POSTS = 30
N_POOLS = 60
# More real pools, kept apart: no synthetic post is written on them. They only serve as real
# negatives, so a false-positive rate can be measured on groups no threshold was set on.
N_EXTRA = 140
ACTORS_PER_POOL = 12
POSTS_PER_ACTOR = 12
# An actor whose posts mostly open with the same words is posting a template.
MIN_DISTINCT_OPENINGS = 0.8
OPENING_CHARS = 40
STOPWORDS = re.compile(r"\b(the|and|is|to|of|that|it|for|you|this|are|was|with|not|have)\b", re.I)

Key = tuple[str, str, str]  # search term, month, username


def is_english(text: str) -> bool:
    """A cheap screen, not a language detector: two common words and almost only ASCII."""
    ascii_share = sum(c.isascii() for c in text) / len(text)
    return ascii_share >= 0.95 and len(STOPWORDS.findall(text)) >= 2


def own_posts() -> Iterator[tuple[Key, str, str]]:
    """(key, text, date) of every English post of the minimum length that is not a repost."""
    for path in sorted(DOWNLOAD_DIR.glob("*.parquet")):
        for batch in pq.ParquetFile(path).iter_batches(batch_size=100_000, columns=list(COLUMNS)):
            cols = batch.to_pydict()
            rows = zip(*(cols[name] for name in COLUMNS), strict=True)
            for term, user, date, text, repost in rows:
                if repost or not text or not user or not term:
                    continue
                clean = text_without_urls(text)
                if len(clean) >= MIN_CHARS and is_english(clean):
                    yield (term, str(date)[:7], user), clean, str(date)


def choose_pools(counts: Counter[Key]) -> list[tuple[str, str]]:
    """One month per term (the one with most prolific actors), the largest pools first."""
    sizes: dict[tuple[str, str], list[int]] = defaultdict(list)
    for (term, month, _user), n in counts.items():
        if n >= MIN_POSTS:
            sizes[(term, month)].append(n)
    best: dict[str, tuple[int, str]] = {}
    for (term, month), posts in sizes.items():
        if len(posts) >= MIN_ACTORS and sum(posts) / len(posts) <= MAX_MEAN_POSTS:
            best[term] = max(best.get(term, (0, "")), (len(posts), month))
    ranked = sorted(best.items(), key=lambda kv: (-kv[1][0], kv[0]))
    return [(term, month) for term, (_n, month) in ranked[: N_POOLS + N_EXTRA]]


def is_template(texts: list[str]) -> bool:
    openings = {text[:OPENING_CHARS].lower() for text in texts}
    return len(openings) < MIN_DISTINCT_OPENINGS * len(texts)


def sampled(
    pools: list[tuple[str, str]], posts: dict[Key, list[tuple[str, str]]], rng: random.Random
) -> list[dict[str, object]]:
    """Up to `ACTORS_PER_POOL` actors of each pool, up to `POSTS_PER_ACTOR` posts of each."""
    rows: list[dict[str, object]] = []
    for term, month in sorted(pools):
        actors = sorted(k for k in posts if k[:2] == (term, month))
        actors = [k for k in actors if not is_template([text for text, _ in posts[k]])]
        for key in rng.sample(actors, min(ACTORS_PER_POOL, len(actors))):
            kept = rng.sample(posts[key], min(POSTS_PER_ACTOR, len(posts[key])))
            for text, date in kept:
                rows.append(
                    {
                        "pool": f"{term}-{month}",
                        "actor": hashed(key[2].lower(), 12),
                        "text": text,
                        "created_at": parse_date(date),
                    }
                )
    return rows


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    counts: Counter[Key] = Counter(key for key, _text, _date in own_posts())
    ranked = choose_pools(counts)
    chosen = set(ranked)
    log.info("%d pools chosen", len(chosen))

    posts: dict[Key, list[tuple[str, str]]] = defaultdict(list)
    for key, text, date in own_posts():
        if key[:2] in chosen and counts[key] >= MIN_POSTS:
            posts[key].append((text, date))

    # Two files and two generators: the first pools do not change when more are added.
    first = write_jsonl(POOLS_FILE, sampled(ranked[:N_POOLS], posts, random.Random(SEED)))
    extra = write_jsonl(POOLS_EXTRA_FILE, sampled(ranked[N_POOLS:], posts, random.Random(SEED + 1)))
    log.info("%d posts in %s, %d posts in %s", first, POOLS_FILE, extra, POOLS_EXTRA_FILE)


if __name__ == "__main__":
    main()

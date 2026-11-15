"""Turns one row of the 2026 sample of X posts into a normalised item. Pure: no I/O."""

from datetime import datetime
from urllib.parse import urlsplit

from pipelines.ingest.ira import PLATFORM_HOSTS, Item, hashed, is_long_enough

# The columns an item is made of; the others (display name, avatar, counts, media) are not read.
COLUMNS = (
    "id",
    "username",
    "profile_id",
    "text",
    "date",
    "is-retweet",
    "replying-to",
    "quoted-post",
    "external-link",
)
PLATFORM = frozenset({*PLATFORM_HOSTS, "x.com", "www.x.com"})


def parse_date(value: object) -> int | None:
    """'2026-06-11 20:41:00+00:00' to milliseconds. The dataset gives minutes."""
    try:
        return int(datetime.fromisoformat(str(value)).timestamp() * 1000)
    except ValueError:
        return None


def post_type(row: dict[str, object]) -> str:
    if row.get("is-retweet"):
        return "repost"
    quoted = row.get("quoted-post")
    if isinstance(quoted, dict) and quoted.get("text"):
        return "quote"
    return "reply" if row.get("replying-to") else "original"


def parse_row(row: dict[str, object]) -> Item | None:
    """None when the row has no id, no author, or a text under the minimum length."""
    tweet_id = str(row.get("id") or "").strip()
    author = str(row.get("username") or row.get("profile_id") or "").strip()
    text = str(row.get("text") or "").strip()
    if not tweet_id or not author or not is_long_enough(text):
        return None
    link = str(row.get("external-link") or "").strip()
    return Item(
        item_id=hashed("x2026:" + tweet_id, 16),
        actor_id=hashed(author.lower(), 12),
        text=text,
        created_at=parse_date(row.get("date")),
        # The dataset has no language column and mixes English, German and others.
        lang=None,
        # The dataset flags a repost but does not say which post it repeats.
        repost_of=None,
        urls=(link,) if link and urlsplit(link).hostname not in PLATFORM else (),
        category="Unknown",
        post_type=post_type(row),
        followers=None,
    )

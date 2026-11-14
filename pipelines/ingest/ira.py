"""Turns one row of the IRA tweets CSV into a normalised item. Pure: no I/O."""

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

# Shorter texts carry too little meaning to place on the map (measured on the text without URLs).
MIN_TEXT_CHARS = 20

URL_PATTERN = re.compile(r"https?://\S+")
LINK_COLUMNS = ("tco1_step1", "tco2_step1", "tco3_step1")
# Links back to the platform spell out the handle of the author, which is never stored.
PLATFORM_HOSTS = frozenset({"twitter.com", "www.twitter.com", "mobile.twitter.com", "t.co"})
POST_TYPES = {"": "original", "RETWEET": "repost", "QUOTE_TWEET": "quote"}


@dataclass(frozen=True)
class Item:
    item_id: str
    actor_id: str
    text: str
    created_at: int | None  # milliseconds since the epoch
    lang: str | None
    repost_of: str | None
    urls: tuple[str, ...]
    category: str
    post_type: str
    followers: int | None


def hashed(value: str, length: int) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def text_without_urls(text: str) -> str:
    return " ".join(URL_PATTERN.sub(" ", text).split())


def is_long_enough(text: str) -> bool:
    return len(text_without_urls(text)) >= MIN_TEXT_CHARS


def parse_date(value: str) -> int | None:
    """'9/14/2015 7:57' to milliseconds. The dataset gives minutes and no time zone: UTC assumed."""
    try:
        moment = datetime.strptime(value.strip(), "%m/%d/%Y %H:%M")
    except ValueError:
        return None
    return int(moment.replace(tzinfo=UTC).timestamp() * 1000)


def external_urls(row: dict[str, str]) -> tuple[str, ...]:
    links = (row.get(column, "").strip() for column in LINK_COLUMNS)
    kept = [u for u in links if u and urlsplit(u).hostname not in PLATFORM_HOSTS]
    return tuple(dict.fromkeys(kept))


def parse_row(row: dict[str, str]) -> Item | None:
    """None when the row has no id, no author, or a text under the minimum length."""
    tweet_id = row.get("tweet_id", "").strip()
    author = row.get("author", "").strip()
    text = row.get("content", "").strip()
    if not tweet_id or not author or not is_long_enough(text):
        return None
    post_type = POST_TYPES.get(row.get("post_type", "").strip(), "original")
    if post_type == "original" and row.get("retweet", "").strip() == "1":
        post_type = "repost"
    followers = row.get("followers", "").strip()
    return Item(
        item_id=hashed("ira:" + tweet_id, 16),
        actor_id=hashed(author.lower(), 12),
        text=text,
        created_at=parse_date(row.get("publish_date", "")),
        lang=row.get("language", "").strip() or None,
        # The dataset flags a repost but does not say which post it repeats.
        repost_of=None,
        urls=external_urls(row),
        category=row.get("account_category", "").strip() or "Unknown",
        post_type=post_type,
        followers=int(followers) if followers.isdigit() else None,
    )

from pipelines.ingest.ira import Item, hashed
from pipelines.ingest.tweets_2026 import parse_row

ROW: dict[str, object] = {
    "id": "2065172604801941976",
    "username": "@SomeHandle",
    "profile_id": "1539653374433546242",
    "text": "The council voted on the budget tonight and nobody was told beforehand.",
    "date": "2026-06-11 20:41:00+00:00",
    "is-retweet": False,
    "replying-to": [],
    "quoted-post": None,
    "external-link": "",
}


def _parsed(row: dict[str, object]) -> Item:
    item = parse_row(row)
    assert item is not None
    return item


def test_row_becomes_item() -> None:
    item = _parsed(ROW)
    assert item.created_at == 1781210460000
    assert item.post_type == "original"
    assert item.lang is None
    assert item.urls == ()


def test_handle_is_hashed_and_never_kept() -> None:
    item = _parsed(ROW)
    assert item.actor_id == hashed("@somehandle", 12)
    assert "somehandle" not in repr(item).lower()


def test_row_without_handle_falls_back_on_the_profile_id() -> None:
    item = _parsed({**ROW, "username": None})
    assert item.actor_id == hashed("1539653374433546242", 12)


def test_kinds_of_post() -> None:
    assert _parsed({**ROW, "is-retweet": True}).post_type == "repost"
    assert _parsed({**ROW, "replying-to": ["@other"]}).post_type == "reply"
    quoted = {"text": "the quoted words", "link": "https://twitter.com/a/status/1"}
    assert _parsed({**ROW, "quoted-post": quoted}).post_type == "quote"
    assert _parsed({**ROW, "quoted-post": {"text": None}}).post_type == "original"


def test_short_text_or_missing_id_is_dropped() -> None:
    assert parse_row({**ROW, "text": "ok thanks"}) is None
    assert parse_row({**ROW, "id": ""}) is None


def test_external_link_is_kept_unless_it_points_back_to_the_platform() -> None:
    assert _parsed({**ROW, "external-link": "https://example.org/story"}).urls == (
        "https://example.org/story",
    )
    assert _parsed({**ROW, "external-link": "https://x.com/a/status/1"}).urls == ()


def test_unreadable_date_gives_no_time() -> None:
    assert _parsed({**ROW, "date": "yesterday"}).created_at is None

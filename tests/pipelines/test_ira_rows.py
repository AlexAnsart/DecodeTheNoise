from pipelines.ingest.__main__ import sample_rows, to_items
from pipelines.ingest.ira import Item, hashed, parse_date, parse_row, text_without_urls

ROW = {
    "author": "SomeHandle",
    "content": "Senate votes on the budget tonight, watch live http://t.co/abc123",
    "language": "English",
    "publish_date": "9/14/2015 7:57",
    "followers": "1836",
    "post_type": "",
    "retweet": "0",
    "account_category": "NewsFeed",
    "tweet_id": "643332738230165504",
    "tco1_step1": "https://twitter.com/somehandle/status/643332738230165504/photo/1",
    "tco2_step1": "http://example.org/story",
    "tco3_step1": "",
}


def _parsed(row: dict[str, str]) -> Item:
    item = parse_row(row)
    assert item is not None
    return item


def test_row_becomes_item() -> None:
    item = _parsed(ROW)
    assert item.created_at == 1442217420000
    assert item.lang == "English"
    assert item.category == "NewsFeed"
    assert item.post_type == "original"
    assert item.followers == 1836
    assert item.repost_of is None


def test_handle_is_hashed_and_never_kept() -> None:
    item = _parsed(ROW)
    assert item.actor_id == hashed("somehandle", 12)
    assert "somehandle" not in repr(item).lower()


def test_same_handle_in_another_case_is_the_same_actor() -> None:
    upper = _parsed({**ROW, "author": "SOMEHANDLE"})
    lower = _parsed({**ROW, "author": "somehandle"})
    assert upper.actor_id == lower.actor_id


def test_links_to_the_platform_are_dropped() -> None:
    assert _parsed(ROW).urls == ("http://example.org/story",)


def test_post_types() -> None:
    assert _parsed({**ROW, "post_type": "RETWEET"}).post_type == "repost"
    assert _parsed({**ROW, "post_type": "QUOTE_TWEET"}).post_type == "quote"
    assert _parsed({**ROW, "retweet": "1"}).post_type == "repost"


def test_text_under_the_minimum_once_links_are_removed_is_dropped() -> None:
    assert parse_row({**ROW, "content": "look http://t.co/abcdefghijklmnop"}) is None


def test_row_without_id_or_author_is_dropped() -> None:
    assert parse_row({**ROW, "tweet_id": ""}) is None
    assert parse_row({**ROW, "author": " "}) is None


def test_date_that_does_not_parse_is_unknown() -> None:
    assert parse_date("not a date") is None
    assert _parsed({**ROW, "publish_date": ""}).created_at is None


def test_text_without_urls_collapses_spaces() -> None:
    assert text_without_urls("a  http://x.y/z  b") == "a b"


def _rows(count: int) -> list[dict[str, str]]:
    return [
        {**ROW, "tweet_id": str(i), "publish_date": f"1/{1 + i % 28}/2016 10:00"}
        for i in range(count)
    ]


def test_sample_is_seeded_and_of_the_asked_size() -> None:
    first = sample_rows(iter(_rows(500)), 50, seed=7)
    again = sample_rows(iter(_rows(500)), 50, seed=7)
    other = sample_rows(iter(_rows(500)), 50, seed=8)
    assert len(first) == 50
    assert [r["tweet_id"] for r in first] == [r["tweet_id"] for r in again]
    assert [r["tweet_id"] for r in first] != [r["tweet_id"] for r in other]


def test_items_are_unique_and_oldest_first() -> None:
    rows = _rows(40)
    items = to_items([*rows, rows[0]])
    assert len(items) == 40
    stamps = [item.created_at for item in items]
    assert stamps == sorted(stamps)

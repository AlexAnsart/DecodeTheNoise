from datetime import UTC, datetime

import httpx
import pytest

from backend.web_reader.context_dev import ContextDevReader, PageUnreadable
from backend.web_reader.plain_text import markdown_to_text

URL = "https://news.example/article"


def _output(success: bool, data: str | None, **extra: str) -> dict[str, object]:
    return {"requested": True, "success": success, "data": data, **extra}


def _reader(handler: httpx.MockTransport) -> ContextDevReader:
    return ContextDevReader("test-key", "https://reader.example/v1", transport=handler)


def test_page_is_read_as_plain_text_and_kept() -> None:
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "url": URL,
                "markdown": _output(
                    True, "# Headline\n\nThe **first** [paragraph](https://x.example)."
                ),
                "metadata": {"title": " Headline - Example News "},
                "cache_metadata": {"status": "hit", "age_ms": 3_600_000},
            },
        )

    reader = _reader(httpx.MockTransport(answer))
    before = datetime.now(UTC)
    page = reader.read(URL)
    again = reader.read(URL)

    assert page.url == URL
    assert page.title == "Headline - Example News"
    assert page.text == "Headline\nThe first paragraph."
    # The reader served a copy fetched an hour ago: that is when the page was read.
    read_at = datetime.strptime(page.read_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert 3_590 <= (before - read_at).total_seconds() <= 3_610
    assert again is page
    assert len(requests) == 1
    assert requests[0].headers["Authorization"] == "Bearer test-key"
    assert requests[0].url == "https://reader.example/v1/web/scrape"


def test_a_failed_output_inside_a_200_is_a_failure_with_its_message() -> None:
    def answer(_: httpx.Request) -> httpx.Response:
        failed = _output(
            False, None, error_code="WEBSITE_NOT_FOUND", message="The hostname does not exist."
        )
        return httpx.Response(200, json={"url": URL, "markdown": failed, "metadata": {}})

    with pytest.raises(PageUnreadable) as caught:
        _reader(httpx.MockTransport(answer)).read(URL)

    assert caught.value.reason == "The hostname does not exist."


@pytest.mark.parametrize(
    ("status", "body", "reason"),
    [
        (400, {"message": "The URL is not public."}, "The URL is not public."),
        (402, {"error_code": "USAGE_EXCEEDED"}, "The page reader is not available right now."),
        (408, {}, "The page took too long to answer."),
        (500, {}, "The page reader is not available right now."),
    ],
)
def test_a_refusal_becomes_a_reason_for_the_user(
    status: int, body: dict[str, str], reason: str
) -> None:
    reader = _reader(httpx.MockTransport(lambda _: httpx.Response(status, json=body)))

    with pytest.raises(PageUnreadable) as caught:
        reader.read(URL)

    assert caught.value.reason == reason


def test_a_network_failure_and_an_unknown_shape_are_failures_not_errors() -> None:
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("no answer", request=request)

    with pytest.raises(PageUnreadable):
        _reader(httpx.MockTransport(unreachable)).read(URL)
    with pytest.raises(PageUnreadable):
        _reader(httpx.MockTransport(lambda _: httpx.Response(200, text="<html>"))).read(URL)
    with pytest.raises(PageUnreadable):
        _reader(httpx.MockTransport(lambda _: httpx.Response(200, json={"unexpected": 1}))).read(
            URL
        )


def test_a_failure_is_not_kept_so_the_next_paste_tries_again() -> None:
    calls = [0]

    def answer(_: httpx.Request) -> httpx.Response:
        calls[0] += 1
        if calls[0] == 1:
            return httpx.Response(500, json={})
        return httpx.Response(200, json={"markdown": _output(True, "Back online.")})

    reader = _reader(httpx.MockTransport(answer))
    with pytest.raises(PageUnreadable):
        reader.read(URL)

    assert reader.read(URL).text == "Back online."


def test_markdown_marks_are_removed() -> None:
    markdown = (
        "## Title\n\n"
        "![photo](https://x.example/a.png)\n"
        "The **Agency** (_**IRA**_), also called `Glavset`,\\[1\\] ran [accounts](https://x.example).\n\n"
        "> A quote.\n\n"
        "- first\n- second\n\n"
        "| Founded | 2013 |\n| --- | --- |\n\n"
        "---\n\n"
        "A snake_case_name stays, and so does 2 * 3 * 4."
    )

    assert markdown_to_text(markdown) == (
        "Title\n"
        "The Agency (IRA), also called Glavset, ran accounts.\n"
        "A quote.\n"
        "first\n"
        "second\n"
        "Founded 2013\n"
        "A snake_case_name stays, and so does 2 * 3 * 4."
    )

"""Reads a web page as clean text through Context.dev: the one module that knows that API.

One call to `POST /web/scrape` asking for the Markdown of the main content. A 200 can still
carry a failed output, so success is read on the output itself. Pages read are kept in memory by
URL: a repeated paste costs no credit and no wait.
"""

import logging
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Protocol

import httpx
from pydantic import BaseModel, Field

from backend.web_reader.plain_text import markdown_to_text

logger = logging.getLogger(__name__)

_CACHE_SIZE = 256
# The reader is told to give up after this long; the HTTP call waits a little more for its answer.
_SCRAPE_DEADLINE_MS = 30_000
_HTTP_TIMEOUT_SECONDS = 40.0


@dataclass(frozen=True)
class Page:
    url: str
    title: str | None
    text: str
    # When the content was fetched from the site (UTC, ISO 8601), not when it was asked for.
    read_at: str


class PageUnreadable(Exception):
    """The page gave no text. `reason` is a sentence fit for the user."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class PageReader(Protocol):
    def read(self, url: str) -> Page: ...


class _Output(BaseModel):
    success: bool | None = None
    data: str | None = None
    error_code: str | None = None
    message: str | None = None


class _Metadata(BaseModel):
    title: str | None = None


class _CacheMetadata(BaseModel):
    age_ms: int = 0


class _ScrapeResponse(BaseModel):
    url: str | None = None
    markdown: _Output
    metadata: _Metadata = Field(default_factory=_Metadata)
    cache_metadata: _CacheMetadata = Field(default_factory=_CacheMetadata)


class _Refusal(BaseModel):
    message: str | None = None
    error_code: str | None = None


class ContextDevReader:
    def __init__(
        self, api_key: str, base_url: str, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_HTTP_TIMEOUT_SECONDS,
            transport=transport,
        )
        self._pages: OrderedDict[str, Page] = OrderedDict()
        self._lock = Lock()

    def read(self, url: str) -> Page:
        with self._lock:
            known = self._pages.get(url)
            if known is not None:
                self._pages.move_to_end(url)
                return known
        page = self._scrape(url)
        with self._lock:
            self._pages[url] = page
            if len(self._pages) > _CACHE_SIZE:
                self._pages.popitem(last=False)
        return page

    def _scrape(self, url: str) -> Page:
        try:
            response = self._http.post(
                "/web/scrape",
                json={
                    "url": url,
                    "formats": {"markdown": True},
                    "sharedParams": {"mainContentOnly": True},
                    "markdownParams": {"includeLinks": False},
                    "timeoutOpts": {"milliseconds": _SCRAPE_DEADLINE_MS},
                },
            )
        except httpx.HTTPError as error:
            logger.warning("page reader unreachable for %s: %s", url, type(error).__name__)
            raise PageUnreadable("The page reader did not answer.") from error
        if response.status_code != httpx.codes.OK:
            raise PageUnreadable(_refusal_reason(url, response))
        try:
            body = _ScrapeResponse.model_validate(response.json())
        except ValueError as error:
            logger.warning("page reader answered in an unknown shape for %s", url)
            raise PageUnreadable(
                "The page reader gave an answer that could not be read."
            ) from error
        output = body.markdown
        if not output.success or not output.data:
            logger.info("page not read: %s (%s)", url, output.error_code)
            raise PageUnreadable(output.message or "The page could not be read.")
        fetched = datetime.now(UTC) - timedelta(milliseconds=body.cache_metadata.age_ms)
        return Page(
            url=body.url or url,
            title=(body.metadata.title or "").strip() or None,
            text=markdown_to_text(output.data),
            read_at=fetched.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    def close(self) -> None:
        self._http.close()


def _refusal_reason(url: str, response: httpx.Response) -> str:
    """Why the reader refused, in words for the user. The detail goes to the log."""
    try:
        refusal = _Refusal.model_validate(response.json())
    except ValueError:
        refusal = _Refusal()
    logger.warning(
        "page reader refused %s: HTTP %d %s", url, response.status_code, refusal.error_code
    )
    if response.status_code == httpx.codes.BAD_REQUEST:
        # The request is ours and fixed: a 400 is about the address itself.
        return refusal.message or "The page reader does not accept this address."
    if response.status_code == httpx.codes.REQUEST_TIMEOUT:
        return "The page took too long to answer."
    return "The page reader is not available right now."

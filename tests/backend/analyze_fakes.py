"""Stand-ins for the embedding model and the web reader: no test calls a paid or local model."""

from dataclasses import dataclass, field

import numpy as np

from backend.web_reader.context_dev import Page, PageUnreadable


@dataclass
class FakeEmbedder:
    """Answers a fixed vector per text, and records what it was asked to embed."""

    key: str
    default: np.ndarray
    by_text: dict[str, np.ndarray] = field(default_factory=dict)
    asked: list[str] = field(default_factory=list)

    def embed(self, text: str) -> np.ndarray:
        self.asked.append(text)
        return self.by_text.get(text, self.default)


@dataclass
class FakeReader:
    """Answers a page or a failure per URL, and records the URLs it was asked to read."""

    pages: dict[str, Page | PageUnreadable]
    asked: list[str] = field(default_factory=list)

    def read(self, url: str) -> Page:
        self.asked.append(url)
        result = self.pages[url]
        if isinstance(result, PageUnreadable):
            raise result
        return result

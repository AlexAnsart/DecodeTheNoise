"""The documents the method page shows as they are: the annotation guides, the report of the
probe campaign and its figures, the note on the LLM review. Read from the repository's `docs/`
folder; a file that is not there is simply not listed.
"""

import re
from pathlib import Path

from backend.method.schema import Document

# Path of `docs/` in the repository, for the links to the sources.
REPOSITORY_DOCS = "docs"
GUIDES = "probes/guides"
FIGURES = "probes/figures"
# The rules every annotator received come before the guide of each family.
COMMON_GUIDE = "common"
DOCUMENTS = (
    ("report", "probes/report.md"),
    ("taxonomy", "probes/taxonomy.md"),
    ("journal", "probes/journal.md"),
    ("review", "review.md"),
)
FIGURE_SUFFIX = ".png"
_HEADING = re.compile(r"^# +(.+)$", re.MULTILINE)
# A label section of a guide: "## `name`", then its closed question.
_QUESTION = re.compile(r"^## +`(?P<name>[^`]+)`\s*\n+\*\*Question\.\*\*\s*(?P<question>.+)$", re.M)


def _document(docs: Path, relative: str, name: str) -> Document | None:
    path = docs / relative
    if not path.is_file():
        return None
    markdown = path.read_text(encoding="utf-8")
    heading = _HEADING.search(markdown)
    return Document(
        name=name,
        title=heading.group(1).strip() if heading else name,
        path=f"{REPOSITORY_DOCS}/{relative}",
        markdown=markdown,
    )


def guides_of(docs: Path) -> list[Document]:
    """The exact instructions the annotators received: the common rules, then each family."""
    folder = docs / GUIDES
    if not folder.is_dir():
        return []
    names = sorted(path.stem for path in folder.glob("*.md"))
    ordered = [name for name in names if name == COMMON_GUIDE] + [
        name for name in names if name != COMMON_GUIDE
    ]
    found = (_document(docs, f"{GUIDES}/{name}.md", name) for name in ordered)
    return [guide for guide in found if guide is not None]


def documents_of(docs: Path) -> list[Document]:
    found = (_document(docs, relative, name) for name, relative in DOCUMENTS)
    return [document for document in found if document is not None]


def figure_names(docs: Path) -> list[str]:
    folder = docs / FIGURES
    if not folder.is_dir():
        return []
    return sorted(path.name for path in folder.glob(f"*{FIGURE_SUFFIX}"))


def questions_of(guides: list[Document]) -> dict[str, str]:
    """The closed question of each label, as its guide asks it."""
    return {
        match["name"]: match["question"].strip()
        for guide in guides
        for match in _QUESTION.finditer(guide.markdown)
    }

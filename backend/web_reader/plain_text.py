"""Markdown from a page reader, turned into plain text with a few regular expressions.

Good enough to embed and to show an excerpt; it is not a Markdown parser.
"""

import re

_FENCE = re.compile(r"^\s*(```|~~~).*$", re.MULTILINE)
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_HTML_TAG = re.compile(r"<[^>\n]+>")
_TABLE_RULE = re.compile(r"^\s*\|?[\s:-]*-[\s:|-]*$", re.MULTILINE)
_RULE = re.compile(r"^\s*([-*_]\s*){3,}$", re.MULTILINE)
_LINE_START = re.compile(
    r"^[ \t]{0,3}(#{1,6}[ \t]+|>[ \t]?|[-*+][ \t]+|\d+[.)][ \t]+)", re.MULTILINE
)
_STARS = re.compile(r"(\*{1,3}|~~|`)(?=\S)(.+?)(?<=\S)\1")
# Underscores mark emphasis only at the edge of a word: snake_case must survive.
_UNDERSCORES = re.compile(r"(?<![A-Za-z0-9])(_{1,3})(?=\S)(.+?)(?<=\S)\1(?![A-Za-z0-9])")
_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|>~])")
_REFERENCE = re.compile(r"\[\d{1,3}\]")
_SPACES = re.compile(r"[ \t\u00a0]+")
_BLANK_LINES = re.compile(r"\n\s*\n+")


def markdown_to_text(markdown: str) -> str:
    """Paragraphs separated by one line break, with the Markdown marks removed."""
    text = _FENCE.sub("", markdown)
    text = _IMAGE.sub("", text)
    text = _LINK.sub(r"\1", text)
    text = _HTML_TAG.sub("", text)
    text = _TABLE_RULE.sub("", text)
    text = _RULE.sub("", text)
    text = _LINE_START.sub("", text)
    # Twice: emphasis nests, as in _**both**_.
    for _ in range(2):
        text = _STARS.sub(r"\2", text)
        text = _UNDERSCORES.sub(r"\2", text)
    text = _ESCAPE.sub(r"\1", text)
    # Footnote marks say nothing once the notes are gone.
    text = _REFERENCE.sub("", text)
    text = text.replace("|", " ")
    text = _SPACES.sub(" ", text)
    lines = (line.strip() for line in _BLANK_LINES.sub("\n", text).split("\n"))
    return "\n".join(line for line in lines if line)

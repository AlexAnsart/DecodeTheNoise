"""The annotation guides, read once at start-up: the review applies them word for word.

The folder holds the rules common to every label (`common.md`) and one guide per family. A
guide has one section per label (question, YES conditions, NO list, examples) and may open with
a condition its labels share. A reading of the review then means what an annotation means.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from backend.probes.names import plain_name

logger = logging.getLogger(__name__)

COMMON_FILE = "common.md"
# The families whose labels are manipulation techniques: every reviewed item is screened for them.
SCREENED_FAMILIES = ("rhetoric", "fallacies")
# Sections of the common rules about the annotators' batches and answer format: not the review's.
_ANNOTATOR_ONLY = ("how to work", "your answer")

_SECTION = re.compile(r"^## ", re.MULTILINE)
_LABEL_HEADING = re.compile(r"^`(\w+)`\s*$")
_SHARED_HEADING = re.compile(r"^Shared \w+ ([A-Z]):")
_QUESTION = re.compile(r"\*\*Question\.\*\*\s*(.+)")
_EVIDENCE_ALL = re.compile(r"Evidence for every label of this guide: (required|none)", re.I)
_EVIDENCE_SOME = re.compile(r"^Evidence: (.+)$", re.MULTILINE)
_NAME = re.compile(r"`(\w+)`")


@dataclass(frozen=True)
class GuideLabel:
    key: str
    family: str
    name: str
    question: str
    # The section of the label, word for word.
    section: str
    # Whether a `yes` must come with a span of the text.
    evidence: bool
    # The label needs the condition its family shares.
    shared: bool


@dataclass(frozen=True)
class FamilyGuide:
    family: str
    # The guide as written, whole.
    text: str
    # What the guide says before its first section, without its title.
    notes: str
    # The condition the labels of the family share, with its heading; empty when there is none.
    condition: str


@dataclass(frozen=True)
class Guides:
    # The rules common to every label; empty when the folder has none.
    common: str = ""
    families: dict[str, FamilyGuide] = field(default_factory=dict)
    labels: dict[str, GuideLabel] = field(default_factory=dict)

    def label(self, key: str) -> GuideLabel | None:
        """The guide of a probe target: of its label, for one answer of a label (`theme:sport`)."""
        return self.labels.get(key.partition(":")[0])

    def screened(self) -> tuple[GuideLabel, ...]:
        """The techniques every reviewed item is screened for, guide by guide."""
        return tuple(
            label
            for family in SCREENED_FAMILIES
            for label in self.labels.values()
            if label.family == family
        )

    def material(self, keys: list[str]) -> str:
        """The guide sections of the given labels that are not techniques, family by family:
        the notes of the guide, its shared condition when a section needs it, the sections."""
        found = [label for key in dict.fromkeys(keys) if (label := self.label(key)) is not None]
        parts = []
        for family in dict.fromkeys(label.family for label in found):
            if family in SCREENED_FAMILIES:
                continue
            guide, own = self.families[family], [label for label in found if label.family == family]
            shared = guide.condition if any(label.shared for label in own) else ""
            sections = "\n\n".join(label.section for label in dict.fromkeys(own))
            body = "\n\n".join(part for part in (guide.notes, shared, sections) if part)
            parts.append(f"### Guide: {family}\n\n{body}")
        return "\n\n".join(parts)


NO_GUIDES = Guides()


def _sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """What comes before the first `## ` heading, then each section as (heading, whole text)."""
    head, *rest = _SECTION.split(text)
    return head, [(part.split("\n", 1)[0].strip(), "## " + part.strip()) for part in rest]


def _without_title(head: str) -> str:
    lines = [line for line in head.splitlines() if not line.startswith(("# ", "Version:"))]
    return "\n".join(lines).strip()


def read_common(text: str) -> str:
    head, sections = _sections(text)
    kept = [body for heading, body in sections if not heading.lower().endswith(_ANNOTATOR_ONLY)]
    return "\n\n".join(part for part in (_without_title(head), *kept) if part)


def _evidence(text: str, keys: list[str]) -> dict[str, bool]:
    """Which labels of a guide need a span for a `yes`. A guide that does not say: none does."""
    whole = _EVIDENCE_ALL.search(text)
    if whole:
        return dict.fromkeys(keys, whole.group(1).lower() == "required")
    needed = dict.fromkeys(keys, False)
    listed = _EVIDENCE_SOME.search(text)
    for sentence in listed.group(1).split(". ") if listed else []:
        if sentence.lower().startswith("required for"):
            needed.update(dict.fromkeys(_NAME.findall(sentence), True))
    return needed


def read_family(family: str, text: str) -> tuple[FamilyGuide, list[GuideLabel]]:
    head, sections = _sections(text)
    shared = [(heading, body) for heading, body in sections if _SHARED_HEADING.match(heading)]
    letter = _SHARED_HEADING.match(shared[0][0]).group(1) if shared else None
    refers = re.compile(rf"\b{letter}\b") if letter else None
    keyed = [
        (m.group(1), body) for heading, body in sections if (m := _LABEL_HEADING.match(heading))
    ]
    needs_span = _evidence(text, [key for key, _ in keyed])
    labels = []
    for key, body in keyed:
        question = _QUESTION.search(body)
        labels.append(
            GuideLabel(
                key=key,
                family=family,
                name=plain_name(key),
                question=question.group(1).strip() if question else "",
                section=body,
                evidence=needs_span[key],
                shared=bool(refers and refers.search(body)),
            )
        )
    guide = FamilyGuide(
        family=family,
        text=text.strip(),
        notes=_without_title(head),
        condition="\n\n".join(body for _, body in shared),
    )
    return guide, labels


def load_guides(folder: Path) -> Guides:
    """The guides of `folder`. Without the folder the review still runs, on the description of
    each probe alone and without the technique screen."""
    if not folder.is_dir():
        logger.warning("no annotation guides at %s: the review runs without them", folder)
        return NO_GUIDES
    common_path = folder / COMMON_FILE
    common = read_common(common_path.read_text(encoding="utf-8")) if common_path.is_file() else ""
    families: dict[str, FamilyGuide] = {}
    labels: dict[str, GuideLabel] = {}
    for path in sorted(folder.glob("*.md")):
        if path.name == COMMON_FILE:
            continue
        guide, found = read_family(path.stem, path.read_text(encoding="utf-8"))
        if not found:
            logger.warning("guide %s has no label section: left out", path.name)
            continue
        families[guide.family] = guide
        labels.update({label.key: label for label in found})
    logger.info("annotation guides: %d labels in %d families", len(labels), len(families))
    return Guides(common=common, families=families, labels=labels)

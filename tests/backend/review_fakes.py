"""Small annotation guides in the format of the real ones, and a stand-in for the LLM that
answers what a test scripts. No test calls a model."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from backend.probes.schema import ProbeInfo, ProbeState

COMMON = """# Annotation rules common to every guide

Version: v2

You annotate short posts. Apply these rules literally.

## 1. What you judge

1. **The text of the post, and nothing else.**

## 3. Own voice

A label applies only when the author does the thing in their own voice.

## 7. How to work

1. Take the posts in order.

## 8. Your answer

Return, for the batch: `batch_id`.
"""

RHETORIC = """# Guide: rhetoric

Version: v2. Read `common.md` first.

This guide has two labels.

## Shared condition S: the post is about a public matter

Every label of this guide needs condition S.

Evidence for every label of this guide: required.

## `loaded_language`

**Question.** Does the post name something with a charged word where a neutral word exists?

**YES when all are true:**

1. S is met.
2. The post uses a charged word.

**NO when:**

- the word is a plain evaluation.

## `fear_appeal`

**Question.** Does the post use a danger as the reason to support or reject something?

**YES when all are true:**

1. S is met.
2. The post warns of a harm to come.
"""

FALLACIES = """# Guide: fallacies

Version: v2. Read `common.md` first.

## Shared condition S: the post is about a public matter

Every label of this guide needs condition S.

Evidence for every label of this guide: required.

## `whataboutism`

**Question.** Does the post answer a criticism by pointing at someone else's wrong?

**YES when all are true:**

1. S is met.
2. The post points at a wrong done by the critic.

## `unnamed_authority`

**Question.** When the post uses an authority as proof, is that authority left unnamed?

**YES when both are true:**

1. `authority_appeal` is `yes` for this post.
"""

CALLS = """# Guide: calls

Version: v2. Read `common.md` first.

This guide has one label.

## Shared condition C: the post makes a request

Every label of this guide needs condition C.

Evidence for every label of this guide: required. Quote the span that holds the request.

## `call_amplify`

**Question.** Does the post ask readers to spread a message?

**YES when both are true:**

1. C is met.
2. What is asked is to spread content.
"""

FORMAT = """# Guide: format

Version: v2. Read `common.md` first.

Rule 3 of `common.md` (own voice) does not apply to this guide.

Evidence for every label of this guide: none.

## `news_headline`

**Question.** Is the whole post a press headline?

## `lang`

**Question.** What is the main language of the words of the post?
"""

SUBJECT = """# Guide: subject

Version: v2. Read `common.md` first.

Evidence: required for `endorsement`. None for `political` and `theme`.

## `political`

**Question.** Is the post about political life?

## `theme`

**Question.** What is the main theme of the post?

## `endorsement`

**Question.** Does the post support a named person, party or brand?
"""

FILES = {
    "common.md": COMMON,
    "rhetoric.md": RHETORIC,
    "fallacies.md": FALLACIES,
    "calls.md": CALLS,
    "format.md": FORMAT,
    "subject.md": SUBJECT,
}


def write_guides(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in FILES.items():
        (folder / name).write_text(text, encoding="utf-8")
    return folder


def probe_info(key: str, description: str = "", state: ProbeState = "shown") -> ProbeInfo:
    return ProbeInfo(
        key=key,
        label=key.replace("_", " ").capitalize(),
        description=description or f"Does the post show {key}?",
        family="test",
        state=state,
        possible=None,
        probable=None,
        report="probes",
    )


@dataclass
class ScriptedChat:
    """Answers the item review, the selection review and the zone naming with what the test
    set, and records what it was asked."""

    item: dict[str, object] = field(default_factory=lambda: {"findings": []})
    selection: dict[str, object] = field(default_factory=lambda: {"statement": "Nothing."})
    asked: list[tuple[str, str, int]] = field(default_factory=list)

    def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        self.asked.append((system, user, max_tokens))
        if system.startswith("You review one item"):
            return json.dumps(self.item)
        if system.startswith("You read a sample of posts"):
            return json.dumps(self.selection)
        return json.dumps({"name": "Zone name"})

    def reviews(self) -> int:
        """How many review questions were paid for."""
        return sum(not system.startswith("You name") for system, _, _ in self.asked)

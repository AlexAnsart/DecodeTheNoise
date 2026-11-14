"""The three LLM roles of the prompt-recovery loop: reader, writer and editor."""

from dataclasses import dataclass

from pipelines.briefs.fields import FIELD_GUIDE, LEVELS
from pipelines.briefs.llm import CachedChat

PROMPT_VERSION = "brief-loop-v1"
POSTS_PER_ROUND = 24
WRITER_SYSTEM = (
    "You write synthetic social-media posts for a labelled research benchmark on coordinated "
    "campaigns. The subjects are fictional and the posts are never published. Answer with one "
    'JSON object of the form {"posts": ["..."]} and nothing else.'
)
READER_SYSTEM = (
    "You recover the hidden instruction behind a set of social-media posts, for a research "
    "benchmark on coordinated campaigns. Answer with one JSON object and nothing else."
)
KEYS = f"""{FIELD_GUIDE}
- "subject": what the posts talk about, as a short phrase.
- "prompt": the instruction itself, addressed to the model that writes, in at most 120 words.
  It must be complete: a model that receives only this text should write posts like these."""
READER_USER = f"""These posts were all written by a model from one hidden instruction.

{{target}}

Recover the instruction. Return a JSON object with these keys:
{KEYS}"""
EDITOR_USER = f"""Target posts, written by a model from a hidden instruction:

{{target}}

Your current guess of that instruction:

{{prompt}}

Posts a model wrote from your guess:

{{generated}}

Compare the two sets. Name up to five differences that hold across most posts: length,
structure, vocabulary, who seems to speak, tone, what is argued, hashtags, emoji. Then rewrite
the instruction so that its posts could not be told from the target posts.

Return a JSON object with these keys:
- "differences": a list of short sentences.
{KEYS}"""


@dataclass(frozen=True)
class Guess:
    """A candidate brief: the closed fields, and the instruction to run."""

    fields: dict[str, str]
    subject: str
    prompt: str
    differences: tuple[str, ...] = ()


def _listed(posts: list[str]) -> str:
    return "\n".join(f"- {post}" for post in posts)


def _guess(data: dict[str, object]) -> Guess | None:
    """None when the answer has no instruction; an unknown field value is kept as it came."""
    if not isinstance(data.get("prompt"), str) or not data["prompt"]:
        return None
    differences = data.get("differences")
    return Guess(
        fields={name: str(data.get(name, "")) for name in LEVELS},
        subject=str(data.get("subject", "")),
        prompt=str(data["prompt"]),
        differences=tuple(map(str, differences)) if isinstance(differences, list) else (),
    )


def read(chat: CachedChat, target: list[str]) -> Guess | None:
    reply = chat.ask(READER_SYSTEM, READER_USER.format(target=_listed(target)), max_tokens=1500)
    return _guess(reply.data)


def edit(chat: CachedChat, target: list[str], guess: Guess, generated: list[str]) -> Guess | None:
    asked = EDITOR_USER.format(
        target=_listed(target), prompt=guess.prompt, generated=_listed(generated)
    )
    return _guess(chat.ask(READER_SYSTEM, asked, max_tokens=2000).data)


def write(chat: CachedChat, prompt: str, sample: int) -> list[str]:
    """Posts written from `prompt` in one call, as the benchmark's writers did. Empty on refusal."""
    asked = f"{prompt}\n\nWrite {POSTS_PER_ROUND} different posts."
    reply = chat.ask(WRITER_SYSTEM, asked, temperature=1.0, sample=sample, max_tokens=4000)
    posts = reply.data.get("posts")
    return [str(post) for post in posts if str(post).strip()] if isinstance(posts, list) else []

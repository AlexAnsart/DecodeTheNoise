"""The record of the disagreements that were read: `reports/review/audit.json`.

Whoever reads the disagreements written by `pipelines.review.disagreements` tags each one with
a failure mode here. The record holds post names and tags, never the text of a post; the
report counts the modes from it.
"""

from typing import Literal

from pydantic import BaseModel

AUDIT_FILE = "audit.json"

Kind = Literal["false positive", "miss"]


class Mode(BaseModel):
    name: str
    # Paraphrased: never the words of a post.
    example: str
    # What the product does about it.
    product: str


class ReadCase(BaseModel):
    post: str
    label: str
    kind: Kind
    mode: str


class Audit(BaseModel):
    # The prompt whose answers were read (`prompt_sha256` of the metrics): the record says
    # nothing of the answers of another prompt.
    prompt_sha256: str
    read: list[ReadCase]
    modes: dict[str, Mode]

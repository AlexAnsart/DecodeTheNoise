"""What identifies the weights an Ollama endpoint serves, and where that is remembered."""

from pathlib import Path

import httpx
from pydantic import BaseModel

REVISION_CHARS = 12


class _Tag(BaseModel):
    name: str
    digest: str


class _Tags(BaseModel):
    models: list[_Tag]


def model_revision(api_base: str, model: str) -> str:
    """First hex characters of the digest of `model`: it changes with weights or quantisation."""
    root = api_base.rstrip("/").removesuffix("/v1")
    response = httpx.get(f"{root}/api/tags", timeout=30.0)
    response.raise_for_status()
    wanted = {model, f"{model}:latest"}
    for tag in _Tags.model_validate(response.json()).models:
        if tag.name in wanted:
            return tag.digest[:REVISION_CHARS]
    raise LookupError(f"{model} is not pulled on {root}")


def remember_in_env(env_path: Path, name: str, value: str) -> None:
    """Appends `NAME=value` unless the file already ends up with that value. Other lines stay."""
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = text.splitlines()
    current = [line.split("=", 1)[1].strip() for line in lines if line.startswith(f"{name}=")]
    if current and current[-1] == value:
        return
    # A last line without its newline must not be glued to the one added.
    gap = "" if not text or text.endswith("\n") else "\n"
    with env_path.open("a", encoding="utf-8") as out:
        out.write(f"{gap}{name}={value}\n")

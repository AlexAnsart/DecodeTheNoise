"""Cached calls to the AI Router for the benchmark: one file per call, one ledger of spend.

A call is keyed on the model, both messages, the temperature and a sample number, so a sampled
call can be repeated on purpose and a re-run pays for nothing it already has.
"""

import hashlib
import json
import logging
from dataclasses import dataclass

import httpx
from pydantic import BaseModel

from backend.model_client.llm import ChatClient
from pipelines.paths import DATA
from pipelines.zones.name import RouterSettings

log = logging.getLogger("briefs.llm")

CACHE_DIR = DATA / "llm" / "briefs"
LEDGER = CACHE_DIR / "ledger.jsonl"
# Anthropic models on the Router take no temperature: it is left out and recorded as such.
NO_TEMPERATURE = ("claude",)


class _Cached(BaseModel):
    model: str
    temperature: float | None
    text: str


@dataclass(frozen=True)
class Reply:
    """A parsed JSON answer; `data` is empty when the model returned no valid object."""

    data: dict[str, object]
    fresh: bool


class CachedChat:
    def __init__(self, model: str) -> None:
        settings = RouterSettings()
        self.model = model
        self._client = ChatClient(
            settings.hostinger_router_api_base, settings.hostinger_router_api_key, model, 180.0
        )
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def ask(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        sample: int = 0,
        max_tokens: int = 600,
    ) -> Reply:
        sent = None if self.model.startswith(NO_TEMPERATURE) else temperature
        identity = json.dumps([self.model, system, user, sent, sample, max_tokens])
        path = CACHE_DIR / f"{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]}.json"
        if path.exists():
            cached = _Cached.model_validate_json(path.read_text(encoding="utf-8"))
            return Reply(_parse(cached.text), fresh=False)
        try:
            text, usage = self._client.answer(system, user, max_tokens, sent)
        except httpx.HTTPError as error:
            # Not cached: the next run asks again.
            log.warning("%s call failed: %s", self.model, error)
            return Reply({}, fresh=True)
        path.write_text(
            _Cached(model=self.model, temperature=sent, text=text).model_dump_json(),
            encoding="utf-8",
        )
        with LEDGER.open("a", encoding="utf-8") as out:
            line = {"model": self.model, "in": usage.prompt_tokens, "out": usage.completion_tokens}
            out.write(json.dumps(line) + "\n")
        return Reply(_parse(text), fresh=True)

    def close(self) -> None:
        self._client.close()


def _parse(text: str) -> dict[str, object]:
    start, end = text.find("{"), text.rfind("}")
    try:
        data = json.loads(text[start : end + 1]) if start >= 0 else {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}

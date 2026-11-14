"""The one chat client: an OpenAI-compatible `/chat/completions` route (the Hostinger AI Router).

Every LLM step is pinned: the caller records the model id and its prompt version beside the
output, the temperature is 0 unless the caller samples on purpose, and the answer is asked as a
JSON object the caller parses.
"""

import httpx
from pydantic import BaseModel


class _Message(BaseModel):
    content: str | None = None


class _Choice(BaseModel):
    message: _Message


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0


class _ChatResponse(BaseModel):
    choices: list[_Choice]
    usage: Usage = Usage()


class ChatClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 60.0) -> None:
        self.model = model
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        """The text of the answer, empty when the model returned none."""
        return self.answer(system, user, max_tokens)[0]

    def answer(
        self, system: str, user: str, max_tokens: int = 400, temperature: float | None = 0.0
    ) -> tuple[str, Usage]:
        """The text and what it cost. `temperature=None` leaves it out, for models that fix it."""
        body: dict[str, object] = {
            "model": self.model,
            "max_tokens": max_tokens,
            # Short structured answers need no long reasoning: it only spends the budget.
            "reasoning_effort": "low",
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if temperature is not None:
            body["temperature"] = temperature
        response = self._http.post("/chat/completions", json=body)
        response.raise_for_status()
        parsed = _ChatResponse.model_validate(response.json())
        text = (parsed.choices[0].message.content or "") if parsed.choices else ""
        return text, parsed.usage

    def close(self) -> None:
        self._http.close()

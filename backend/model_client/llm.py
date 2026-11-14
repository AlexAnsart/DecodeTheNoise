"""The one chat client: an OpenAI-compatible `/chat/completions` route (the Hostinger AI Router).

Every LLM step is pinned: the caller records the model id and its prompt version beside the
output, the temperature is 0, and the answer is asked as a JSON object the caller parses.
"""

import httpx
from pydantic import BaseModel


class _Message(BaseModel):
    content: str | None = None


class _Choice(BaseModel):
    message: _Message


class _ChatResponse(BaseModel):
    choices: list[_Choice]


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
        response = self._http.post(
            "/chat/completions",
            json={
                "model": self.model,
                "temperature": 0,
                "max_tokens": max_tokens,
                # Short structured answers need no long reasoning: it only spends the budget.
                "reasoning_effort": "low",
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        response.raise_for_status()
        choices = _ChatResponse.model_validate(response.json()).choices
        return (choices[0].message.content or "") if choices else ""

    def close(self) -> None:
        self._http.close()

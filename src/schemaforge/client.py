"""Small OpenAI-compatible HTTP client."""

from __future__ import annotations

from typing import Any

import httpx

from schemaforge.config import Settings
from schemaforge.errors import ModelAPIError


class OpenAICompatibleClient:
    """Call `/chat/completions` on any compatible provider."""

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self._client = httpx.Client(
            base_url=f"{settings.base_url}/",
            headers={"Authorization": f"Bearer {settings.api_key}"},
            timeout=settings.timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OpenAICompatibleClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def complete_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        schema_name: str = "extraction",
    ) -> str:
        """Request JSON matching a schema using OpenAI structured-output syntax."""
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        }
        try:
            response = self._client.post("chat/completions", json=payload)
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelAPIError(f"Model API request failed: {exc}") from exc
        if not isinstance(content, str) or not content.strip():
            raise ModelAPIError("Model API returned empty content")
        return content

    def health(self) -> bool:
        """Check that the configured API responds to the standard models route."""
        try:
            response = self._client.get("models")
            return response.is_success
        except httpx.HTTPError:
            return False

from __future__ import annotations

from typing import Any

import pytest

from schemaforge.errors import ExtractionError, ModelAPIError
from schemaforge.extractor import Extractor


class StubClient:
    def __init__(self, replies: list[str | Exception]) -> None:
        self.replies = iter(replies)
        self.messages: list[list[dict[str, str]]] = []

    def complete_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        schema_name: str = "extraction",
    ) -> str:
        self.messages.append(messages.copy())
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_extracts_and_normalizes(contact_schema: dict[str, Any]) -> None:
    client = StubClient(['{"name":" Ada  Lovelace ","email":" ADA@EXAMPLE.ORG "}'])
    result = Extractor(client).extract("Ada's details", contact_schema)
    assert result.data == {"name": "Ada Lovelace", "email": "ada@example.org"}
    assert result.attempts == 1


@pytest.mark.parametrize("invalid", ["not json", "[]", '{"name":"Ada"}'])
def test_retries_invalid_output(invalid: str, contact_schema: dict[str, Any]) -> None:
    client = StubClient([invalid, '{"name":"Ada","email":null}'])
    result = Extractor(client, max_retries=1).extract("Ada", contact_schema)
    assert result.attempts == 2
    assert "Validation error" in client.messages[1][-1]["content"]


def test_raises_after_retries(contact_schema: dict[str, Any]) -> None:
    client = StubClient([ModelAPIError("offline"), "{}"])
    with pytest.raises(ExtractionError, match="after 2 attempts"):
        Extractor(client, max_retries=1).extract("Ada", contact_schema)


def test_rejects_empty_text(contact_schema: dict[str, Any]) -> None:
    with pytest.raises(ExtractionError, match="must not be empty"):
        Extractor(StubClient([])).extract("  ", contact_schema)


def test_rejects_invalid_schema() -> None:
    with pytest.raises(ExtractionError, match="Invalid JSON Schema"):
        Extractor(StubClient([])).extract("Ada", {"type": "nonsense"})

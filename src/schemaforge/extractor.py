"""Validated extraction and repair loop."""

from __future__ import annotations

import json
from typing import Any, Protocol

import structlog
from jsonschema import Draft202012Validator, SchemaError, ValidationError

from schemaforge.errors import ExtractionError, ModelAPIError
from schemaforge.models import ExtractionResult
from schemaforge.normalization import normalize_data

logger = structlog.get_logger(__name__)


class CompletionClient(Protocol):
    """Port implemented by an OpenAI-compatible model adapter."""

    def complete_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        schema_name: str = "extraction",
    ) -> str: ...


class Extractor:
    """Extract, normalize, validate, and ask the model to repair failures."""

    def __init__(self, client: CompletionClient, max_retries: int = 2) -> None:
        self.client = client
        self.max_retries = max_retries

    def extract(self, text: str, schema: dict[str, Any]) -> ExtractionResult:
        if not text.strip():
            raise ExtractionError("Input text must not be empty")
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            raise ExtractionError(f"Invalid JSON Schema: {exc.message}") from exc

        messages = self._initial_messages(text)
        last_error = "unknown validation error"
        for attempt in range(1, self.max_retries + 2):
            try:
                raw = self.client.complete_json(messages, schema)
                data = normalize_data(self._parse_json(raw))
                Draft202012Validator(schema).validate(data)
                logger.info("extraction_succeeded", attempt=attempt)
                return ExtractionResult(data=data, attempts=attempt)
            except (json.JSONDecodeError, ValidationError, ModelAPIError) as exc:
                last_error = self._describe_error(exc)
                logger.warning("extraction_attempt_failed", attempt=attempt, error=last_error)
                if attempt <= self.max_retries:
                    messages.extend(
                        self._repair_messages(raw if "raw" in locals() else "", last_error)
                    )

        raise ExtractionError(
            f"Could not produce schema-valid JSON after {self.max_retries + 1} attempts: "
            f"{last_error}"
        )

    @staticmethod
    def _initial_messages(text: str) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "Extract factual data from the user text. Return only one JSON object. "
                    "Do not invent values; use null only when the schema permits it."
                ),
            },
            {"role": "user", "content": text},
        ]

    @staticmethod
    def _repair_messages(raw: str, error: str) -> list[dict[str, str]]:
        return [
            {"role": "assistant", "content": raw},
            {
                "role": "user",
                "content": (
                    "The previous JSON was invalid. Correct it and return only JSON. "
                    f"Validation error: {error}"
                ),
            },
        ]

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise json.JSONDecodeError("Expected a JSON object", raw, 0)
        return value

    @staticmethod
    def _describe_error(exc: Exception) -> str:
        if isinstance(exc, ValidationError):
            path = ".".join(str(part) for part in exc.absolute_path) or "$"
            return f"{path}: {exc.message}"
        return str(exc)

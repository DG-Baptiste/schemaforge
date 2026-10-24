"""Pydantic models used at the application boundary."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InputRecord(BaseModel):
    """One JSONL input item."""

    model_config = ConfigDict(extra="allow")

    id: str | int | None = None
    text: str = Field(min_length=1)


class OutputRecord(BaseModel):
    """One JSONL/Parquet output item."""

    id: str | int | None
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    attempts: int = Field(ge=1)


class ExtractionResult(BaseModel):
    """Validated extraction result and diagnostic metadata."""

    data: dict[str, Any]
    attempts: int = Field(ge=1)

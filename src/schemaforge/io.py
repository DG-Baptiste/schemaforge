"""Streaming JSONL input and JSONL/Parquet output."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError

from schemaforge.errors import SchemaForgeError
from schemaforge.models import InputRecord, OutputRecord


def read_schema(path: Path) -> dict[str, Any]:
    """Read a JSON Schema and require an object at its root."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaForgeError(f"Cannot read schema {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SchemaForgeError("JSON Schema root must be an object")
    return value


def read_jsonl(path: Path) -> Iterator[tuple[int, InputRecord]]:
    """Yield validated records with one-based line numbers."""
    try:
        with path.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    yield number, InputRecord.model_validate_json(line)
                except ValidationError as exc:
                    raise SchemaForgeError(f"Invalid input on line {number}: {exc}") from exc
    except OSError as exc:
        raise SchemaForgeError(f"Cannot read input {path}: {exc}") from exc


def write_jsonl(records: Iterable[OutputRecord], path: Path) -> None:
    """Write records incrementally as UTF-8 JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(record.model_dump_json(exclude_none=True) + "\n")


def write_parquet(records: Iterable[OutputRecord], path: Path) -> None:
    """Write flattened metadata plus extracted fields to Parquet."""
    rows: list[dict[str, Any]] = []
    for record in records:
        row: dict[str, Any] = {
            "id": None if record.id is None else str(record.id),
            "ok": record.ok,
            "error": record.error,
            "attempts": record.attempts,
        }
        row.update(record.data or {})
        rows.append(row)
    if not rows:
        raise SchemaForgeError("Cannot write an empty Parquet dataset")
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)

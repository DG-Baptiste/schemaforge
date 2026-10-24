from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from schemaforge.errors import SchemaForgeError
from schemaforge.io import read_jsonl, read_schema, write_jsonl, write_parquet
from schemaforge.models import OutputRecord


def test_read_schema(tmp_path: Path) -> None:
    path = tmp_path / "schema.json"
    path.write_text('{"type":"object"}', encoding="utf-8")
    assert read_schema(path)["type"] == "object"


def test_read_jsonl_skips_blanks(tmp_path: Path) -> None:
    path = tmp_path / "input.jsonl"
    path.write_text('\n{"id":1,"text":"hello"}\n', encoding="utf-8")
    assert [(line, item.text) for line, item in read_jsonl(path)] == [(2, "hello")]


def test_read_jsonl_reports_line(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"text":""}\n', encoding="utf-8")
    with pytest.raises(SchemaForgeError, match="line 1"):
        list(read_jsonl(path))


def test_writers(tmp_path: Path) -> None:
    records = [OutputRecord(id=1, ok=True, data={"name": "Ada"}, attempts=1)]
    jsonl = tmp_path / "out.jsonl"
    parquet = tmp_path / "out.parquet"
    write_jsonl(records, jsonl)
    assert json.loads(jsonl.read_text())["data"]["name"] == "Ada"
    write_parquet(records, parquet)
    assert pq.read_table(parquet).to_pylist()[0]["name"] == "Ada"


def test_empty_parquet_fails(tmp_path: Path) -> None:
    with pytest.raises(SchemaForgeError, match="empty"):
        write_parquet([], tmp_path / "empty.parquet")

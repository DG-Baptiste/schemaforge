from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from schemaforge.batch import AsyncBatchProcessor
from schemaforge.cli import _resolve_schema, _write_output
from schemaforge.domain import Vacancy
from schemaforge.eval import evaluate_predictions
from schemaforge.models import ExtractionResult, InputRecord, OutputRecord
from schemaforge.schema_loader import compile_model, load_schema


def test_vacancy_validators() -> None:
    vacancy = Vacancy(title="Engineer", company="Acme", salary_min=10, salary_max=20)
    assert vacancy.salary_min == 10
    with pytest.raises(ValueError, match="salary_max"):
        Vacancy(title="Engineer", company="Acme", salary_min=20, salary_max=10)


def test_dynamic_yaml_schema(tmp_path: Path) -> None:
    path = tmp_path / "schema.yaml"
    path.write_text(
        "type: object\nproperties:\n  score:\n    type: number\n"
        "    minimum: 0\nrequired: [score]\n",
        encoding="utf-8",
    )
    schema = load_schema(path)
    model = compile_model(schema)
    assert model(score=2).score == 2
    with pytest.raises(ValueError):
        model(score=-1)


def test_evaluation_metrics() -> None:
    inputs = [InputRecord(id="1", text="x")]
    metrics = evaluate_predictions(
        inputs,
        [{"name": "Ada", "email": "wrong"}],
        [{"name": "Ada", "email": "right"}],
    )
    assert metrics.records == 1
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5


class FakeExtractor:
    max_retries = 2

    def extract(self, text: str, schema: dict[str, object]) -> ExtractionResult:
        return ExtractionResult(data={"value": text}, attempts=1)


def test_async_batch_checkpoint(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint.jsonl"
    records = [InputRecord(id="1", text="one"), InputRecord(id="2", text="two")]
    processor = AsyncBatchProcessor(
        FakeExtractor(), {}, max_concurrency=2, checkpoint_path=checkpoint
    )  # type: ignore[arg-type]
    results, stats = asyncio.run(processor.process(records))
    assert len(results) == 2
    assert stats.succeeded == 2
    assert stats.resumed == 0
    results_again, stats_again = asyncio.run(processor.process(records))
    assert len(results_again) == 2
    assert stats_again.resumed == 2


def test_cli_helpers(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text('{"type":"object"}', encoding="utf-8")
    assert _resolve_schema(schema_path) == schema_path
    output = tmp_path / "records.jsonl"
    _write_output([OutputRecord(id="1", ok=True, data={"x": 1}, attempts=1)], output, "jsonl")
    assert output.exists()

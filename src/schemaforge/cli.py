"""Command-line interface."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated, Any

import typer

from schemaforge.batch import AsyncBatchProcessor
from schemaforge.client import OpenAICompatibleClient
from schemaforge.config import Settings
from schemaforge.domain import Vacancy
from schemaforge.errors import SchemaForgeError
from schemaforge.eval import evaluate_predictions
from schemaforge.extractor import Extractor
from schemaforge.io import read_jsonl, read_schema, write_jsonl, write_parquet
from schemaforge.logging import configure_logging
from schemaforge.schema_loader import compile_model

app = typer.Typer(no_args_is_help=True, help="Extract schema-valid data from unstructured text.")


def _settings() -> Settings:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    return settings


def _resolve_schema(value: Path) -> Path:
    """Allow `--schema job` as shorthand for schemas/job.yaml or .json."""
    if value.exists():
        return value
    for candidate in (Path("schemas") / f"{value}.yaml", Path("schemas") / f"{value}.json"):
        if candidate.exists():
            return candidate
    raise SchemaForgeError(f"Schema not found: {value}")


def _write_output(records: list[Any], output_path: Path, output_format: str) -> None:
    if output_format == "parquet":
        write_parquet(records, output_path)
    else:
        write_jsonl(records, output_path)


@app.command("schema")
def show_schema(
    name: Annotated[str, typer.Argument(help="Schema name or path.")] = "vacancy",
) -> None:
    """Print the generated JSON Schema for a Pydantic or YAML model."""
    if name == "vacancy":
        typer.echo(json.dumps(Vacancy.model_json_schema(), ensure_ascii=False, indent=2))
        return
    resolved = _resolve_schema(Path(name))
    model = compile_model(read_schema(resolved), resolved.stem)
    typer.echo(json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2))


def _run_batch(
    input_path: Path,
    output_path: Path,
    schema_path: Path,
    output_format: str,
    mode: str,
    concurrency: int,
    checkpoint: Path | None,
) -> None:
    settings = _settings()
    resolved_schema = _resolve_schema(schema_path)
    json_schema = read_schema(resolved_schema)
    validator_model = compile_model(json_schema, resolved_schema.stem)
    inputs = [record for _, record in read_jsonl(input_path)]
    with OpenAICompatibleClient(settings) as client:
        extractor = Extractor(
            client, settings.max_retries, mode=mode, validator_model=validator_model
        )
        processor = AsyncBatchProcessor(extractor, json_schema, concurrency, checkpoint)
        records, stats = asyncio.run(processor.process(inputs))
    _write_output(records, output_path, output_format)
    typer.echo(
        f"Processed {stats.total} records: {stats.succeeded} succeeded, "
        f"{stats.failed} failed, {stats.resumed} resumed."
    )


@app.command()
def extract(
    text: Annotated[str | None, typer.Argument(help="Text, or 'run'/'eval' for workflows.")] = None,
    schema: Annotated[Path, typer.Option("--schema", "-s", dir_okay=False)] = Path(
        "schemas/vacancy.yaml"
    ),
    input_path: Annotated[Path | None, typer.Option("--in", exists=True, dir_okay=False)] = None,
    output_path: Annotated[Path | None, typer.Option("--out", dir_okay=False)] = None,
    gold_path: Annotated[Path | None, typer.Option("--gold", exists=True, dir_okay=False)] = None,
    output_format: Annotated[str, typer.Option("--format", "-f")] = "jsonl",
    mode: Annotated[str, typer.Option("--mode")] = "schema",
    concurrency: Annotated[int, typer.Option("--concurrency", min=1, max=32)] = 4,
    checkpoint: Annotated[Path | None, typer.Option("--checkpoint")] = None,
) -> None:
    """Extract one object, run a batch, or evaluate predictions."""
    try:
        if text in {"run", "eval"} or input_path is not None:
            if input_path is None:
                raise SchemaForgeError("--in is required for run/eval")
            if text == "eval":
                if gold_path is None:
                    raise SchemaForgeError("--gold is required for eval")
                _run_eval(input_path, gold_path, schema, mode, concurrency)
                return
            if output_path is None:
                raise SchemaForgeError("--out is required for run")
            _run_batch(
                input_path, output_path, schema, output_format, mode, concurrency, checkpoint
            )
            return
        if not text:
            raise SchemaForgeError("Text is required")
        settings = _settings()
        resolved_schema = _resolve_schema(schema)
        json_schema = read_schema(resolved_schema)
        validator_model = compile_model(json_schema, resolved_schema.stem)
        with OpenAICompatibleClient(settings) as client:
            result = Extractor(
                client, settings.max_retries, mode=mode, validator_model=validator_model
            ).extract(text, json_schema)
        typer.echo(json.dumps(result.data, ensure_ascii=False, indent=2))
    except SchemaForgeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def batch(
    input_path: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    output_path: Annotated[Path, typer.Argument(dir_okay=False)],
    schema: Annotated[Path, typer.Option("--schema", "-s", dir_okay=False)],
    output_format: Annotated[str, typer.Option("--format", "-f")] = "jsonl",
) -> None:
    """Process a JSONL file; failures are recorded without stopping the batch."""
    if output_format not in {"jsonl", "parquet"}:
        typer.echo("--format must be 'jsonl' or 'parquet'", err=True)
        raise typer.Exit(code=2)
    try:
        _run_batch(input_path, output_path, schema, output_format, "schema", 4, None)
    except SchemaForgeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def _run_eval(
    input_path: Path, gold_path: Path, schema_path: Path, mode: str, concurrency: int
) -> None:
    """Run extraction and compare fields with a JSONL gold file."""
    settings = _settings()
    inputs = [record for _, record in read_jsonl(input_path)]
    gold: list[dict[str, Any]] = []
    for line in gold_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            gold.append(value["gold"])
    resolved_schema = _resolve_schema(schema_path)
    json_schema = read_schema(resolved_schema)
    validator_model = compile_model(json_schema, resolved_schema.stem)
    with OpenAICompatibleClient(settings) as client:
        extractor = Extractor(
            client, settings.max_retries, mode=mode, validator_model=validator_model
        )
        processor = AsyncBatchProcessor(extractor, json_schema, concurrency)
        results, _ = asyncio.run(processor.process(inputs))
    predictions = [result.data or {} for result in results]
    metrics = evaluate_predictions(inputs, predictions, gold)
    typer.echo(
        f"records={metrics.records} precision={metrics.precision:.3f} recall={metrics.recall:.3f}"
    )


@app.command()
def health() -> None:
    """Check connectivity to the configured model API."""
    settings = _settings()
    with OpenAICompatibleClient(settings) as client:
        healthy = client.health()
    typer.echo("ok" if healthy else "unavailable")
    if not healthy:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

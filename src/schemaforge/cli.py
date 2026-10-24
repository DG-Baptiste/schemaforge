"""Command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from schemaforge.client import OpenAICompatibleClient
from schemaforge.config import Settings
from schemaforge.errors import SchemaForgeError
from schemaforge.extractor import Extractor
from schemaforge.io import read_jsonl, read_schema, write_jsonl, write_parquet
from schemaforge.logging import configure_logging
from schemaforge.service import process_record

app = typer.Typer(no_args_is_help=True, help="Extract schema-valid data from unstructured text.")


def _settings() -> Settings:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    return settings


@app.command()
def extract(
    text: Annotated[str, typer.Argument(help="Text to extract data from.")],
    schema: Annotated[Path, typer.Option("--schema", "-s", exists=True, dir_okay=False)],
) -> None:
    """Extract one JSON object and write it to standard output."""
    try:
        settings = _settings()
        with OpenAICompatibleClient(settings) as client:
            result = Extractor(client, settings.max_retries).extract(text, read_schema(schema))
        typer.echo(json.dumps(result.data, ensure_ascii=False, indent=2))
    except SchemaForgeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def batch(
    input_path: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    output_path: Annotated[Path, typer.Argument(dir_okay=False)],
    schema: Annotated[Path, typer.Option("--schema", "-s", exists=True, dir_okay=False)],
    output_format: Annotated[str, typer.Option("--format", "-f")] = "jsonl",
) -> None:
    """Process a JSONL file; failures are recorded without stopping the batch."""
    if output_format not in {"jsonl", "parquet"}:
        typer.echo("--format must be 'jsonl' or 'parquet'", err=True)
        raise typer.Exit(code=2)
    try:
        settings = _settings()
        json_schema = read_schema(schema)
        with OpenAICompatibleClient(settings) as client:
            extractor = Extractor(client, settings.max_retries)
            records = [
                process_record(record, extractor, json_schema)
                for _, record in read_jsonl(input_path)
            ]
        if output_format == "parquet":
            write_parquet(records, output_path)
        else:
            write_jsonl(records, output_path)
        succeeded = sum(record.ok for record in records)
        typer.echo(
            f"Processed {len(records)} records: {succeeded} succeeded, "
            f"{len(records) - succeeded} failed."
        )
    except SchemaForgeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


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

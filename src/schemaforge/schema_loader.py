"""Load JSON/YAML schemas and compile a practical Pydantic model dynamically."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from pydantic import ConfigDict, Field, create_model

from schemaforge.errors import SchemaForgeError


def load_schema(path: Path) -> dict[str, Any]:
    """Load a JSON or YAML object schema."""
    try:
        raw = path.read_text(encoding="utf-8")
        value = yaml.safe_load(raw) if path.suffix.lower() in {".yaml", ".yml"} else json.loads(raw)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise SchemaForgeError(f"Cannot read schema {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SchemaForgeError("Schema root must be an object")
    return value


def compile_model(schema: dict[str, Any], name: str = "DynamicRecord") -> type[Any]:
    """Compile a subset of JSON Schema into a Pydantic model with constraints."""
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise SchemaForgeError("Schema properties must be an object")
    required = set(schema.get("required", []))
    fields: dict[str, tuple[type[Any], Any]] = {}
    for field_name, definition in properties.items():
        if not isinstance(definition, dict):
            raise SchemaForgeError(f"Invalid definition for field {field_name}")
        python_type: Any = _python_type(definition)
        default = ... if field_name in required else None
        constraints: dict[str, Any] = {}
        if "minimum" in definition:
            constraints["ge"] = definition["minimum"]
        fields[field_name] = (
            cast(type[Any], python_type),
            Field(default=default, **constraints),
        )
    return cast(
        type[Any],
        create_model(  # type: ignore[call-overload]
            name, __config__=ConfigDict(extra="forbid"), **fields
        ),
    )


def _python_type(definition: dict[str, Any]) -> Any:
    enum = definition.get("enum")
    if enum:
        return Literal[tuple(enum)]
    value_type = definition.get("type")
    if definition.get("format") == "date":
        return date
    if isinstance(value_type, list):
        non_null = [item for item in value_type if item != "null"]
        value_type = non_null[0] if non_null else "null"
        base = _python_type({**definition, "type": value_type})
        return base | None
    result = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "array": list[str],
        "null": type(None),
        "date": date,
    }
    return result.get(cast(str, value_type), dict[str, Any])

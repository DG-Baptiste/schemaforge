"""Application service for fault-tolerant batch extraction."""

from __future__ import annotations

import structlog

from schemaforge.errors import SchemaForgeError
from schemaforge.extractor import Extractor
from schemaforge.models import InputRecord, OutputRecord

logger = structlog.get_logger(__name__)


def process_record(
    record: InputRecord, extractor: Extractor, schema: dict[str, object]
) -> OutputRecord:
    """Process one record while converting domain failures into output data."""
    try:
        result = extractor.extract(record.text, schema)
        return OutputRecord(id=record.id, ok=True, data=result.data, attempts=result.attempts)
    except SchemaForgeError as exc:
        logger.error("record_failed", record_id=record.id, error=str(exc))
        return OutputRecord(
            id=record.id, ok=False, error=str(exc), attempts=extractor.max_retries + 1
        )

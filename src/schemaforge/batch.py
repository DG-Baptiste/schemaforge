"""Asynchronous batch processing with bounded concurrency and checkpoints."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from schemaforge.extractor import Extractor
from schemaforge.models import InputRecord, OutputRecord
from schemaforge.service import process_record

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BatchStats:
    total: int
    succeeded: int
    failed: int
    resumed: int


class AsyncBatchProcessor:
    """Run extraction concurrently without overwhelming a local model server."""

    def __init__(
        self,
        extractor: Extractor,
        schema: dict[str, Any],
        max_concurrency: int = 4,
        checkpoint_path: Path | None = None,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be positive")
        self.extractor = extractor
        self.schema = schema
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.checkpoint_path = checkpoint_path

    async def process(self, records: list[InputRecord]) -> tuple[list[OutputRecord], BatchStats]:
        completed = self._load_checkpoint()
        resumed = sum(1 for record in records if str(record.id) in completed)
        pending = [record for record in records if str(record.id) not in completed]

        async def one(record: InputRecord) -> OutputRecord:
            async with self.semaphore:
                result = await asyncio.to_thread(
                    process_record, record, self.extractor, self.schema
                )
                self._append_checkpoint(record, result)
                return result

        fresh = await asyncio.gather(*(one(record) for record in pending))
        restored = [completed[str(record.id)] for record in records if str(record.id) in completed]
        results = restored + fresh
        stats = BatchStats(
            total=len(results),
            succeeded=sum(item.ok for item in results),
            failed=sum(not item.ok for item in results),
            resumed=resumed,
        )
        logger.info("batch_completed", **stats.__dict__)
        return results, stats

    def _load_checkpoint(self) -> dict[str, OutputRecord]:
        if self.checkpoint_path is None or not self.checkpoint_path.exists():
            return {}
        result: dict[str, OutputRecord] = {}
        for line in self.checkpoint_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = OutputRecord.model_validate_json(line)
                result[str(record.id)] = record
        return result

    def _append_checkpoint(self, record: InputRecord, result: OutputRecord) -> None:
        if self.checkpoint_path is None:
            return
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with self.checkpoint_path.open("a", encoding="utf-8") as stream:
            stream.write(result.model_dump_json(exclude_none=True) + "\n")

from __future__ import annotations

from schemaforge.errors import ExtractionError
from schemaforge.models import ExtractionResult, InputRecord
from schemaforge.service import process_record


class FakeExtractor:
    max_retries = 2

    def __init__(self, error: bool = False) -> None:
        self.error = error

    def extract(self, text: str, schema: dict[str, object]) -> ExtractionResult:
        if self.error:
            raise ExtractionError("bad model")
        return ExtractionResult(data={"value": text}, attempts=1)


def test_process_record_success() -> None:
    result = process_record(InputRecord(id="1", text="hello"), FakeExtractor(), {})  # type: ignore[arg-type]
    assert result.ok and result.data == {"value": "hello"}


def test_process_record_failure() -> None:
    result = process_record(InputRecord(id="1", text="hello"), FakeExtractor(True), {})  # type: ignore[arg-type]
    assert not result.ok and result.attempts == 3

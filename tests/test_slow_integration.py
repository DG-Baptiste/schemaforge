from __future__ import annotations

import os

import pytest

from schemaforge.client import OpenAICompatibleClient
from schemaforge.config import Settings
from schemaforge.extractor import Extractor


@pytest.mark.slow
@pytest.mark.skipif(not os.getenv("RUN_SLOW_TESTS"), reason="set RUN_SLOW_TESTS=1")
def test_real_model() -> None:
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    }
    settings = Settings.from_env()
    with OpenAICompatibleClient(settings) as client:
        result = Extractor(client).extract("The person's name is Ada.", schema)
    assert result.data["name"] == "Ada"

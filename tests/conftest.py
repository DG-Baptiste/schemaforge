from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def contact_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string"},
            "email": {"type": ["string", "null"]},
        },
        "required": ["name", "email"],
    }

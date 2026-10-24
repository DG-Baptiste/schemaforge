from __future__ import annotations

import pytest

from schemaforge.normalization import normalize_data


@pytest.mark.parametrize(
    ("key", "raw", "expected"),
    [
        ("name", "  Ada   Lovelace ", "Ada Lovelace"),
        ("email", " ADA@Example.ORG ", "ada@example.org"),
        ("work_email_address", " A@B.COM ", "a@b.com"),
        ("phone", "+44 (0) 12-34", "+4401234"),
    ],
)
def test_normalize_string(key: str, raw: str, expected: str) -> None:
    assert normalize_data(raw, key) == expected


def test_normalize_nested_values() -> None:
    assert normalize_data({"people": [{"email": " A@B.COM "}], "count": 1}) == {
        "people": [{"email": "a@b.com"}],
        "count": 1,
    }

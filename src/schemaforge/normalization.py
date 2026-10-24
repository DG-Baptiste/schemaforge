"""Deterministic post-processing for common textual fields."""

from __future__ import annotations

import re
from typing import Any

_WHITESPACE = re.compile(r"\s+")
_PHONE_CHARS = re.compile(r"[^\d+]")
_EMAIL_KEY = re.compile(r"(^|_)email($|_)", re.IGNORECASE)
_PHONE_KEY = re.compile(r"(^|_)(phone|telephone|mobile)($|_)", re.IGNORECASE)


def normalize_data(value: Any, key: str = "") -> Any:
    """Recursively normalize strings while preserving unknown schema shapes."""
    if isinstance(value, dict):
        return {item_key: normalize_data(item, item_key) for item_key, item in value.items()}
    if isinstance(value, list):
        return [normalize_data(item, key) for item in value]
    if not isinstance(value, str):
        return value

    normalized = _WHITESPACE.sub(" ", value).strip()
    if _EMAIL_KEY.search(key):
        return normalized.lower()
    if _PHONE_KEY.search(key):
        return _PHONE_CHARS.sub("", normalized)
    return normalized

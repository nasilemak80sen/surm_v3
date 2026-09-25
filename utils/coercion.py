"""Small, defensive type coercion helpers for interactive and legacy study data."""

from __future__ import annotations

from typing import Any


def safe_int(value: Any, default: int = 0) -> int:
    """Convert numeric-looking values to int without leaking TypeError/ValueError."""
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    try:
        text = str(value).strip()
        if not text:
            return default
        return int(float(text))
    except (TypeError, ValueError, OverflowError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert numeric-looking values to float without leaking conversion errors."""
    if value is None:
        return default
    if isinstance(value, bool):
        return float(value)
    try:
        text = str(value).strip()
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError, OverflowError):
        return default

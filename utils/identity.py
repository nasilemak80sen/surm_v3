"""Stable display-identity validation helpers for SURM editor inputs."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def duplicate_values(rows: list[dict[str, Any]], field: str) -> list[str]:
    """Return non-empty duplicate display values, case-insensitively."""
    seen: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = str(row.get(field, "") or "").strip()
        if value:
            seen[value.casefold()].append(value)

    return [
        values[0]
        for values in seen.values()
        if len(values) > 1
    ]


def duplicate_message(rows: list[dict[str, Any]], field: str) -> str:
    """Return a compact human-readable duplicate validation message."""
    duplicates = duplicate_values(rows, field)
    if not duplicates:
        return ""
    labels = ", ".join(f'"{value}"' for value in duplicates[:5])
    suffix = "…" if len(duplicates) > 5 else ""
    return f"Duplicate {field} value(s) are not allowed: {labels}{suffix}"

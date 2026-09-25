"""Study revision history and deterministic diff utilities."""

from __future__ import annotations

from typing import Any

from utils.db import get_db


DIFF_KEYS = (
    "project_name",
    "field_name",
    "project_phase",
    "study_lifecycle",
    "team_members",
    "uncertainties",
    "key_decisions",
    "impact_assessment",
    "key_uncertainties",
    "resolution_list",
    "resolution_planner",
    "risk_register",
    "bowtie_register",
    "barrier_register",
    "study_reviews",
)


def list_revisions(project_name: str, field_name: str) -> list[dict[str, Any]]:
    return get_db().list_versions(project_name, field_name)


def load_revision(project_name: str, field_name: str, revision: int) -> dict[str, Any]:
    return get_db().load_version(project_name, field_name, int(revision))


def _shape(value: Any) -> str:
    if isinstance(value, dict):
        return f"dict({len(value)})"
    if isinstance(value, list):
        return f"list({len(value)})"
    if value is None:
        return "empty"
    text = str(value).strip()
    return text[:120] + ("…" if len(text) > 120 else "")


def diff_revisions(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, str]]:
    old_session = old.get("session", {}) if isinstance(old, dict) else {}
    new_session = new.get("session", {}) if isinstance(new, dict) else {}
    rows = []

    for key in DIFF_KEYS:
        before = old_session.get(key)
        after = new_session.get(key)
        if before == after:
            continue
        rows.append({
            "Field": key.replace("_", " ").title(),
            "Before": _shape(before),
            "After": _shape(after),
        })

    return rows


def revision_summary(record: dict[str, Any]) -> dict[str, Any]:
    session = record.get("session", {})
    return {
        "revision": int(session.get("study_revision", record.get("meta", {}).get("study_revision", 0)) or 0),
        "lifecycle": str(session.get("study_lifecycle", "Draft")),
        "saved_at": record.get("meta", {}).get("saved_at", ""),
        "project_name": str(session.get("project_name", "")),
        "field_name": str(session.get("field_name", "")),
    }

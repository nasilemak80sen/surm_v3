"""Governance and assurance rules for SURM study lifecycle."""

from __future__ import annotations

from typing import Any

from utils.intelligence import build_bowtie_qa
from utils.workflow import stage_results


LIFECYCLE_ORDER = ["Draft", "In Review", "Reviewed", "Approved", "Archived"]
ROLE_RANK = {"Viewer": 0, "Author": 1, "Reviewer": 2, "Approver": 3}


def signoff_complete(session: dict[str, Any]) -> bool:
    required = (
        "prep_name", "prep_role", "prep_date",
        "rev_gg_name", "rev_gg_role", "rev_gg_date",
        "rev_re_name", "rev_re_role", "rev_re_date",
        "rev_pp_name", "rev_pp_role", "rev_pp_date",
        "endorsed_name", "endorsed_role", "endorsed_date",
    )
    return all(str(session.get(key, "")).strip() for key in required)


def approval_readiness(session: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    stages = stage_results(session)
    if not all(stage.complete for stage in stages):
        reasons.append("All core workflow stages must be complete.")
    if not signoff_complete(session):
        reasons.append("All governance sign-offs must be completed.")
    risks = [
        row for row in session.get("risk_register", [])
        if isinstance(row, dict) and str(row.get("risk_id", "")).strip()
    ]
    bowties = session.get("bowtie_register", {}) or {}
    missing_bowties = [
        row.get("risk_id", "")
        for row in risks
        if str(row.get("risk_id", "")).strip() not in bowties
    ]
    if missing_bowties:
        reasons.append(f"Create Bowtie documents for {len(missing_bowties)} assessed risk(s).")

    qa = build_bowtie_qa(session)
    if qa:
        reasons.append(f"Resolve {len(qa)} Bowtie assurance finding(s).")
    return not reasons, reasons


def validate_transition(
    session: dict[str, Any],
    target: str,
) -> tuple[bool, list[str]]:
    current = str(session.get("study_lifecycle", "Draft"))
    role = str(session.get("study_role", "Author"))
    errors: list[str] = []

    if target not in LIFECYCLE_ORDER:
        return False, [f"Unknown lifecycle state: {target}."]

    if current not in LIFECYCLE_ORDER:
        current = "Draft"

    if LIFECYCLE_ORDER.index(target) < LIFECYCLE_ORDER.index(current):
        errors.append("Lifecycle cannot move backward.")

    if target == "In Review" and not all(stage.complete for stage in stage_results(session)):
        errors.append("Complete the core workflow before entering review.")

    if target == "Reviewed" and ROLE_RANK.get(role, 0) < ROLE_RANK["Reviewer"]:
        errors.append("Reviewer or Approver study role is required to record Reviewed.")

    if target == "Approved":
        if role != "Approver":
            errors.append("Approver study role is required to approve the study.")
        ready, reasons = approval_readiness(session)
        if not ready:
            errors.extend(reasons)

    if target == "Archived" and role != "Approver":
        errors.append("Approver study role is required to archive the study.")

    return not errors, errors


def study_is_editable(session: dict[str, Any]) -> bool:
    """Return whether the current governance mode should allow edits."""
    if str(session.get("study_access_mode", "edit")) != "edit":
        return False
    if str(session.get("study_role", "Author")) == "Viewer":
        return False
    if str(session.get("study_lifecycle", "Draft")) == "Archived":
        return False
    return True

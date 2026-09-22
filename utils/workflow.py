"""Workflow state, validation, and downstream invalidation for SURM.

This module is intentionally UI-agnostic. It answers:
- what the user has completed,
- what is currently available,
- what still needs attention,
- and which downstream outputs must be invalidated when an upstream stage changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WorkflowStage:
    key: str
    label: str
    complete: bool
    available: bool
    reason: str = ""
    guidance: str = ""

    @property
    def state(self) -> str:
        if self.complete:
            return "Complete"
        if not self.available:
            return "Blocked"
        return "In Progress"


STAGES = (
    ("uncertainties", "Uncertainties"),
    ("key_decisions", "Key Decisions"),
    ("impact_assessment", "Impact Assessment"),
    ("key_uncertainties", "Key Uncertainties"),
    ("resolution_list", "Resolution List"),
    ("resolution_planner", "Resolution Planner"),
    ("risk_register", "Risk Register"),
    ("pra_output", "PRA Output"),
)

# Direct downstream dependencies. The values are state keys, not UI labels.
DOWNSTREAM_STATE = {
    "uncertainties": (
        "impact_assessment",
        "key_uncertainties",
        "resolution_list",
        "resolution_planner",
        "risk_register",
        "pra_output",
    ),
    "key_decisions": (
        "impact_assessment",
        "key_uncertainties",
        "resolution_list",
        "resolution_planner",
        "risk_register",
        "pra_output",
    ),
    "impact_assessment": (
        "key_uncertainties",
        "resolution_list",
        "resolution_planner",
        "risk_register",
        "pra_output",
    ),
    "key_uncertainties": (
        "resolution_list",
        "resolution_planner",
        "risk_register",
        "pra_output",
    ),
    "resolution_list": (
        "resolution_planner",
        "risk_register",
        "pra_output",
    ),
    "resolution_planner": (
        "risk_register",
        "pra_output",
    ),
    "risk_register": (
        "pra_output",
    ),
}


def _selected_uncertainties(session: dict[str, Any]) -> int:
    return sum(
        1
        for item in session.get("uncertainties", [])
        if isinstance(item, dict) and item.get("selected")
    )


def _selected_uncertainty_names(session: dict[str, Any]) -> set[str]:
    return {
        str(item.get("name", "")).strip()
        for item in session.get("uncertainties", [])
        if isinstance(item, dict) and item.get("selected") and item.get("name")
    }


def _decision_names(session: dict[str, Any]) -> list[str]:
    return [
        str(item.get("Key Decision", "")).strip()
        for item in session.get("key_decisions", [])
        if isinstance(item, dict)
        and str(item.get("Key Decision", "")).strip()
    ]


def _decision_count(session: dict[str, Any]) -> int:
    return len(_decision_names(session))


def _active_decision_names(session: dict[str, Any]) -> list[str]:
    return [
        str(item.get("Key Decision", "")).strip()
        for item in session.get("key_decisions", [])
        if isinstance(item, dict)
        and str(item.get("Key Decision", "")).strip()
        and int(item.get("Weight (1-3)", 0) or 0) >= 1
    ]


def _impact_complete(session: dict[str, Any]) -> tuple[bool, str]:
    selected = _selected_uncertainty_names(session)
    decisions = _active_decision_names(session)
    rows = {
        str(row.get("Uncertainty", "")).strip(): row
        for row in session.get("impact_assessment", [])
        if isinstance(row, dict)
    }

    if not selected:
        return False, "Select at least one uncertainty first."
    if not decisions:
        return False, "Define at least one weighted key decision first."

    missing_rows = selected - rows.keys()
    if missing_rows:
        return (
            False,
            f"{len(missing_rows)} selected uncertainties are missing an impact assessment.",
        )

    for name in selected:
        row = rows[name]
        degree = str(row.get("Degree of Uncertainty", "") or "").strip().upper()
        if degree not in {"H", "M", "L"}:
            return False, f'"{name}" needs a Degree of Uncertainty rating.'

        for decision in decisions:
            value = str(row.get(decision, "") or "").strip().upper()
            if value not in {"H", "M", "L", "NA"}:
                return (
                    False,
                    f'"{name}" needs a valid impact rating for "{decision}".',
                )

    return True, ""


def _key_uncertainties_complete(session: dict[str, Any]) -> tuple[bool, str]:
    impact_ready, impact_reason = _impact_complete(session)
    if not impact_ready:
        return False, impact_reason

    selected_names = _selected_uncertainty_names(session)
    key_uncertainties = {
        str(row.get("Uncertainty", "")).strip(): row
        for row in session.get("key_uncertainties", [])
        if isinstance(row, dict)
    }

    if not selected_names.issubset(key_uncertainties.keys()):
        return (
            False,
            "Review and apply the ranked Key Uncertainties list before continuing.",
        )

    if not any(
        row.get("Include in Plan")
        for row in key_uncertainties.values()
    ):
        return False, "Include at least one key uncertainty in the plan."

    return True, ""


def _resolution_coverage(
    session: dict[str, Any],
) -> tuple[bool, str, list[str]]:
    selected = [
        row
        for row in session.get("key_uncertainties", [])
        if isinstance(row, dict) and row.get("Include in Plan")
    ]
    resolution_list = session.get("resolution_list", {}) or {}
    options = (
        session.get("_mapping", {})
        .get("resolution_options", [])
    )

    uncovered: list[str] = []

    for row in selected:
        name = str(row.get("Uncertainty", "")).strip()
        values = resolution_list.get(name, {})
        if not any(values.get(option) == "Y" for option in options):
            uncovered.append(name)

    if uncovered:
        return (
            False,
            (
                f"{len(uncovered)} key uncertainties have no selected "
                "resolution action."
            ),
            uncovered,
        )

    return True, "", []


def _resolution_planner_complete(session: dict[str, Any]) -> tuple[bool, str]:
    coverage_ok, coverage_reason, _ = _resolution_coverage(session)
    if not coverage_ok:
        return False, coverage_reason

    planner = [
        row for row in session.get("resolution_planner", [])
        if isinstance(row, dict)
    ]
    if not planner:
        return False, "Generate at least one resolution planning action."

    workplan_rows = [
        row
        for row in planner
        if row.get("Part of Workplan")
    ]
    if not workplan_rows:
        return False, "Mark at least one resolution action as part of the workplan."

    missing_owner = [
        row.get("Resolution Action", "Unnamed action")
        for row in workplan_rows
        if not str(row.get("Action Owner", "") or "").strip()
    ]
    if missing_owner:
        return (
            False,
            f"{len(missing_owner)} workplan actions still need an Action Owner.",
        )

    return True, ""


def _risk_assessment_complete(session: dict[str, Any]) -> tuple[bool, str]:
    risks = [
        row for row in session.get("risk_register", [])
        if isinstance(row, dict)
    ]
    if not risks:
        return False, "Populate the risk register first."

    unassessed = [
        row.get("Risk", "Unnamed risk")
        for row in risks
        if (
            str(row.get("Likelihood (H/M/L)", "") or "").strip().upper()
            not in {"H", "M", "L"}
            or str(row.get("Impact (H/M/L)", "") or "").strip().upper()
            not in {"H", "M", "L"}
        )
    ]
    if unassessed:
        return (
            False,
            f"{len(unassessed)} risks still need explicit likelihood and impact assessment.",
        )

    missing_governance = [
        row.get("Risk", "Unnamed risk")
        for row in risks
        if (
            not str(row.get("Action Owner", "") or "").strip()
            or not str(row.get("Contingency Plan", "") or "").strip()
            or not str(row.get("Impact/Consequence", "") or "").strip()
        )
    ]
    if missing_governance:
        return (
            False,
            f"{len(missing_governance)} risks still need owner, consequence, and contingency details.",
        )

    return True, ""


def stage_results(session: dict[str, Any]) -> list[WorkflowStage]:
    """Return completion and access state for every study stage."""
    selected = _selected_uncertainties(session)
    decisions = _decision_count(session)

    impact_complete, impact_reason = _impact_complete(session)
    key_uncertainties_complete, key_uncertainties_reason = _key_uncertainties_complete(session)
    resolution_coverage_ok, resolution_reason, _ = _resolution_coverage(session)
    planner_complete, planner_reason = _resolution_planner_complete(session)
    risk_complete, risk_reason = _risk_assessment_complete(session)

    completed = {
        "uncertainties": selected > 0,
        "key_decisions": decisions > 0
        and all(
            str(item.get("Key Decision", "")).strip()
            and int(item.get("Weight (1-3)", 0) or 0) in {1, 2, 3}
            for item in session.get("key_decisions", [])
            if isinstance(item, dict)
            and str(item.get("Key Decision", "")).strip()
        ),
        "impact_assessment": impact_complete,
        "key_uncertainties": key_uncertainties_complete,
        "resolution_list": resolution_coverage_ok
        and any(
            isinstance(item, dict) and item.get("Include in Plan")
            for item in session.get("key_uncertainties", [])
        ),
        "resolution_planner": planner_complete,
        "risk_register": risk_complete,
        "pra_output": risk_complete and bool(session.get("pra_output")),
    }

    prerequisites = {
        "uncertainties": (True, ""),
        "key_decisions": (
            selected > 0,
            "Select at least one uncertainty first.",
        ),
        "impact_assessment": (
            decisions > 0,
            "Define at least one key decision first.",
        ),
        "key_uncertainties": (
            impact_complete,
            impact_reason or "Complete the impact assessment first.",
        ),
        "resolution_list": (
            key_uncertainties_complete,
            key_uncertainties_reason
            or "Identify at least one key uncertainty first.",
        ),
        "resolution_planner": (
            resolution_coverage_ok,
            resolution_reason
            or "Complete resolution coverage first.",
        ),
        "risk_register": (
            planner_complete,
            planner_reason
            or "Create at least one owned workplan action first.",
        ),
        "pra_output": (
            risk_complete,
            risk_reason
            or "Complete the risk register first.",
        ),
    }

    guidance = {
        "uncertainties": (
            "Select the uncertainties that matter for this field and project."
        ),
        "key_decisions": (
            "Confirm the decisions this study needs to support and their weights."
        ),
        "impact_assessment": (
            impact_reason
            or "All selected uncertainties have been rated against the active decisions."
        ),
        "key_uncertainties": (
            key_uncertainties_reason
            or "Review the ranking and choose what carries forward into planning."
        ),
        "resolution_list": (
            resolution_reason
            or "Every included key uncertainty has a selected resolution action."
        ),
        "resolution_planner": (
            planner_reason
            or "At least one owned resolution action is in the workplan."
        ),
        "risk_register": (
            risk_reason
            or "Every generated risk is assessed and has required governance details."
        ),
        "pra_output": (
            risk_reason
            or "PRA output is ready for review."
        ),
    }

    return [
        WorkflowStage(
            key=key,
            label=label,
            complete=completed[key],
            available=prerequisites[key][0],
            reason=prerequisites[key][1]
            if not prerequisites[key][0]
            else "",
            guidance=guidance[key],
        )
        for key, label in STAGES
    ]


def current_stage(session: dict[str, Any]) -> WorkflowStage:
    """Return the first incomplete stage, or the final stage when complete."""
    stages = stage_results(session)
    return next(
        (stage for stage in stages if not stage.complete),
        stages[-1],
    )


def validate_stage(
    session: dict[str, Any],
    stage_key: str,
) -> tuple[bool, str]:
    """Check whether a stage is available based on upstream prerequisites."""
    for stage in stage_results(session):
        if stage.key == stage_key:
            return stage.available, stage.reason
    return False, "Unknown workflow stage."


def completion_percent(session: dict[str, Any]) -> int:
    stages = stage_results(session)
    return round(
        sum(stage.complete for stage in stages)
        / len(stages)
        * 100
    )


def invalidate_downstream(
    session: dict[str, Any],
    stage_key: str,
) -> tuple[str, ...]:
    """Clear all derived state downstream of a changed stage."""
    downstream = DOWNSTREAM_STATE.get(stage_key, ())

    for state_key in downstream:
        if state_key == "resolution_list":
            session[state_key] = {}
        else:
            session[state_key] = []

    return downstream


def mark_stage_changed(
    session: dict[str, Any],
    stage_key: str,
) -> None:
    """Record a stage revision and invalidate its downstream dependants."""
    revisions = dict(session.get("workflow_revisions", {}) or {})
    revisions[stage_key] = int(revisions.get(stage_key, 0) or 0) + 1
    session["workflow_revisions"] = revisions

    snapshots = dict(session.get("workflow_snapshots", {}) or {})
    snapshots[stage_key] = {
        "revision": revisions[stage_key],
    }
    session["workflow_snapshots"] = snapshots

    invalidate_downstream(session, stage_key)


def stage_revision(session: dict[str, Any], stage_key: str) -> int:
    """Return the current revision counter for a stage."""
    return int(
        (session.get("workflow_revisions", {}) or {}).get(stage_key, 0)
        or 0
    )

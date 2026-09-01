"""Workflow state and stage validation for a SURM study.

This module is intentionally pure: it reads a session-shaped mapping and
returns decisions. Streamlit widgets remain responsible for presentation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowStage:
    key: str
    label: str
    complete: bool
    available: bool
    reason: str = ""

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


def _selected_uncertainties(session: dict[str, Any]) -> int:
    return sum(
        1 for item in session.get("uncertainties", [])
        if isinstance(item, dict) and item.get("selected")
    )


def _decision_count(session: dict[str, Any]) -> int:
    return sum(
        1 for item in session.get("key_decisions", [])
        if isinstance(item, dict) and str(item.get("Key Decision", "")).strip()
    )


def stage_results(session: dict[str, Any]) -> list[WorkflowStage]:
    """Return completion and access state for every study stage."""

    selected = _selected_uncertainties(session)
    decisions = _decision_count(session)
    completed = {
        "uncertainties": selected > 0,
        "key_decisions": decisions > 0,
        "impact_assessment": bool(session.get("impact_assessment")),
        "key_uncertainties": any(
            isinstance(item, dict) and item.get("Include in Plan")
            for item in session.get("key_uncertainties", [])
        ),
        "resolution_list": bool(session.get("resolution_list")),
        "resolution_planner": bool(session.get("resolution_planner")),
        "risk_register": bool(session.get("risk_register")),
        "pra_output": bool(session.get("pra_output")) or bool(session.get("risk_register")),
    }
    prerequisites = {
        "uncertainties": (True, ""),
        "key_decisions": (selected > 0, "Select at least one uncertainty first."),
        "impact_assessment": (decisions > 0, "Define at least one key decision first."),
        "key_uncertainties": (bool(session.get("impact_assessment")), "Complete the impact assessment first."),
        "resolution_list": (completed["key_uncertainties"], "Identify at least one key uncertainty first."),
        "resolution_planner": (bool(session.get("resolution_list")), "Select at least one resolution action first."),
        "risk_register": (bool(session.get("resolution_planner")), "Create at least one resolution plan action first."),
        "pra_output": (bool(session.get("risk_register")), "Complete the risk register first."),
    }
    return [
        WorkflowStage(
            key=key,
            label=label,
            complete=completed[key],
            available=prerequisites[key][0],
            reason=prerequisites[key][1] if not prerequisites[key][0] else "",
        )
        for key, label in STAGES
    ]


def current_stage(session: dict[str, Any]) -> WorkflowStage:
    """Return the first incomplete stage, or the final stage when complete."""

    stages = stage_results(session)
    return next((stage for stage in stages if not stage.complete), stages[-1])


def validate_stage(session: dict[str, Any], stage_key: str) -> tuple[bool, str]:
    """Check whether a stage has its upstream prerequisites."""

    for stage in stage_results(session):
        if stage.key == stage_key:
            return stage.available, stage.reason
    return False, "Unknown workflow stage."


def completion_percent(session: dict[str, Any]) -> int:
    stages = stage_results(session)
    return round(sum(stage.complete for stage in stages) / len(stages) * 100)
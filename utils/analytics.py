"""Read-only study analytics derived from the canonical session records."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from utils.workflow import completion_percent, stage_results


def _selected_uncertainties(session: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item for item in session.get("uncertainties", [])
        if isinstance(item, dict) and item.get("selected")
    ]


def build_relationships(session: dict[str, Any]) -> list[dict[str, str]]:
    """Trace uncertainty -> decision and uncertainty -> risk relationships."""

    decisions = [
        str(item.get("Key Decision", "")).strip()
        for item in session.get("key_decisions", [])
        if isinstance(item, dict) and str(item.get("Key Decision", "")).strip()
    ]
    assessments = {
        item.get("Uncertainty"): item
        for item in session.get("impact_assessment", [])
        if isinstance(item, dict)
    }
    risks_by_uncertainty = defaultdict(list)
    for risk in session.get("risk_register", []):
        if not isinstance(risk, dict):
            continue
        for uncertainty in str(risk.get("Uncertainty/Causes", "")).splitlines():
            cleaned = uncertainty.split(". ", 1)[-1].strip()
            if cleaned:
                risks_by_uncertainty[cleaned].append(str(risk.get("Risk", "")))

    relationships = []
    for uncertainty in _selected_uncertainties(session):
        name = str(uncertainty.get("name", ""))
        assessment = assessments.get(name, {})
        for decision in decisions:
            rating = str(assessment.get(decision, "NA"))
            if rating in {"H", "M"}:
                relationships.append({"uncertainty": name, "type": "affects", "target": decision, "strength": rating})
        for risk in risks_by_uncertainty.get(name, []):
            relationships.append({"uncertainty": name, "type": "contributes_to", "target": risk, "strength": ""})
    return relationships


def build_study_analytics(session: dict[str, Any]) -> dict[str, Any]:
    """Build dashboard-ready metrics without introducing a scoring methodology."""

    key_uncertainties = [
        item for item in session.get("key_uncertainties", [])
        if isinstance(item, dict) and item.get("Include in Plan")
    ]
    resolution_actions = [
        item for item in session.get("resolution_planner", [])
        if isinstance(item, dict)
    ]
    status_counts = Counter(
        str(item.get("Status", item.get("Resolution Status", "Open")))
        for item in resolution_actions
    )
    if not resolution_actions:
        status_counts = Counter()
    critical = sorted(
        key_uncertainties,
        key=lambda item: (item.get("Rank", 999), -float(item.get("Impact (Weighted)", 0) or 0)),
    )[:5]
    by_discipline = Counter(str(item.get("discipline", "Unclassified")) for item in _selected_uncertainties(session))
    return {
        "completion": completion_percent(session),
        "current_stage": stage_results(session)[next((i for i, s in enumerate(stage_results(session)) if not s.complete), -1)].label,
        "critical_uncertainties": [item.get("Uncertainty", item.get("name", "")) for item in critical],
        "resolution_status": dict(status_counts),
        "uncertainties_by_discipline": dict(by_discipline),
        "relationships": build_relationships(session),
        "counts": {
            "uncertainties": len(_selected_uncertainties(session)),
            "decisions": sum(1 for item in session.get("key_decisions", []) if isinstance(item, dict) and str(item.get("Key Decision", "")).strip()),
            "actions": len(resolution_actions),
            "risks": len(session.get("risk_register", [])),
        },
    }


def build_executive_summary(session: dict[str, Any]) -> str:
    """Create a factual summary from recorded data, without engineering inference."""

    analytics = build_study_analytics(session)
    critical = analytics["critical_uncertainties"]
    actions = analytics["counts"]["actions"]
    risks = analytics["counts"]["risks"]
    lead = critical[0] if critical else "no material uncertainty ranked yet"
    return (
        f"The study is {analytics['completion']}% complete with "
        f"{analytics['counts']['uncertainties']} selected uncertainties, "
        f"{analytics['counts']['decisions']} key decisions, "
        f"{actions} resolution actions and {risks} risks recorded. "
        f"The highest-ranked current uncertainty is {lead}."
    )
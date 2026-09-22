"""SURM decision intelligence, traceability and barrier assurance services.

This module is intentionally deterministic and methodology-neutral. It derives
operational health and traceability signals from the canonical study model; it
does not alter SURM risk scoring.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any

from utils.coercion import safe_float


RISK_ORDER = ["Extreme", "High", "Medium", "Low", "Not Assessed"]
BARRIER_HEALTH = ["Healthy", "At Risk", "Planned"]
ACTION_STATUS = ["Not Started", "In Progress", "Completed", "On Hold", "Closed"]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _items(value: Any) -> list[str]:
    text = _text(value)
    if not text:
        return []
    result = []
    for raw in text.replace(";", "\n").splitlines():
        item = raw.strip()
        if not item:
            continue
        while item and item[0] in "-•*":
            item = item[1:].strip()
        if ". " in item and item.split(". ", 1)[0].isdigit():
            item = item.split(". ", 1)[1].strip()
        if item:
            result.append(item)
    return result


def _parse_date(value: Any) -> date | None:
    text = _text(value)
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _risk_rows(session: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in session.get("risk_register", []) if isinstance(row, dict)]


def _uncertainty_maps(session: dict[str, Any]):
    by_name = {}
    for row in session.get("uncertainties", []):
        if isinstance(row, dict):
            name = _text(row.get("name"))
            if name:
                by_name[name] = row
    return by_name


def _resolution_maps(session: dict[str, Any]):
    by_id = {}
    by_name = {}
    for row in session.get("resolution_planner", []):
        if not isinstance(row, dict):
            continue
        rid = _text(row.get("resolution_id"))
        name = _text(row.get("Resolution Action"))
        if rid:
            by_id[rid] = row
        if name:
            by_name[name] = row
    return by_id, by_name


def build_traceability(session: dict[str, Any]) -> list[dict[str, Any]]:
    """Build risk -> uncertainty -> resolution -> barrier traceability rows."""
    uncertainties = _uncertainty_maps(session)
    resolution_by_id, resolution_by_name = _resolution_maps(session)
    bowties = session.get("bowtie_register", {}) or {}
    rows: list[dict[str, Any]] = []

    for risk in _risk_rows(session):
        risk_id = _text(risk.get("risk_id"))
        risk_name = _text(risk.get("Risk"))
        causes = _items(risk.get("Uncertainty/Causes"))
        resolution_names = _items(risk.get("Resolution Plan"))

        linked_uncertainties = []
        for cause in causes:
            unc = uncertainties.get(cause, {})
            linked_uncertainties.append(
                {
                    "uncertainty_id": _text(unc.get("uncertainty_id")),
                    "uncertainty": cause,
                }
            )

        for unc in linked_uncertainties:
            rows.append(
                {
                    "Risk ID": risk_id,
                    "Risk": risk_name,
                    "Uncertainty ID": unc["uncertainty_id"],
                    "Uncertainty": unc["uncertainty"],
                    "Resolution ID": "",
                    "Resolution": "",
                    "Action Status": "",
                    "Barrier ID": "",
                    "Barrier": "",
                    "Barrier Health": "",
                    "Relation": "risk→uncertainty",
                }
            )

            for resolution_name in resolution_names:
                action = resolution_by_name.get(resolution_name, {})
                rid = _text(action.get("resolution_id"))
                rows.append(
                    {
                        "Risk ID": risk_id,
                        "Risk": risk_name,
                        "Uncertainty ID": unc["uncertainty_id"],
                        "Uncertainty": unc["uncertainty"],
                        "Resolution ID": rid,
                        "Resolution": resolution_name,
                        "Action Status": _text(action.get("Status")),
                        "Barrier ID": "",
                        "Barrier": "",
                        "Barrier Health": "",
                        "Relation": "uncertainty→resolution",
                    }
                )

        document = bowties.get(risk_id, {})
        if document:
            for kind, label in (
                ("preventativeBarrier", "preventive"),
                ("mitigativeBarrier", "mitigative"),
            ):
                for node in document.get("library", {}).get(kind, []):
                    if not isinstance(node, dict):
                        continue
                    barrier_id = _text(node.get("id"))
                    name = _text(node.get("name"))
                    source = node.get("surm_source") or {}
                    rid = _text(source.get("resolution_id"))
                    action = resolution_by_id.get(rid) or resolution_by_name.get(name, {})
                    health = _text((session.get("barrier_register", {}) or {}).get(barrier_id, {}).get("health"))
                    rows.append(
                        {
                            "Risk ID": risk_id,
                            "Risk": risk_name,
                            "Uncertainty ID": "",
                            "Uncertainty": "",
                            "Resolution ID": rid,
                            "Resolution": name,
                            "Action Status": _text(action.get("Status")),
                            "Barrier ID": barrier_id,
                            "Barrier": name,
                            "Barrier Health": health,
                            "Relation": f"resolution→{label}_barrier",
                        }
                    )

    return rows


def _planner_health(action: dict[str, Any]) -> str:
    status = _text(action.get("Status")) or "Not Started"
    due = _parse_date(action.get("Required Completion") or action.get("End Date"))
    progress = safe_float(action.get("Progress (0-1)"), default=0.0)

    if status in {"Completed", "Closed"} or progress >= 1.0:
        return "Healthy"
    if due and due < date.today():
        return "At Risk"
    if status == "On Hold":
        return "At Risk"
    return "Planned"


def sync_barrier_register(session: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Synchronise durable managed-barrier records from current Bowties.

    User-maintained fields are preserved. Source-of-truth fields are refreshed
    from the current Bowtie, Risk Register and Resolution Planner.
    """
    existing = session.get("barrier_register", {}) or {}
    resolution_by_id, resolution_by_name = _resolution_maps(session)
    synced: dict[str, dict[str, Any]] = {}

    for risk_id, document in (session.get("bowtie_register", {}) or {}).items():
        if not isinstance(document, dict):
            continue
        for kind, placements_key in (
            ("Preventive", "preventativeBarriers"),
            ("Mitigative", "mitigativeBarriers"),
        ):
            library = {
                _text(node.get("id")): node
                for node in document.get("library", {}).get(
                    "preventativeBarrier" if kind == "Preventive" else "mitigativeBarrier", []
                )
                if isinstance(node, dict) and _text(node.get("id"))
            }
            placement_ids = {
                _text(item.get("nodeId"))
                for item in document.get(placements_key, [])
                if isinstance(item, dict)
            }
            for barrier_id in placement_ids:
                node = library.get(barrier_id)
                if not node:
                    continue
                source = node.get("surm_source") or {}
                resolution_id = _text(source.get("resolution_id")) or barrier_id
                action = resolution_by_id.get(resolution_id) or resolution_by_name.get(_text(node.get("name")), {})
                prev = existing.get(barrier_id, {}) if isinstance(existing, dict) else {}

                existing_risk_ids = prev.get("risk_ids") or []
                if isinstance(existing_risk_ids, str):
                    existing_risk_ids = [item.strip() for item in existing_risk_ids.split(",") if item.strip()]
                elif not isinstance(existing_risk_ids, list):
                    existing_risk_ids = list(existing_risk_ids) if existing_risk_ids else []
                status = _text(action.get("Status")) or _text(prev.get("status")) or "Planned"
                owner = _text(action.get("Action Owner")) or _text(node.get("owner")) or _text(prev.get("owner"))
                due_date = _text(action.get("Required Completion") or action.get("End Date")) or _text(prev.get("due_date"))
                progress = safe_float(action.get("Progress (0-1)"), default=safe_float(prev.get("progress"), default=0.0))
                effectiveness = _text(node.get("effectiveness")) or _text(prev.get("effectiveness"))
                degradation_factors = node.get("degradation_factors") if isinstance(node.get("degradation_factors"), list) else []
                controls = node.get("controls") if isinstance(node.get("controls"), list) else []
                health = _planner_health(action) if action else _text(prev.get("health")) or "Planned"

                record = {
                    "barrier_id": barrier_id,
                    "name": _text(node.get("name")) or barrier_id,
                    "kind": kind,
                    "risk_ids": sorted(set(existing_risk_ids + [str(risk_id)])),
                    "resolution_id": resolution_id,
                    "owner": owner,
                    "status": status,
                    "progress": progress,
                    "due_date": due_date,
                    "effectiveness": effectiveness,
                    "degradation_factors": degradation_factors,
                    "controls": controls,
                    "health": health,
                    "criticality": _text(prev.get("criticality")) or "Standard",
                    "verification_status": _text(prev.get("verification_status")) or "Pending",
                    "evidence_count": int(safe_float(prev.get("evidence_count"), default=0)),
                    "notes": _text(prev.get("notes")),
                    "source": "SURM Bowtie / Resolution Planner",
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
                synced[barrier_id] = record

    # Preserve manually managed barriers that no longer appear so deletion is auditable.
    for barrier_id, record in existing.items():
        if barrier_id not in synced and isinstance(record, dict):
            archived = dict(record)
            archived["health"] = "Archived"
            archived["source"] = "Retained historical barrier"
            synced[barrier_id] = archived

    session["barrier_register"] = synced
    return synced


def apply_barrier_register_to_bowties(session: dict[str, Any]) -> None:
    """Project managed barrier metadata back into Bowtie node metadata."""
    register = session.get("barrier_register", {}) or {}
    for document in (session.get("bowtie_register", {}) or {}).values():
        if not isinstance(document, dict):
            continue
        library = document.get("library", {}) or {}
        for node_type in ("preventativeBarrier", "mitigativeBarrier"):
            for node in library.get(node_type, []) or []:
                if not isinstance(node, dict):
                    continue
                record = register.get(_text(node.get("id")), {})
                if not record:
                    continue
                if _text(record.get("owner")):
                    node["owner"] = _text(record.get("owner"))
                if _text(record.get("effectiveness")):
                    node["effectiveness"] = _text(record.get("effectiveness"))
                node["surm_management"] = {
                    "status": _text(record.get("status")),
                    "health": _text(record.get("health")),
                    "criticality": _text(record.get("criticality")),
                    "verification_status": _text(record.get("verification_status")),
                }


def build_bowtie_qa(session: dict[str, Any]) -> list[dict[str, Any]]:
    """Return non-scoring Bowtie completeness findings for every risk."""
    findings: list[dict[str, Any]] = []
    registers = session.get("barrier_register", {}) or {}

    for risk_id, document in (session.get("bowtie_register", {}) or {}).items():
        if not isinstance(document, dict):
            continue
        risk_name = _text(document.get("name")) or str(risk_id)
        causes = document.get("causes", []) or []
        outcomes = document.get("outcomes", []) or []
        preventive = document.get("preventativeBarriers", []) or []
        mitigative = document.get("mitigativeBarriers", []) or []
        lines = document.get("lines", []) or []

        if not causes:
            findings.append({"risk_id": risk_id, "risk": risk_name, "severity": "warning", "message": "Bowtie has no cause."})
        if not outcomes:
            findings.append({"risk_id": risk_id, "risk": risk_name, "severity": "warning", "message": "Bowtie has no consequence."})
        if not preventive:
            findings.append({"risk_id": risk_id, "risk": risk_name, "severity": "warning", "message": "Bowtie has no preventive barrier."})
        if outcomes and not mitigative:
            findings.append({"risk_id": risk_id, "risk": risk_name, "severity": "warning", "message": "Consequences exist but no mitigative barrier is defined."})

        cause_lines = {str(line.get("originId")): line for line in lines if line.get("originType") == "cause"}
        for cause in causes:
            line = cause_lines.get(_text(cause.get("id")))
            if not line or not line.get("stops"):
                findings.append({
                    "risk_id": risk_id,
                    "risk": risk_name,
                    "severity": "warning",
                    "message": f"Cause '{cause.get('id', '')}' has no preventive barrier path.",
                })

        barrier_nodes = []
        for node_type in ("preventativeBarrier", "mitigativeBarrier"):
            barrier_nodes.extend(document.get("library", {}).get(node_type, []) or [])
        for node in barrier_nodes:
            barrier_id = _text(node.get("id"))
            managed = registers.get(barrier_id, {})
            if not _text(node.get("owner")) and not _text(managed.get("owner")):
                findings.append({
                    "risk_id": risk_id,
                    "risk": risk_name,
                    "severity": "warning",
                    "message": f"Barrier '{node.get('name', barrier_id)}' has no owner.",
                })
            if not _text(node.get("effectiveness")) and not _text(managed.get("effectiveness")):
                findings.append({
                    "risk_id": risk_id,
                    "risk": risk_name,
                    "severity": "info",
                    "message": f"Barrier '{node.get('name', barrier_id)}' has no effectiveness recorded.",
                })
            degradation = node.get("degradation_factors") or managed.get("degradation_factors") or []
            controls = node.get("controls") or managed.get("controls") or []
            if degradation and not controls:
                findings.append({
                    "risk_id": risk_id,
                    "risk": risk_name,
                    "severity": "warning",
                    "message": f"Barrier '{node.get('name', barrier_id)}' has degradation factors but no controls.",
                })

    return findings


def build_risk_intelligence(session: dict[str, Any]) -> dict[str, Any]:
    risks = _risk_rows(session)
    ratings = Counter(_text(row.get("Risk Rating")) or "Not Assessed" for row in risks)
    statuses = Counter(_text(row.get("Risk Status")) or "Open" for row in risks)
    owners = Counter(_text(row.get("Action Owner")) or "Unassigned" for row in risks)

    actions = [row for row in session.get("resolution_planner", []) if isinstance(row, dict)]
    action_status = Counter(_text(row.get("Status")) or "Not Started" for row in actions)
    overdue_actions = [
        row for row in actions
        if _parse_date(row.get("Required Completion") or row.get("End Date"))
        and _parse_date(row.get("Required Completion") or row.get("End Date")) < date.today()
        and _text(row.get("Status")) not in {"Completed", "Closed"}
    ]

    barriers = sync_barrier_register(dict(session))
    health = Counter(_text(row.get("health")) or "Planned" for row in barriers.values())

    qa = build_bowtie_qa({**session, "barrier_register": barriers})
    error_count = sum(item["severity"] == "error" for item in qa)
    warning_count = sum(item["severity"] == "warning" for item in qa)

    assessed = sum(
        _text(row.get("Likelihood (H/M/L)")).upper() in {"H", "M", "L"}
        and _text(row.get("Impact (H/M/L)")).upper() in {"H", "M", "L"}
        for row in risks
    )

    return {
        "risk_count": len(risks),
        "assessed_risk_count": assessed,
        "assessment_pct": round(assessed / max(len(risks), 1) * 100),
        "ratings": {key: ratings.get(key, 0) for key in RISK_ORDER},
        "statuses": dict(statuses),
        "owners": dict(owners),
        "action_count": len(actions),
        "action_status": dict(action_status),
        "overdue_actions": len(overdue_actions),
        "barrier_count": len(barriers),
        "barrier_health": dict(health),
        "bowtie_qa": qa,
        "bowtie_qa_warnings": warning_count,
        "bowtie_qa_errors": error_count,
        "traceability_rows": build_traceability({**session, "barrier_register": barriers}),
    }


def build_portfolio_intelligence(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate saved-study summaries without requiring corporate integrations."""
    if not records:
        return {
            "study_count": 0,
            "lifecycle": {},
            "phases": {},
            "completion_avg": 0,
            "completion_min": 0,
            "completion_max": 0,
            "by_owner": {},
        }

    completion = [float(record.get("completion", 0) or 0) for record in records]
    return {
        "study_count": len(records),
        "lifecycle": dict(Counter(_text(r.get("study_lifecycle")) or "Draft" for r in records)),
        "phases": dict(Counter(_text(r.get("phase")) or "—" for r in records)),
        "completion_avg": round(sum(completion) / len(completion)),
        "completion_min": round(min(completion)),
        "completion_max": round(max(completion)),
        "by_owner": dict(Counter(_text(r.get("last_edited_by")) or "Unassigned" for r in records)),
    }


def build_historical_patterns(documents: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe recurring recorded content; it does not predict outcomes."""
    uncertainty_counts = Counter()
    resolution_counts = Counter()
    risk_counts = Counter()

    for session in documents:
        for row in session.get("uncertainties", []):
            if isinstance(row, dict) and row.get("selected"):
                name = _text(row.get("name"))
                if name:
                    uncertainty_counts[name] += 1
        for row in session.get("resolution_planner", []):
            if isinstance(row, dict):
                name = _text(row.get("Resolution Action"))
                if name:
                    resolution_counts[name] += 1
        for row in session.get("risk_register", []):
            if isinstance(row, dict):
                name = _text(row.get("Risk"))
                if name:
                    risk_counts[name] += 1

    return {
        "recurring_uncertainties": uncertainty_counts.most_common(10),
        "recurring_resolutions": resolution_counts.most_common(10),
        "recurring_risks": risk_counts.most_common(10),
    }

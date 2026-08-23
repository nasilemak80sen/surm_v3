"""Structured study export for interchange and audit-friendly snapshots."""

from __future__ import annotations

import json
import csv
import io
from datetime import datetime, timezone
from typing import Any

from utils.analytics import build_study_analytics
from utils.workflow import stage_results


def build_study_snapshot(session: dict[str, Any]) -> dict[str, Any]:
    """Return an explicit, versioned study document from session state."""

    return {
        "schema_version": "2.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "study": {
            "project_name": session.get("project_name", ""),
            "field_name": session.get("field_name", ""),
            "phase": session.get("project_phase", ""),
            "lifecycle": session.get("study_lifecycle", "Draft"),
        },
        "entities": {
            "team": session.get("team_members", []),
            "uncertainties": session.get("uncertainties", []),
            "decisions": session.get("key_decisions", []),
            "impact_assessments": session.get("impact_assessment", []),
            "key_uncertainties": session.get("key_uncertainties", []),
            "resolutions": session.get("resolution_planner", []),
            "risks": session.get("risk_register", []),
        },
<<<<<<< HEAD
        "workflow": [
            {**stage.__dict__, "state": stage.state}
            for stage in stage_results(session)
        ],
=======
        "workflow": [stage.__dict__ for stage in stage_results(session)],
>>>>>>> fdabfa70d79f5ac5259db5e93512c9a3dc1cbc85
        "analytics": build_study_analytics(session),
    }


def snapshot_json(session: dict[str, Any]) -> bytes:
    return json.dumps(build_study_snapshot(session), indent=2, ensure_ascii=False).encode("utf-8")


def snapshot_csv(session: dict[str, Any]) -> bytes:
    """Export the relationship layer as a portable, analysis-friendly CSV."""

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["uncertainty", "type", "target", "strength"],
    )
    writer.writeheader()
    for relationship in build_study_snapshot(session)["analytics"]["relationships"]:
        writer.writerow(relationship)
    return output.getvalue().encode("utf-8")
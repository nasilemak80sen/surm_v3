"""Structured study export for interchange and audit-friendly snapshots."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from utils.analytics import build_study_analytics
from utils.study_document import StudyDocument
from utils.workflow import stage_results


def build_study_snapshot(session: dict[str, Any]) -> dict[str, Any]:
    """Build a versioned snapshot from the canonical StudyDocument model."""
    document = StudyDocument.from_session(session)
    study = document.to_dict()

    return {
        "schema_version": document.schema_version,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "study": {
            "study_id": document.study_id,
            "project_name": document.project_name,
            "field_name": document.field_name,
            "phase": document.project_phase,
            "lifecycle": document.study_lifecycle,
            "owner": document.study_owner,
            "methodology_version": document.methodology_version,
            "revision": document.study_revision,
        },
        "governance": {
            "prepared_by": {
                "name": document.prep_name,
                "role": document.prep_role,
                "date": document.prep_date,
            },
            "reviewed_by_gg": {
                "name": document.rev_gg_name,
                "role": document.rev_gg_role,
                "date": document.rev_gg_date,
            },
            "reviewed_by_re": {
                "name": document.rev_re_name,
                "role": document.rev_re_role,
                "date": document.rev_re_date,
            },
            "reviewed_by_pp": {
                "name": document.rev_pp_name,
                "role": document.rev_pp_role,
                "date": document.rev_pp_date,
            },
            "endorsed_by": {
                "name": document.endorsed_name,
                "role": document.endorsed_role,
                "date": document.endorsed_date,
            },
        },
        "entities": {
            "team": study["team_members"],
            "uncertainties": study["uncertainties"],
            "decisions": study["key_decisions"],
            "impact_assessments": study["impact_assessment"],
            "key_uncertainties": study["key_uncertainties"],
            "resolution_list": study["resolution_list"],
            "resolutions": study["resolution_planner"],
            "risks": study["risk_register"],
            "bowties": study["bowtie_register"],
            "barriers": study["barrier_register"],
            "pra_output": study["pra_output"],
            "study_reviews": study["study_reviews"],
        },
        "workflow": [
            {**stage.__dict__, "state": stage.state}
            for stage in stage_results(session)
        ],
        "workflow_revisions": study["workflow_revisions"],
        "workflow_snapshots": study["workflow_snapshots"],
        "analytics": build_study_analytics(session),
    }


def snapshot_json(session: dict[str, Any]) -> bytes:
    return json.dumps(
        build_study_snapshot(session),
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8")


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

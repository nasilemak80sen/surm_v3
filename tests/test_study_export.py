from utils.study_export import build_study_snapshot


def test_snapshot_uses_canonical_schema_and_governance_fields():
    snapshot = build_study_snapshot({
        "study_id": "study-export-001",
        "project_name": "Export Project",
        "field_name": "Export Field",
        "project_phase": "PGR3/FID",
        "study_owner": "owner",
        "methodology_version": "SURM-2026.01",
        "prep_name": "Prepared Person",
        "prep_role": "Engineer",
        "prep_date": "22/09/2026",
        "workflow_revisions": {"impact_assessment": 2},
        "workflow_snapshots": {"impact_assessment": {"revision": 2}},
        "uncertainties": [],
        "key_decisions": [],
        "impact_assessment": [],
        "key_uncertainties": [],
        "resolution_list": {},
        "resolution_planner": [],
        "risk_register": [],
        "pra_output": [],
        "team_members": [],
        "study_lifecycle": "Draft",
        "study_revision": 2,
        "_mapping": {"resolution_options": []},
    })

    assert snapshot["schema_version"] == "2.2"
    assert snapshot["study"]["study_id"] == "study-export-001"
    assert snapshot["study"]["methodology_version"] == "SURM-2026.01"
    assert snapshot["governance"]["prepared_by"]["name"] == "Prepared Person"
    assert snapshot["workflow_revisions"]["impact_assessment"] == 2
    assert "pra_output" in snapshot["entities"]

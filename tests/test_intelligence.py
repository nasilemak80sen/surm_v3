from utils.intelligence import (
    build_bowtie_qa,
    build_historical_patterns,
    build_portfolio_intelligence,
    build_risk_intelligence,
    build_traceability,
    sync_barrier_register,
)


def fixture():
    return {
        "uncertainties": [
            {"uncertainty_id": "UNC-001", "name": "Fault seal", "selected": True},
        ],
        "resolution_planner": [
            {
                "resolution_id": "RES-001",
                "Resolution Action": "Fault Seal Analysis",
                "Status": "In Progress",
                "Action Owner": "Engineer A",
                "Progress (0-1)": 0.5,
            },
        ],
        "risk_register": [
            {
                "risk_id": "RSK-001",
                "Risk": "Low in place volume",
                "Uncertainty/Causes": "1. Fault seal",
                "Resolution Plan": "Fault Seal Analysis",
                "Action Owner": "Engineer A",
                "Risk Rating": "High",
                "Risk Status": "Open",
                "Likelihood (H/M/L)": "H",
                "Impact (H/M/L)": "M",
                "Contingency Plan": "Review",
                "Impact/Consequence": "Lower volume",
            }
        ],
        "bowtie_register": {
            "RSK-001": {
                "risk_id": "RSK-001",
                "name": "Low in place volume",
                "causes": [
                    {"id": "CAUSE-1", "nodeId": "UNC-001"}
                ],
                "preventativeBarriers": [
                    {"id": "PB-1", "nodeId": "RES-001"}
                ],
                "mitigativeBarriers": [],
                "outcomes": [],
                "lines": [
                    {"originType": "cause", "originId": "CAUSE-1", "stops": ["PB-PLACEMENT-1"]}
                ],
                "library": {
                    "preventativeBarrier": [
                        {
                            "id": "RES-001",
                            "name": "Fault Seal Analysis",
                            "owner": "Engineer A",
                            "effectiveness": "Medium",
                            "surm_source": {"resolution_id": "RES-001"},
                        }
                    ],
                    "mitigativeBarrier": [],
                },
            }
        },
        "barrier_register": {},
    }


def test_barrier_sync_preserves_source_and_adds_management_record():
    session = fixture()
    register = sync_barrier_register(session)

    assert "RES-001" in register
    assert register["RES-001"]["name"] == "Fault Seal Analysis"
    assert register["RES-001"]["owner"] == "Engineer A"
    assert register["RES-001"]["resolution_id"] == "RES-001"


def test_traceability_connects_risk_uncertainty_resolution_and_barrier():
    rows = build_traceability(fixture())

    relations = {row["Relation"] for row in rows}
    assert "risk→uncertainty" in relations
    assert "uncertainty→resolution" in relations
    assert "resolution→preventive_barrier" in relations


def test_risk_intelligence_reports_assessment_and_action_counts():
    intelligence = build_risk_intelligence(fixture())

    assert intelligence["risk_count"] == 1
    assert intelligence["assessed_risk_count"] == 1
    assert intelligence["assessment_pct"] == 100
    assert intelligence["action_count"] == 1
    assert intelligence["barrier_count"] == 1


def test_bowtie_qa_flags_missing_consequence_and_mitigation():
    findings = build_bowtie_qa(fixture())
    messages = {row["message"] for row in findings}

    assert "Bowtie has no consequence." in messages
    assert "Consequences exist but no mitigative barrier is defined." not in messages


def test_portfolio_and_history_are_deterministic():
    portfolio = build_portfolio_intelligence([
        {"completion": 40, "study_lifecycle": "Draft", "phase": "PGR1", "last_edited_by": "A"},
        {"completion": 80, "study_lifecycle": "Approved", "phase": "PGR2", "last_edited_by": "B"},
    ])
    assert portfolio["study_count"] == 2
    assert portfolio["completion_avg"] == 60

    historical = build_historical_patterns([fixture(), fixture()])
    assert historical["recurring_uncertainties"][0] == ("Fault seal", 2)


def test_bowtie_qa_flags_degradation_without_controls():
    session = fixture()
    session["bowtie_register"]["RSK-001"]["library"]["preventativeBarrier"][0]["degradation_factors"] = [
        "Poor seismic resolution"
    ]
    findings = build_bowtie_qa(session)

    assert any(
        "degradation factors but no controls" in row["message"]
        for row in findings
    )

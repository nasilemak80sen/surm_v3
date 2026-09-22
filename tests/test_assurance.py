from utils.assurance import approval_readiness, validate_transition
from utils.study_document import StudyDocument


def test_new_canonical_entities_round_trip():
    document = StudyDocument.from_session({
        "study_id": "study-next-wave",
        "project_name": "Alpha",
        "barrier_register": {"RES-001": {"name": "Fault Seal Analysis"}},
        "study_role": "Reviewer",
        "study_reviews": [{"to": "Reviewed"}],
        "bowtie_register": {"RSK-001": {"risk_id": "RSK-001"}},
    })

    restored = StudyDocument.from_session(document.to_dict())

    assert document.schema_version == "2.2"
    assert restored.barrier_register == {"RES-001": {"name": "Fault Seal Analysis"}}
    assert restored.study_role == "Reviewer"
    assert restored.study_reviews == [{"to": "Reviewed"}]
    assert restored.bowtie_register["RSK-001"]["risk_id"] == "RSK-001"


def test_approval_requires_governance_and_workflow():
    ready, reasons = approval_readiness({
        "study_lifecycle": "Reviewed",
        "study_role": "Approver",
        "uncertainties": [],
        "key_decisions": [],
        "impact_assessment": [],
        "key_uncertainties": [],
        "resolution_list": {},
        "resolution_planner": [],
        "risk_register": [],
        "pra_output": [],
        "bowtie_register": {},
        "barrier_register": {},
    })

    assert not ready
    assert any("workflow" in reason.lower() for reason in reasons)


def test_approval_requires_approver_role():
    allowed, reasons = validate_transition(
        {"study_lifecycle": "Reviewed", "study_role": "Reviewer"},
        "Approved",
    )

    assert not allowed
    assert any("Approver" in reason for reason in reasons)


def test_approval_requires_bowtie_coverage_for_assessed_risks():
    ready, reasons = approval_readiness({
        "study_lifecycle": "Reviewed",
        "study_role": "Approver",
        "uncertainties": [],
        "key_decisions": [],
        "impact_assessment": [],
        "key_uncertainties": [],
        "resolution_list": {},
        "resolution_planner": [],
        "risk_register": [{"risk_id": "RSK-001"}],
        "pra_output": [],
        "bowtie_register": {},
        "barrier_register": {},
        "prep_name": "A", "prep_role": "Engineer", "prep_date": "01/01/2026",
        "rev_gg_name": "B", "rev_gg_role": "G&G", "rev_gg_date": "01/01/2026",
        "rev_re_name": "C", "rev_re_role": "RE", "rev_re_date": "01/01/2026",
        "rev_pp_name": "D", "rev_pp_role": "PP", "rev_pp_date": "01/01/2026",
        "endorsed_name": "E", "endorsed_role": "Lead", "endorsed_date": "01/01/2026",
    })

    assert not ready
    assert any("Bowtie documents" in reason for reason in reasons)

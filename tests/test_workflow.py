from utils.workflow import (
    completion_percent,
    invalidate_downstream,
    mark_stage_changed,
    stage_results,
)


def make_minimal_ready_session():
    return {
        "uncertainties": [
            {
                "name": "U1",
                "selected": True,
            }
        ],
        "key_decisions": [
            {
                "Key Decision": "D1",
                "Weight (1-3)": 3,
            }
        ],
        "impact_assessment": [
            {
                "Uncertainty": "U1",
                "Degree of Uncertainty": "H",
                "D1": "M",
            }
        ],
        "key_uncertainties": [
            {
                "Uncertainty": "U1",
                "Include in Plan": True,
                "Resolution Achieved": False,
            }
        ],
        "_mapping": {
            "resolution_options": ["Option A"],
        },
        "resolution_list": {
            "U1": {
                "Option A": "Y",
            }
        },
        "resolution_planner": [
            {
                "Resolution Action": "Option A",
                "Part of Workplan": True,
                "Action Owner": "Owner",
            }
        ],
        "risk_register": [
            {
                "Risk": "Risk A",
                "Likelihood (H/M/L)": "M",
                "Impact (H/M/L)": "H",
                "Action Owner": "Owner",
                "Contingency Plan": "Contingency",
                "Impact/Consequence": "Consequence",
            }
        ],
        "pra_output": [{"Risk": "Risk A"}],
        "workflow_revisions": {},
        "workflow_snapshots": {},
    }


def test_empty_study_only_has_first_stage_available():
    stages = stage_results({
        "uncertainties": [],
        "key_decisions": [],
        "impact_assessment": [],
        "key_uncertainties": [],
        "resolution_list": {},
        "resolution_planner": [],
        "risk_register": [],
        "pra_output": [],
        "_mapping": {"resolution_options": ["Option A"]},
    })

    assert stages[0].available is True
    assert stages[0].complete is False
    assert stages[1].available is False
    assert stages[-1].available is False
    assert completion_percent({
        "uncertainties": [],
        "key_decisions": [],
        "impact_assessment": [],
        "key_uncertainties": [],
        "resolution_list": {},
        "resolution_planner": [],
        "risk_register": [],
        "pra_output": [],
        "_mapping": {"resolution_options": ["Option A"]},
    }) == 0


def test_missing_resolution_coverage_blocks_planner():
    session = make_minimal_ready_session()
    session["resolution_list"]["U1"]["Option A"] = ""

    stages = stage_results(session)
    planner_stage = next(s for s in stages if s.key == "resolution_planner")

    assert planner_stage.complete is False
    assert planner_stage.available is False
    assert "no selected resolution" in planner_stage.reason


def test_unassessed_risk_blocks_pra():
    session = make_minimal_ready_session()
    session["risk_register"][0]["Impact (H/M/L)"] = ""

    stages = stage_results(session)
    risk_stage = next(s for s in stages if s.key == "risk_register")
    pra_stage = next(s for s in stages if s.key == "pra_output")

    assert risk_stage.complete is False
    assert pra_stage.available is False


def test_ready_flow_completes_through_pra():
    session = make_minimal_ready_session()
    stages = stage_results(session)

    assert all(stage.complete for stage in stages)
    assert completion_percent(session) == 100


def test_dependency_invalidation_only_clears_downstream_state():
    session = {
        "impact_assessment": [{"Uncertainty": "U1"}],
        "key_uncertainties": [{"Uncertainty": "U1"}],
        "resolution_list": {"U1": {"Option A": "Y"}},
        "resolution_planner": [{"Resolution Action": "Option A"}],
        "risk_register": [{"Risk": "Risk A"}],
        "pra_output": [{"Risk": "Risk A"}],
    }

    downstream = invalidate_downstream(session, "impact_assessment")

    assert downstream == (
        "key_uncertainties",
        "resolution_list",
        "resolution_planner",
        "risk_register",
        "pra_output",
    )
    assert session["impact_assessment"] == [{"Uncertainty": "U1"}]
    assert session["key_uncertainties"] == []
    assert session["resolution_list"] == {}
    assert session["resolution_planner"] == []
    assert session["risk_register"] == []
    assert session["pra_output"] == []


def test_stage_change_tracks_revision_and_invalidates():
    session = {
        "impact_assessment": [{"Uncertainty": "U1"}],
        "key_uncertainties": [{"Uncertainty": "U1"}],
        "resolution_list": {"U1": {"Option A": "Y"}},
        "resolution_planner": [{"Resolution Action": "Option A"}],
        "risk_register": [{"Risk": "Risk A"}],
        "pra_output": [{"Risk": "Risk A"}],
        "workflow_revisions": {},
        "workflow_snapshots": {},
    }

    mark_stage_changed(session, "impact_assessment")

    assert session["workflow_revisions"]["impact_assessment"] == 1
    assert session["workflow_snapshots"]["impact_assessment"]["revision"] == 1
    assert session["key_uncertainties"] == []

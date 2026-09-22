from pathlib import Path

import pandas as pd
import pytest


TARGET_FORM_FILES = [
    "modules/tab2_key_decisions.py",
    "modules/tab3_impact_assessment.py",
    "modules/tab4_key_uncertainties.py",
    "modules/tab5_resolution_list.py",
    "modules/tab6_resolution_planner.py",
    "modules/tab7_risk_register.py",
]


def test_multi_action_forms_disable_accidental_enter_submission():
    project_root = Path(__file__).resolve().parents[1]

    for relative_path in TARGET_FORM_FILES:
        source = (project_root / relative_path).read_text(encoding="utf-8")
        assert "enter_to_submit=False" in source, relative_path


def _run_app(script):
    from streamlit.testing.v1 import AppTest

    return AppTest.from_function(script, default_timeout=10).run()


def test_team_editor_submit_captures_active_editor_state():
    def app():
        import streamlit as st
        from modules import tab_documentation as page
        from utils.session import init_session

        init_session()
        st.session_state["project_name"] = "Interaction Test"

        def fake_editor(df, **kwargs):
            edited = df.copy()
            edited.loc[0, "Name"] = "Active Cell User"
            edited.loc[0, "Function / Role"] = "RE"
            edited.loc[0, "Date (DD/MM/YYYY)"] = "22/09/2026"
            return edited

        page.st.data_editor = fake_editor
        page.save_session = lambda auto=False: True
        page.render()

    at = _run_app(app)
    at.button(key="save_team").click().run()

    assert not at.exception
    assert at.session_state["team_members"][0]["Name"] == "Active Cell User"
    assert at.session_state["team_members"][0]["Function / Role"] == "RE"



def test_key_decision_duplicate_is_rejected_on_save():
    def app():
        import streamlit as st
        from modules import tab2_key_decisions as page
        from utils.session import init_session

        init_session()
        st.session_state["project_name"] = "Interaction Test"
        page.save_session = lambda auto=False: True
        page.render()

    at = _run_app(app)
    editor_key = f"kd_editor_{at.session_state['study_id']}"
    at.session_state[editor_key] = {
        "edited_rows": {
            0: {"Key Decision": "No. of injectors"}
        },
        "added_rows": [],
        "deleted_rows": [],
    }

    at.button(key="save_key_decisions").click().run()

    assert any("Duplicate Key Decision value" in warning.value for warning in at.warning)
    assert at.session_state["key_decisions"][0]["Key Decision"] == "No. of reactivated producers"


def test_impact_save_requires_explicit_decision_rating():
    def app():
        import streamlit as st
        from modules import tab3_impact_assessment as page
        from utils.session import init_session

        init_session()
        st.session_state["project_name"] = "Interaction Test"
        st.session_state["uncertainties"][0]["selected"] = True
        st.session_state["impact_assessment"] = []
        page.save_session = lambda auto=False: True
        page.render()

    at = _run_app(app)
    at.button(key="save_impact_assessment").click().run()

    assert any(
        "explicitly rate each decision impact" in warning.value
        or "choose a Degree of Uncertainty" in warning.value
        for warning in at.warning
    )
    assert at.session_state["impact_assessment"] == []


def test_key_uncertainty_resolution_tracking_does_not_clear_resolution_list():
    def app():
        import streamlit as st
        from modules import tab4_key_uncertainties as page
        from utils.session import init_session

        init_session()
        st.session_state["project_name"] = "Interaction Test"
        st.session_state["uncertainties"][0]["selected"] = True
        decision = st.session_state["key_decisions"][0]
        st.session_state["impact_assessment"] = [{
            "uncertainty_id": st.session_state["uncertainties"][0]["uncertainty_id"],
            "Uncertainty": st.session_state["uncertainties"][0]["name"],
            "Degree of Uncertainty": "H",
            decision["Key Decision"]: "H",
            "Impact (Weighted)": 3.0,
            "Impact Bin": "H",
            "Combined Rating": "HH",
        }]
        uncertainty_name = st.session_state["uncertainties"][0]["name"]
        st.session_state["key_uncertainties"] = [{
            "uncertainty_id": st.session_state["uncertainties"][0]["uncertainty_id"],
            "Uncertainty": uncertainty_name,
            "Degree of Uncertainty": "H",
            "Impact (Weighted)": 3.0,
            "Impact Bin": "H",
            "Combined Rating": "HH",
            "Rank": 1,
            "Include in Plan": True,
            "Resolution Achieved": False,
        }]
        st.session_state["resolution_list"] = {uncertainty_name: {"Option A": "Y"}}
        st.session_state["resolution_planner"] = [{
            "resolution_id": "RES-001",
            "Resolution Action": "Option A",
            "Part of Workplan": True,
            "Action Owner": "Owner",
        }]
        st.session_state["risk_register"] = [{"Risk": "Risk A"}]

        def fake_editor(df, **kwargs):
            edited = df.copy()
            edited.loc[0, "Resolution Achieved"] = True
            return edited

        page.st.data_editor = fake_editor
        page.save_session = lambda auto=False: True
        page.render()

    at = _run_app(app)

    uncertainty_name = at.session_state["key_uncertainties"][0]["Uncertainty"]
    at.button(key="save_key_uncertainties").click().run()

    assert at.session_state["key_uncertainties"][0]["Resolution Achieved"] is True
    assert at.session_state["resolution_list"] == {uncertainty_name: {"Option A": "Y"}}
    assert at.session_state["resolution_planner"]
    assert at.session_state["risk_register"]



def test_resolution_list_bulk_action_stays_draft_until_save():
    def app():
        import streamlit as st
        from modules import tab5_resolution_list as page
        from utils.session import init_session

        init_session()
        st.session_state["project_name"] = "Interaction Test"
        uncertainty = st.session_state["uncertainties"][0]
        uncertainty["selected"] = True
        decision = st.session_state["key_decisions"][0]
        st.session_state["impact_assessment"] = [{
            "uncertainty_id": uncertainty["uncertainty_id"],
            "Uncertainty": uncertainty["name"],
            "Degree of Uncertainty": "H",
            decision["Key Decision"]: "H",
            "Impact (Weighted)": 3.0,
            "Impact Bin": "H",
            "Combined Rating": "HH",
        }]
        st.session_state["key_uncertainties"] = [{
            "uncertainty_id": uncertainty["uncertainty_id"],
            "Uncertainty": uncertainty["name"],
            "Degree of Uncertainty": "H",
            "Impact (Weighted)": 3.0,
            "Impact Bin": "H",
            "Combined Rating": "HH",
            "Rank": 1,
            "Include in Plan": True,
            "Resolution Achieved": False,
        }]
        page.save_session = lambda auto=False: True
        page.render()

    at = _run_app(app)
    at.button(key="res_select_all").click().run()

    name = at.session_state["key_uncertainties"][0]["Uncertainty"]
    assert all(
        value == "Y"
        for value in at.session_state["resolution_list"][name].values()
    )

    at.button(key="save_resolution_list").click().run()
    assert at.session_state["resolution_list"][name]


def test_planner_execution_metadata_save_preserves_existing_risk_register():
    def app():
        import streamlit as st
        from modules import tab6_resolution_planner as page
        from utils.session import init_session

        init_session()
        st.session_state["project_name"] = "Interaction Test"
        uncertainty = st.session_state["uncertainties"][0]
        uncertainty["selected"] = True
        st.session_state["key_uncertainties"] = [{
            "uncertainty_id": uncertainty["uncertainty_id"],
            "Uncertainty": uncertainty["name"],
            "Combined Rating": "HH",
            "Include in Plan": True,
        }]
        st.session_state["resolution_list"] = {
            uncertainty["name"]: {"Option A": "Y"}
        }
        st.session_state["resolution_planner"] = [{
            "resolution_id": "RES-001",
            "#": 1,
            "Resolution Action": "Option A",
            "Associated Uncertainties": uncertainty["name"],
            "Ratings": "HH",
            "Description": "Existing description",
            "Duration (months)": 3,
            "Resources": "RE",
            "Constraints": "",
            "Start Date": "",
            "Required Completion": "",
            "Progress (0-1)": 0.25,
            "Status": "In Progress",
            "Action Owner": "Owner",
            "Part of Workplan": True,
            "Remarks": "Existing remarks",
        }]
        st.session_state["risk_register"] = [{"Risk": "Risk A"}]

        def fake_editor(df, **kwargs):
            edited = df.copy()
            edited.loc[0, "Remarks"] = "Updated remarks"
            return edited

        page.st.data_editor = fake_editor
        page.save_session = lambda auto=False: True
        page.render()

    at = _run_app(app)
    at.button(key="save_resolution_planner").click().run()

    assert at.session_state["resolution_planner"][0]["Remarks"] == "Updated remarks"
    assert at.session_state["risk_register"] == [{"Risk": "Risk A"}]



def test_risk_register_form_is_explicit_save_transaction():
    def app():
        import streamlit as st
        from modules import tab7_risk_register as page
        from utils.session import init_session

        init_session()
        st.session_state["project_name"] = "Interaction Test"
        uncertainty = st.session_state["uncertainties"][0]
        uncertainty["selected"] = True
        st.session_state["key_uncertainties"] = [{
            "uncertainty_id": uncertainty["uncertainty_id"],
            "Uncertainty": uncertainty["name"],
            "Combined Rating": "HH",
            "Include in Plan": True,
        }]
        st.session_state["resolution_list"] = {
            uncertainty["name"]: {"Option A": "Y"}
        }
        st.session_state["risk_register"] = [{
            "risk_id": "RSK-001",
            "#": 1,
            "Risk": "Risk A",
            "Uncertainty/Causes": uncertainty["name"],
            "Resolution Plan": "Option A",
            "Action Owner": "Owner",
            "Contingency Plan": "Contingency",
            "Impact/Consequence": "Consequence",
            "Likelihood (H/M/L)": "H",
            "Impact (H/M/L)": "H",
            "Risk Rating": "Extreme",
            "Risk Status": "Open",
            "Remarks": "",
        }]
        page.save_session = lambda auto=False: True
        page.render()

    at = _run_app(app)
    assert at.button(key="save_risk_register")
    assert not at.exception


@pytest.mark.parametrize("page_path", TARGET_FORM_FILES)
def test_form_modules_import(page_path):
    module_name = page_path[:-3].replace("/", ".")
    __import__(module_name)

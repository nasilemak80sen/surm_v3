import ast
from pathlib import Path

import pandas as pd
import pytest


def test_shell_uses_one_sidebar_navigation_surface():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "surm.py").read_text(encoding="utf-8")

    ast.parse(source)
    assert "def render_top_navigation" not in source
    assert "render_top_navigation()" not in source
    assert "_build_sidebar_navigation" in source
    assert "header_slot = st.empty()" not in source
    assert 'with st.expander("Insights & governance", expanded=False)' in source
    assert 'with st.expander("Session & export", expanded=False)' in source
    assert 'with st.expander("Account & access", expanded=False)' in source


def test_overview_does_not_duplicate_repository_or_export():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "modules/tab_frontpage.py").read_text(encoding="utf-8")

    ast.parse(source)
    assert "list_sessions" not in source
    assert "load_session_record" not in source
    assert "build_excel_export" not in source
    assert "Download study JSON" not in source
    assert "Saved studies" not in source


TARGET_FORM_FILES = [
    "modules/tab2_key_decisions.py",
    "modules/tab3_impact_assessment.py",
    "modules/tab4_key_uncertainties.py",
    "modules/tab5_resolution_list.py",
    "modules/tab6_resolution_planner.py",
    "modules/tab7_risk_register.py",
]


def test_durable_study_signature_tracks_real_edits_only():
    from utils.session import study_has_unsaved_changes, study_state_signature

    state = {
        "project_name": "Study A",
        "field_name": "Field A",
        "study_access_mode": "edit",
        "study_mode": "new",
        "ui_primary_color": "#1F6B3A",
        "_auto_save_enabled": True,
    }

    state["_saved_signature"] = study_state_signature(state)
    assert not study_has_unsaved_changes(state)

    state["study_access_mode"] = "view"
    state["ui_primary_color"] = "#000000"
    assert not study_has_unsaved_changes(state)

    state["field_name"] = "Field B"
    assert study_has_unsaved_changes(state)


def test_entrypoint_and_page_shell_compile():
    project_root = Path(__file__).resolve().parents[1]
    entrypoint = (project_root / "surm.py").read_text(encoding="utf-8")
    compile(entrypoint, str(project_root / "surm.py"), "exec")

    for module in (
        "modules.tab_frontpage",
        "modules.tab_study_repository",
        "modules.tab1_uncertainties",
        "modules.tab2_key_decisions",
        "modules.tab3_impact_assessment",
        "modules.tab4_key_uncertainties",
        "modules.tab5_resolution_list",
        "modules.tab6_resolution_planner",
        "modules.tab7_risk_register",
    ):
        __import__(module)


def test_view_only_router_renders_without_missing_function():
    def app():
        import streamlit as st
        import surm
        from utils.session import init_session

        init_session()
        st.session_state["current_page"] = "👥 Team"
        st.session_state["study_access_mode"] = "view"
        surm.render_navigation()

    at = _run_app(app)

    assert not at.exception, f"view-only navigation failed: {at.exception}"
    assert any("Read-only view" in info.value for info in at.info)
    assert at.markdown or at.dataframe


def test_project_identity_survives_overview_to_team_save_rerun():
    def app():
        import streamlit as st
        from modules import tab_frontpage, tab_documentation
        from utils.session import init_session
        from unittest.mock import patch

        init_session()
        page = st.selectbox(
            "Test page",
            ["Overview", "Team"],
            key="interaction_page",
        )

        if page == "Overview":
            tab_frontpage.render()
        else:
            with patch.object(tab_documentation, "save_session", lambda auto=False: True):
                tab_documentation.render()

    at = _run_app(app)

    at.text_input(key="project_name_input").set_value("Ledang FDP").run()
    assert at.session_state["project_name"] == "Ledang FDP"

    at.selectbox(key="interaction_page").set_value("Team").run()
    assert at.session_state["project_name"] == "Ledang FDP"

    at.button(key="save_team").click().run()
    assert not at.exception
    assert at.session_state["project_name"] == "Ledang FDP"


def test_multi_action_forms_disable_accidental_enter_submission():
    project_root = Path(__file__).resolve().parents[1]

    for relative_path in TARGET_FORM_FILES:
        source = (project_root / relative_path).read_text(encoding="utf-8")
        assert "enter_to_submit=False" in source, relative_path




def test_dense_workspaces_expose_work_and_result_surfaces():
    project_root = Path(__file__).resolve().parents[1]
    expected_tabs = {
        "modules/tab3_impact_assessment.py": ["1 · Assessment", "2 · Current ranking"],
        "modules/tab4_key_uncertainties.py": ["1 · Prioritise", "2 · Decision support"],
        "modules/tab5_resolution_list.py": ["1 · Resolution mapping", "2 · Coverage"],
        "modules/tab6_resolution_planner.py": ["1 · Workplan", "2 · Execution pulse"],
        "modules/tab7_risk_register.py": ["1 · Risk assessment", "2 · Risk pulse", "3 · Bowtie analysis"],
    }

    for relative_path, labels in expected_tabs.items():
        source = (project_root / relative_path).read_text(encoding="utf-8")
        ast.parse(source)
        for label in labels:
            assert label in source, f"{relative_path}: missing workspace label {label!r}"


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

        from unittest.mock import patch

        with patch.object(st, "data_editor", fake_editor),             patch.object(page, "save_session", lambda auto=False: True):
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

        def fake_editor(df, **kwargs):
            edited = df.copy()
            edited.loc[0, "Key Decision"] = edited.iloc[1]["Key Decision"]
            return edited

        from unittest.mock import patch

        with patch.object(st, "data_editor", fake_editor),             patch.object(page, "save_session", lambda auto=False: True):
            page.render()

    at = _run_app(app)
    at.button(key="save_key_decisions").click().run()

    assert any(
        "Duplicate Key Decision value" in warning.value
        for warning in at.warning
    )



def test_impact_assessment_renders_explicit_save_transaction():
    def app():
        import streamlit as st
        import importlib
        from modules import tab3_impact_assessment as page
        from utils.session import init_session
        importlib.reload(page)

        init_session()
        st.session_state["project_name"] = "Interaction Test"
        st.session_state["uncertainties"][0]["selected"] = True
        st.session_state["impact_assessment"] = []
        page.save_session = lambda auto=False: True
        page.render()

    at = _run_app(app)
    assert at.button(key="save_impact_assessment")
    assert not at.exception



def test_key_uncertainty_save_does_not_invalidate_on_metadata_only_submission():
    mark_calls = []

    def app():
        import streamlit as st
        from modules import tab4_key_uncertainties as page
        from utils.session import init_session
        from unittest.mock import patch

        importlib = __import__("importlib")
        importlib.reload(page)

        init_session()
        st.session_state["project_name"] = "Interaction Test"
        st.session_state["uncertainties"][0]["selected"] = True
        decision = st.session_state["key_decisions"][0]
        uncertainty_name = st.session_state["uncertainties"][0]["name"]
        st.session_state["impact_assessment"] = [{
            "uncertainty_id": st.session_state["uncertainties"][0]["uncertainty_id"],
            "Uncertainty": uncertainty_name,
            "Degree of Uncertainty": "H",
            decision["Key Decision"]: "H",
            "Impact (Weighted)": 3.0,
            "Impact Bin": "H",
            "Combined Rating": "HH",
        }]
        st.session_state["key_uncertainties"] = [{
            "uncertainty_id": st.session_state["uncertainties"][0]["uncertainty_id"],
            "Uncertainty": uncertainty_name,
            "Degree of Uncertainty": "H",
            "Impact (Weighted)": 3.0,
            "Impact Bin": "H",
            "Combined Rating": "HH",
            "Rank": 1,
            "Include in Plan": False,
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

        def record_change(session, stage):
            mark_calls.append(stage)

        with patch.object(page, "mark_stage_changed", record_change),             patch.object(page, "save_session", lambda auto=False: True),             patch.object(st, "plotly_chart", lambda *args, **kwargs: None),             patch.object(st, "download_button", lambda *args, **kwargs: None):
            page.render()

    at = _run_app(app)
    at.button(key="save_key_uncertainties").click().run()

    assert "key_uncertainties" not in mark_calls
    uncertainty_name = at.session_state["key_uncertainties"][0]["Uncertainty"]
    assert at.session_state["resolution_list"][uncertainty_name] == {"Option A": "Y"}
    assert at.session_state["risk_register"] == [{"Risk": "Risk A"}]



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


def test_planner_save_does_not_invalidate_risk_on_execution_metadata():
    mark_calls = []

    def app():
        import streamlit as st
        from modules import tab6_resolution_planner as page
        from utils.session import init_session
        from unittest.mock import patch

        importlib = __import__("importlib")
        importlib.reload(page)

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

        def record_change(session, stage):
            mark_calls.append(stage)

        with patch.object(page, "mark_stage_changed", record_change),             patch.object(page, "save_session", lambda auto=False: True):
            page.render()

    at = _run_app(app)
    at.button(key="save_resolution_planner").click().run()

    assert "resolution_planner" not in mark_calls
    assert at.session_state["risk_register"] == [{"Risk": "Risk A"}]



def test_risk_register_dropdowns_source_team_and_planner_and_normalize_others():
    from modules import tab7_risk_register as page

    session = {
        "team_members": [{"Name": "Team RE", "Function / Role": "RE"}],
        "resolution_planner": [{"Action Owner": "Planner PE"}],
        "risk_register": [],
    }

    assert page._risk_owner_options(session) == ["", "Team RE", "Planner PE"]

    rows = [{
        "Action Owner": "Team RE",
        "Contingency Plan": "Others",
        "Custom Contingency": "Trigger additional history matching",
        "Impact/Consequence": "Others",
        "Custom Consequence": "Potential uncertainty in forecast recovery",
        "Custom Owner": "",
    }]
    normalized = page._normalize_risk_rows(rows, ["", "Team RE", "Planner PE"])

    assert normalized[0]["Action Owner"] == "Team RE"
    assert normalized[0]["Contingency Plan"] == "Trigger additional history matching"
    assert normalized[0]["Impact/Consequence"] == "Potential uncertainty in forecast recovery"
    assert "Custom Contingency" not in normalized[0]
    assert "Custom Consequence" not in normalized[0]


def test_planner_status_counts_handles_workplan_rows():
    from modules import tab6_resolution_planner as page

    rows = [
        {"Part of Workplan": True, "Status": "In Progress"},
        {"Part of Workplan": True, "Status": "Resolved"},
        {"Part of Workplan": False, "Status": "Closed"},
        {"Part of Workplan": True, "Status": ""},
    ]

    counts = page._planner_status_counts(rows)

    assert int(counts.loc["In Progress", "Workplan actions"]) == 1
    assert int(counts.loc["Resolved", "Workplan actions"]) == 1
    assert int(counts.loc["Open", "Workplan actions"]) == 1
    assert int(counts["Workplan actions"].sum()) == 3


def test_study_repository_resume_opens_last_saved_page():
    from unittest.mock import patch

    def app():
        import streamlit as st
        from modules import tab_study_repository as page
        from utils.session import init_session

        init_session()
        summaries = [{
            "project_name": "Resume Study",
            "field_name": "North Field",
            "phase": "PGR1",
            "completion": 62,
            "study_lifecycle": "Draft",
            "study_revision": 4,
            "last_edited_by": "Engineer A",
            "last_edited_at": "2026-10-01T10:00:00",
            "resume_page": "6️⃣ Resolution Planner",
        }]

        with patch.object(page, "list_sessions", lambda: summaries),              patch.object(page, "load_session_record", lambda summary: True):
            page.render()

    at = _run_app(app)

    assert at.button(key="repository_edit_0")
    at.button(key="repository_edit_0").click().run()

    assert not at.exception
    assert at.session_state["study_access_mode"] == "edit"
    assert at.session_state["current_page"] == "6️⃣ Resolution Planner"


def test_resolution_planner_uses_native_date_picker_and_target_completion_label():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "modules/tab6_resolution_planner.py").read_text(encoding="utf-8")

    assert '"Start Date": st.column_config.DateColumn(' in source
    assert '"Required Completion": st.column_config.DateColumn(' in source
    assert 'format="DD/MM/YYYY"' in source
    assert '"Target Completion Date"' in source


def test_resolution_planner_normalizes_calendar_dates_back_to_study_format():
    from datetime import date
    from modules import tab6_resolution_planner as page

    prepared = page._prepare_planner_draft([{
        "Resolution Action": "Test action",
        "Duration (months)": 3,
        "Progress (0-1)": 0.50,
        "Start Date": "05/10/2026",
        "Required Completion": "31/12/2026",
        "Part of Workplan": True,
    }])

    assert str(prepared.loc[0, "Start Date"])[:10] == "2026-10-05"
    assert str(prepared.loc[0, "Required Completion"])[:10] == "2026-12-31"

    normalized = page._normalize_planner_draft([{
        "Resolution Action": "Test action",
        "Duration (months)": 3,
        "Progress (%)": 75,
        "Start Date": date(2026, 10, 5),
        "Required Completion": date(2026, 12, 31),
        "Part of Workplan": True,
    }])

    assert normalized[0]["Start Date"] == "05/10/2026"
    assert normalized[0]["Required Completion"] == "31/12/2026"
    assert normalized[0]["Progress (0-1)"] == 0.75


def test_live_gantt_builds_from_unsaved_workplan_draft():
    from modules import tab6_resolution_planner as page

    rows = [
        {
            "Resolution Action": "Acquire surveillance data",
            "Part of Workplan": True,
            "Start Date": "01/10/2026",
            "Duration (months)": 6,
            "Progress (0-1)": 0.5,
            "Action Owner": "RE User",
            "Status": "In Progress",
            "Required Completion": "31/03/2027",
        },
        {
            "Resolution Action": "Decision gate",
            "Part of Workplan": True,
            "Start Date": "15/10/2026",
            "Duration (months)": 0,
            "Progress (0-1)": 1.0,
            "Action Owner": "PE User",
            "Status": "Resolved",
            "Required Completion": "15/10/2026",
        },
        {
            "Resolution Action": "Missing start",
            "Part of Workplan": True,
            "Start Date": "",
            "Duration (months)": 3,
            "Progress (0-1)": 0.25,
            "Action Owner": "RE User",
            "Status": "Open",
        },
    ]

    figure, count, missing = page._build_live_gantt(rows)

    assert figure is not None
    assert count == 2
    assert missing == ["Missing start"]
    assert len(figure.data) >= 3  # planned/progress + milestone/deadline traces


def test_resolution_planner_uses_bounded_months_and_percentage_progress():
    from modules import tab6_resolution_planner as page

    assert page._MONTH_OPTIONS == list(range(13))

    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "modules/tab6_resolution_planner.py").read_text(encoding="utf-8")

    assert '"Duration (months)": st.column_config.SelectboxColumn(' in source
    assert 'options=_MONTH_OPTIONS' in source
    assert 'Every edit reruns the app and refreshes the' in source
    assert '"Progress (%)": st.column_config.NumberColumn(' in source
    assert 'min_value=0' in source
    assert 'max_value=100' in source
    assert 'format="%d%%"' in source
    assert '"Progress (0-1)": None' in source


def test_resolution_planner_percentage_maps_back_to_canonical_fraction():
    from modules import tab6_resolution_planner as page

    rows = [{"Progress (%)": 75, "Duration (months)": 12}]
    # Mirror the persistence conversion performed by the planner editor.
    normalized = []
    for row in rows:
        next_row = dict(row)
        next_row["Progress (0-1)"] = max(
            0.0,
            min(1.0, page.safe_float(next_row.get("Progress (%)", 0), default=0.0) / 100.0),
        )
        next_row["Duration (months)"] = max(
            0,
            min(12, int(page.safe_float(next_row.get("Duration (months)", 0), default=0))),
        )
        normalized.append(next_row)

    assert normalized[0]["Progress (0-1)"] == 0.75
    assert normalized[0]["Duration (months)"] == 12


def test_live_gantt_uses_current_percentage_draft_value():
    from modules import tab6_resolution_planner as page

    rows = [{
        "Resolution Action": "Risk mitigation",
        "Part of Workplan": True,
        "Start Date": "01/10/2026",
        "Duration (months)": 4,
        "Progress (%)": 75,
        "Progress (0-1)": 0.10,
        "Action Owner": "Owner",
        "Status": "In Progress",
    }]

    live_rows = page._normalize_planner_draft(rows)
    assert live_rows[0]["Progress (0-1)"] == 0.75

    figure, count, missing = page._build_live_gantt(live_rows)
    assert figure is not None
    assert count == 1
    assert missing == []



def test_risk_register_readiness_message_is_not_assessment_only():
    project_root = Path(__file__).resolve().parents[1]
    source = (project_root / "modules/tab7_risk_register.py").read_text(encoding="utf-8")

    assert "PRA readiness" in source
    assert "Assessment complete." in source
    assert "Owner, Consequence and/or Contingency details." in source
    assert "Ready for PRA Output." in source


def test_risk_register_form_is_explicit_save_transaction():
    def app():
        import streamlit as st
        import importlib
        from modules import tab7_risk_register as page
        from utils.session import init_session
        importlib.reload(page)

        page.render_bowtie_editor = lambda *args, **kwargs: None

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


@pytest.mark.parametrize(
    "module_name",
    [
        "modules.tab_intelligence",
        "modules.tab_barrier_management",
        "modules.tab_assurance",
        "modules.tab_revision_history",
    ],
)
def test_next_wave_modules_import(module_name):
    __import__(module_name)

def test_markdown_adapter_is_reload_safe():
    from utils.ui import _install_markdown_adapter

    class FakeStreamlit:
        def __init__(self):
            self.calls = []

        def markdown(self, body, unsafe_allow_html=False, **kwargs):
            self.calls.append((body, unsafe_allow_html, kwargs))
            return "ok"

    fake = FakeStreamlit()

    _install_markdown_adapter(fake)
    first_adapter = fake.markdown
    _install_markdown_adapter(fake)
    second_adapter = fake.markdown

    assert first_adapter is not second_adapter
    assert fake.markdown("hello", unsafe_allow_html=True) == "ok"
    assert fake.calls == [("hello", True, {})]


def test_excel_export_is_deferred_until_requested():
    from unittest.mock import patch

    project_root = Path(__file__).resolve().parents[1]
    import utils.export_excel as export_excel

    calls = []

    def fake_build_excel_export():
        calls.append(True)
        return b"fake-xlsx"

    with patch.object(export_excel, "build_excel_export", fake_build_excel_export):
        at = __import__("streamlit.testing.v1", fromlist=["AppTest"]).AppTest.from_file(
            project_root / "surm.py",
            default_timeout=20,
        ).run()

        assert not at.exception
        assert calls == []

        at.button(key="prepare_excel_export").click().run()
        assert not at.exception
        assert calls == [True]
        assert at.download_button

def test_entrypoint_boots_as_a_streamlit_app():
    project_root = Path(__file__).resolve().parents[1]

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(
        project_root / "surm.py",
        default_timeout=20,
    ).run()

    assert not at.exception
    assert at.markdown or at.title or at.header
    assert at.button


def test_streamlit_local_runtime_config_is_stable_for_synced_worktrees():
    project_root = Path(__file__).resolve().parents[1]
    import tomllib

    config = tomllib.loads(
        (project_root / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    )
    server = config["server"]

    # Local file changes must not trigger a second script execution while the
    # browser is still hydrating, which can produce a flash-then-blank canvas.
    assert server["runOnSave"] is False
    assert server["fileWatcherType"] in {"auto", "watchdog", "poll", "none"}
    blacklist = set(server.get("folderWatchBlacklist", []))
    assert {".git", ".venv", "__pycache__", ".pytest_cache"} <= blacklist


def test_all_first_party_python_sources_compile():
    project_root = Path(__file__).resolve().parents[1]
    for path in sorted(project_root.rglob("*.py")):
        if any(part in {".venv", ".git", "__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")


def test_markdown_adapter_remains_idempotent_across_module_reload():
    import importlib
    import streamlit as st
    import utils.ui as ui

    importlib.reload(ui)
    original = st._surm_original_markdown
    wrapped_once = st.markdown

    importlib.reload(ui)
    assert st._surm_original_markdown is original
    assert st.markdown is not wrapped_once
    assert getattr(st._surm_original_markdown, "__name__", "") == "markdown"

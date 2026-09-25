from pathlib import Path


TAB4 = Path(__file__).resolve().parents[1] / "modules" / "tab4_key_uncertainties.py"
TEAM = Path(__file__).resolve().parents[1] / "modules" / "tab_documentation.py"
TAB6 = Path(__file__).resolve().parents[1] / "modules" / "tab6_resolution_planner.py"


def test_tab4_uses_three_to_two_layout_for_matrix_and_tornado_details():
    source = TAB4.read_text(encoding="utf-8")

    assert source.count('st.columns([3, 2], gap="large")') == 2
    assert "build_uncertainty_matrix(matrix_display, show_full_names=True)" in source
    assert "build_tornado_chart(active, full_labels=True)" in source


def test_team_and_planner_owner_controls_are_present():
    team_source = TEAM.read_text(encoding="utf-8")
    planner_source = TAB6.read_text(encoding="utf-8")

    assert "FDP Lead" in team_source
    assert "TEAM_ROLE_OPTIONS" in team_source
    assert "build_owner_options(st.session_state)" in planner_source
    assert "SelectboxColumn(" in planner_source
    assert '_OTHER_OWNER_OPTION = "Others"' in planner_source
    assert "Other Owner Name" in planner_source
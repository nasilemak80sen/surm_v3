from modules.tab6_resolution_planner import (
    _normalize_owner_rows,
    _planner_quality,
    build_owner_options,
)
from modules.tab_documentation import TEAM_ROLE_OPTIONS


def test_team_role_options_include_fdp_lead():
    assert "FDP Lead" in TEAM_ROLE_OPTIONS


def test_owner_options_are_derived_from_team_names_and_existing_custom_names():
    session = {
        "team_members": [
            {"Name": "Engineer A", "Function / Role": "RE"},
            {"Name": "Engineer B", "Function / Role": "FDP Lead"},
            {"Name": "", "Function / Role": "PE"},
            {"Name": "Engineer A", "Function / Role": "RE"},
        ],
        "resolution_planner": [
            {"Action Owner": "External Specialist"},
        ],
    }

    assert build_owner_options(session) == [
        "",
        "Engineer A",
        "Engineer B",
        "External Specialist",
        "Others",
    ]


def test_others_requires_a_custom_owner_name_and_normalizes_on_save():
    rows = [
        {
            "Action Owner": "Others",
            "Other Owner Name": "External Specialist",
            "Part of Workplan": True,
        },
        {
            "Action Owner": "Others",
            "Other Owner Name": "",
            "Part of Workplan": True,
        },
    ]

    _, missing_owner = _planner_quality(rows)
    assert missing_owner == 1

    normalized = _normalize_owner_rows(rows)
    assert normalized[0]["Action Owner"] == "External Specialist"
    assert "Other Owner Name" not in normalized[0]
    assert normalized[1]["Action Owner"] == ""
    assert "Other Owner Name" not in normalized[1]
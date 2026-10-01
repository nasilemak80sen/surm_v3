from utils.logic import (
    calculate_risk_rating,
    compute_combined_rating,
    compute_weighted_score,
    is_risk_assessed,
    score_to_bin,
    build_impact_table,
    build_risk_register,
)


def test_weighted_score_excludes_na_from_denominator():
    decisions = [
        {"Key Decision": "Decision A", "Weight (1-3)": 3},
        {"Key Decision": "Decision B", "Weight (1-3)": 1},
    ]
    row = {
        "Decision A": "H",
        "Decision B": "NA",
    }

    assert compute_weighted_score(row, decisions) == 3.0


def test_weighted_score_preserves_existing_weighting():
    decisions = [
        {"Key Decision": "Decision A", "Weight (1-3)": 3},
        {"Key Decision": "Decision B", "Weight (1-3)": 1},
    ]
    row = {
        "Decision A": "H",
        "Decision B": "L",
    }

    assert compute_weighted_score(row, decisions) == 2.5


def test_rating_bins_preserve_existing_three_bucket_logic():
    assert score_to_bin(3.0) == "H"
    assert score_to_bin(2.0) == "M"
    assert score_to_bin(1.0) == "L"


def test_combined_rating_preserves_existing_order():
    assert compute_combined_rating("H", "H") == "HH"
    assert compute_combined_rating("M", "H") == "MH"
    assert compute_combined_rating("L", "L") == "LL"


def test_new_risk_is_not_assessed_until_both_dimensions_exist():
    assert calculate_risk_rating("", "") == "Not Assessed"
    assert calculate_risk_rating("H", "") == "Not Assessed"
    assert calculate_risk_rating("", "H") == "Not Assessed"
    assert is_risk_assessed({"Likelihood (H/M/L)": "", "Impact (H/M/L)": ""}) is False


def test_assessed_risk_uses_existing_matrix():
    assert calculate_risk_rating("H", "H") == "Extreme"
    assert calculate_risk_rating("H", "M") == "High"
    assert calculate_risk_rating("M", "M") == "Medium"
    assert calculate_risk_rating("L", "L") == "Low"
    assert is_risk_assessed({
        "Likelihood (H/M/L)": "M",
        "Impact (H/M/L)": "H",
    }) is True


def test_new_risk_owner_is_inherited_from_linked_resolution_planner():
    import streamlit as st

    st.session_state["_mapping"] = {
        "resolution_options": ["Option A"],
        "risks": ["Risk A"],
    }
    st.session_state["uncertainties"] = [{
        "name": "U1",
        "selected": True,
        "risks": ["Risk A"],
    }]
    st.session_state["resolution_planner"] = [{
        "Resolution Action": "Option A",
        "Action Owner": "Planner Owner",
    }]
    st.session_state["risk_register"] = []

    key_unc_df = __import__("pandas").DataFrame([{
        "Uncertainty": "U1",
        "Combined Rating": "HH",
    }])
    resolution_df = __import__("pandas").DataFrame([{
        "Uncertainty": "U1",
        "Rating": "HH",
        "Option A": "Y",
    }])

    result = build_risk_register(key_unc_df, resolution_df)

    assert result.loc[0, "Action Owner"] == "Planner Owner"
    assert result.loc[0, "Action Owner Source"] == "planner_default"


def test_planner_owner_lineage_survives_until_manual_override():
    import pandas as pd
    import streamlit as st

    st.session_state["_mapping"] = {
        "resolution_options": ["Option A"],
        "risks": ["Risk A"],
    }
    st.session_state["uncertainties"] = [{
        "name": "U1",
        "selected": True,
        "risks": ["Risk A"],
    }]
    st.session_state["resolution_planner"] = [{
        "Resolution Action": "Option A",
        "Action Owner": "Planner Owner",
    }]
    st.session_state["risk_register"] = [{
        "Risk": "Risk A",
        "Action Owner": "Planner Owner",
        "Action Owner Source": "planner_default",
        "Likelihood (H/M/L)": "M",
        "Impact (H/M/L)": "M",
    }]

    key_unc_df = pd.DataFrame([{"Uncertainty": "U1"}])
    resolution_df = pd.DataFrame([{
        "Uncertainty": "U1",
        "Option A": "Y",
    }])

    result = build_risk_register(key_unc_df, resolution_df)
    assert result.loc[0, "Action Owner"] == "Planner Owner"
    assert result.loc[0, "Action Owner Source"] == "planner_default"

    st.session_state["risk_register"][0]["Action Owner"] = "Manual Owner"
    st.session_state["risk_register"][0]["Action Owner Source"] = "manual"

    result = build_risk_register(key_unc_df, resolution_df)
    assert result.loc[0, "Action Owner"] == "Manual Owner"
    assert result.loc[0, "Action Owner Source"] == "manual"


def test_existing_risk_owner_is_preserved_over_planner_default():
    import streamlit as st

    st.session_state["_mapping"] = {
        "resolution_options": ["Option A"],
        "risks": ["Risk A"],
    }
    st.session_state["uncertainties"] = [{
        "name": "U1",
        "selected": True,
        "risks": ["Risk A"],
    }]
    st.session_state["resolution_planner"] = [{
        "Resolution Action": "Option A",
        "Action Owner": "Planner Owner",
    }]
    st.session_state["risk_register"] = [{
        "Risk": "Risk A",
        "Action Owner": "Manual Override",
        "Action Owner Source": "manual",
        "Likelihood (H/M/L)": "M",
        "Impact (H/M/L)": "M",
    }]

    key_unc_df = __import__("pandas").DataFrame([{
        "Uncertainty": "U1",
        "Combined Rating": "HH",
    }])
    resolution_df = __import__("pandas").DataFrame([{
        "Uncertainty": "U1",
        "Rating": "HH",
        "Option A": "Y",
    }])

    result = build_risk_register(key_unc_df, resolution_df)

    assert result.loc[0, "Action Owner"] == "Manual Override"
    assert result.loc[0, "Action Owner Source"] == "manual"


def test_weighted_score_accepts_numeric_string_weights():
    decisions = [
        {"Key Decision": "Decision A", "Weight (1-3)": "3.0"},
        {"Key Decision": "Decision B", "Weight (1-3)": "1"},
    ]
    row = {"Decision A": "H", "Decision B": "L"}
    assert compute_weighted_score(row, decisions) == 2.5


def test_new_impact_rows_do_not_invent_a_degree_rating():
    import streamlit as st

    st.session_state["uncertainties"] = [{"name": "U1", "selected": True}]
    st.session_state["key_decisions"] = [{"Key Decision": "D1", "Weight (1-3)": 3}]
    st.session_state["impact_assessment"] = []

    table = build_impact_table()

    assert table.loc[0, "Degree of Uncertainty"] == ""


def test_invalid_risk_dimensions_are_not_treated_as_assessed():
    assert is_risk_assessed({
        "Likelihood (H/M/L)": "unexpected",
        "Impact (H/M/L)": "H",
    }) is False


def test_blank_combined_rating_is_not_coerced_to_low():
    assert compute_combined_rating("", "H") == ""
    assert compute_combined_rating("H", "") == ""

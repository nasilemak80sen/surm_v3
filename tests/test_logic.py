from utils.logic import (
    calculate_risk_rating,
    compute_combined_rating,
    compute_weighted_score,
    is_risk_assessed,
    score_to_bin,
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

"""
utils/logic.py

The cascade engine mirrors the existing Excel methodology while keeping
calculations independent from the page UI. Enhancements here are intentionally
additive: the original H/M/L scoring rules and ranking order are preserved.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


RATING_VALUE = {"H": 3, "M": 2, "L": 1, "NA": 0}
RATING_RANK = {
    "HH": 1, "HM": 2, "HL": 3,
    "MH": 4, "MM": 5, "ML": 6,
    "LH": 7, "LM": 8, "LL": 9,
}

RISK_MATRIX = {
    ("H", "H"): "Extreme",
    ("H", "M"): "High",
    ("H", "L"): "Medium",
    ("M", "H"): "High",
    ("M", "M"): "Medium",
    ("M", "L"): "Low",
    ("L", "H"): "Medium",
    ("L", "M"): "Low",
    ("L", "L"): "Low",
}

RISK_RATING_ORDER = ("Extreme", "High", "Medium", "Low", "Not Assessed")


def compute_bin_thresholds() -> dict[str, tuple[float, float]]:
    """Mirror the existing Excel thirds-based rating thresholds."""
    max_v, min_v = 3.0, 1.0
    third = (max_v - min_v) / 3
    return {
        "High": (min_v + 2 * third, max_v),
        "Mid": (min_v + third, min_v + 2 * third),
        "Low": (min_v, min_v + third),
    }


BINS = compute_bin_thresholds()


def score_to_bin(score: float) -> str:
    if score >= BINS["High"][0]:
        return "H"
    if score >= BINS["Mid"][0]:
        return "M"
    return "L"


def compute_weighted_score(impact_row: dict, decisions: list) -> float:
    """
    Preserve the current scoring rule:
    NA contributes neither score nor denominator weight.
    """
    total_weight = 0
    weighted_sum = 0.0

    for decision in decisions:
        name = decision["Key Decision"]
        weight = decision.get("Weight (1-3)", 1)
        value = RATING_VALUE.get(impact_row.get(name, "NA"), 0)
        if value > 0:
            weighted_sum += value * weight
            total_weight += weight

    if total_weight == 0:
        return 1.0

    return weighted_sum / total_weight


def compute_combined_rating(deg_uncertainty: str, impact_bin: str) -> str:
    """Return the two-letter degree × impact rating used by SURM."""
    degree = deg_uncertainty.strip().upper() if deg_uncertainty else "L"
    impact = impact_bin.strip().upper() if impact_bin else "L"

    if degree not in ("H", "M", "L"):
        degree = "L"
    if impact not in ("H", "M", "L"):
        impact = "L"

    return degree + impact


def calculate_risk_rating(
    likelihood: Any,
    impact: Any,
) -> str:
    """Calculate risk rating without inventing an assessment."""
    likelihood_value = str(likelihood or "").strip().upper()
    impact_value = str(impact or "").strip().upper()

    return RISK_MATRIX.get(
        (likelihood_value, impact_value),
        "Not Assessed",
    )


def is_risk_assessed(row: dict[str, Any]) -> bool:
    """Return True only when both dimensions have been explicitly assessed."""
    return bool(
        str(row.get("Likelihood (H/M/L)", "") or "").strip()
        and str(row.get("Impact (H/M/L)", "") or "").strip()
    )


def build_impact_table() -> pd.DataFrame:
    """
    Build the editable impact matrix from selected uncertainties and decisions.
    Existing values are preserved by uncertainty name for backwards compatibility.
    """
    selected = [
        u
        for u in st.session_state["uncertainties"]
        if u.get("selected")
    ]
    decisions = st.session_state["key_decisions"]
    existing = {
        row["Uncertainty"]: row
        for row in st.session_state.get("impact_assessment", [])
        if isinstance(row, dict) and row.get("Uncertainty")
    }

    decision_names = [d["Key Decision"] for d in decisions]

    rows = []
    for uncertainty in selected:
        name = uncertainty["name"]
        existing_row = existing.get(name, {})
        row = {
            "Uncertainty": name,
            "Degree of Uncertainty": existing_row.get(
                "Degree of Uncertainty",
                existing_row.get("Degree of Uncertainty (H/M/L)", "L"),
            ),
        }
        for decision_name in decision_names:
            row[decision_name] = existing_row.get(decision_name, "NA")
        rows.append(row)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _uncertainty_id_for_name(name: str) -> str:
    """Resolve the durable uncertainty ID while retaining name compatibility."""
    for uncertainty in st.session_state.get("uncertainties", []):
        if uncertainty.get("name") == name:
            return str(
                uncertainty.get("uncertainty_id")
                or uncertainty.get("id")
                or ""
            )
    return ""


def compute_key_uncertainties(
    impact_df: pd.DataFrame,
    decisions: list,
) -> pd.DataFrame:
    """Calculate and rank uncertainties using the existing scoring rules."""
    if impact_df.empty:
        return pd.DataFrame()

    degree_col = "Degree of Uncertainty"
    if degree_col not in impact_df.columns:
        degree_col = "Degree of Uncertainty (H/M/L)"

    rows = []
    for _, row in impact_df.iterrows():
        degree = row.get(degree_col, "L")
        score = compute_weighted_score(row.to_dict(), decisions)
        impact_bin = score_to_bin(score)
        rating = compute_combined_rating(degree, impact_bin)

        rows.append({
            "uncertainty_id": _uncertainty_id_for_name(row["Uncertainty"]),
            "Uncertainty": row["Uncertainty"],
            "Degree of Uncertainty": degree,
            "Impact (Weighted)": round(score, 3),
            "Impact Bin": impact_bin,
            "Combined Rating": rating,
            "Rank": RATING_RANK.get(rating, 9),
            "Include in Plan": True,
            "Resolution Achieved": False,
        })

    return (
        pd.DataFrame(rows)
        .sort_values("Rank")
        .reset_index(drop=True)
    )


def build_resolution_matrix(key_unc_df: pd.DataFrame) -> pd.DataFrame:
    """Build the selected-uncertainty × resolution-option matrix."""
    if key_unc_df.empty:
        return pd.DataFrame()

    options = st.session_state["_mapping"]["resolution_options"]
    existing = st.session_state.get("resolution_list", {})

    rows = []
    for _, row in key_unc_df.iterrows():
        name = row["Uncertainty"]
        existing_row = existing.get(name, {})
        output = {
            "uncertainty_id": row.get("uncertainty_id", ""),
            "Uncertainty": name,
            "Rating": row["Combined Rating"],
        }
        for option in options:
            output[option] = existing_row.get(option, "")
        rows.append(output)

    return pd.DataFrame(rows)


def build_resolution_planner(
    resolution_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Group the resolution matrix into action-level workplan rows.

    A deterministic RES-### identifier is added so future edits can key on
    action identity rather than the display label alone.
    """
    if resolution_df.empty:
        return pd.DataFrame()

    options = st.session_state["_mapping"]["resolution_options"]
    existing = {
        row["Resolution Action"]: row
        for row in st.session_state.get("resolution_planner", [])
        if isinstance(row, dict) and row.get("Resolution Action")
    }

    rows = []
    for index, option in enumerate(options, start=1):
        if option not in resolution_df.columns:
            continue

        mask = resolution_df[option] == "Y"
        associated = resolution_df.loc[mask, "Uncertainty"].tolist()
        ratings = resolution_df.loc[mask, "Rating"].tolist()

        if not associated:
            continue

        existing_row = existing.get(option, {})
        rows.append({
            "resolution_id": existing_row.get(
                "resolution_id",
                f"RES-{index:03d}",
            ),
            "#": index,
            "Resolution Action": option,
            "Associated Uncertainties": "; ".join(associated),
            "Ratings": "; ".join(ratings),
            "Description": existing_row.get("Description", ""),
            "Duration (months)": existing_row.get("Duration (months)", 0),
            "Resources": existing_row.get("Resources", ""),
            "Constraints": existing_row.get("Constraints", ""),
            "Start Date": existing_row.get("Start Date", ""),
            "Required Completion": existing_row.get("Required Completion", ""),
            "Progress (0-1)": existing_row.get("Progress (0-1)", 0.0),
            "Status": existing_row.get("Status", "Open"),
            "Action Owner": existing_row.get("Action Owner", ""),
            "Part of Workplan": existing_row.get("Part of Workplan", True),
            "Remarks": existing_row.get("Remarks", ""),
        })

    return pd.DataFrame(rows)


def _all_known_risks() -> list[str]:
    """Return master risks plus risks introduced by custom uncertainties."""
    mapping_risks = list(st.session_state["_mapping"].get("risks", []))
    custom_risks = [
        risk
        for uncertainty in st.session_state.get("uncertainties", [])
        if isinstance(uncertainty, dict)
        for risk in uncertainty.get("risks", [])
    ]

    output: list[str] = []
    for risk in [*mapping_risks, *custom_risks]:
        if risk not in output:
            output.append(risk)
    return output


def build_risk_register(
    key_unc_df: pd.DataFrame,
    resolution_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build one row per linked risk.

    Existing risk assessments are preserved. New risks intentionally start as
    Not Assessed instead of silently becoming Medium/Medium.
    """
    if key_unc_df.empty:
        return pd.DataFrame()

    options = st.session_state["_mapping"]["resolution_options"]
    uncertainty_details = {
        u["name"]: u
        for u in st.session_state.get("uncertainties", [])
        if isinstance(u, dict)
    }
    existing = {
        row["Risk"]: row
        for row in st.session_state.get("risk_register", [])
        if isinstance(row, dict) and row.get("Risk")
    }

    res_lookup: dict[str, list[str]] = {}
    if not resolution_df.empty:
        for _, row in resolution_df.iterrows():
            uncertainty_name = row["Uncertainty"]
            res_lookup[uncertainty_name] = [
                option
                for option in options
                if row.get(option) == "Y"
            ]

    rows = []
    for risk_index, risk in enumerate(_all_known_risks(), start=1):
        linked_uncertainties: list[str] = []

        for _, row in key_unc_df.iterrows():
            uncertainty_name = row["Uncertainty"]
            details = uncertainty_details.get(uncertainty_name, {})
            if risk in details.get("risks", []):
                linked_uncertainties.append(uncertainty_name)

        if not linked_uncertainties:
            continue

        all_resolutions: list[str] = []
        for uncertainty_name in linked_uncertainties:
            all_resolutions.extend(
                res_lookup.get(uncertainty_name, [])
            )

        unique_resolutions = list(dict.fromkeys(all_resolutions))
        existing_row = existing.get(risk, {})

        likelihood = existing_row.get("Likelihood (H/M/L)", "")
        impact = existing_row.get("Impact (H/M/L)", "")

        rows.append({
            "risk_id": existing_row.get(
                "risk_id",
                f"RSK-{risk_index:03d}",
            ),
            "#": risk_index,
            "Risk": risk,
            "Uncertainty/Causes": "\n".join(
                f"{index + 1}. {uncertainty}"
                for index, uncertainty in enumerate(linked_uncertainties)
            ),
            "Resolution Plan": (
                "\n".join(
                    f"- {resolution}"
                    for resolution in unique_resolutions
                )
                if unique_resolutions
                else ""
            ),
            "Action Owner": existing_row.get("Action Owner", ""),
            "Contingency Plan": existing_row.get("Contingency Plan", ""),
            "Impact/Consequence": existing_row.get("Impact/Consequence", ""),
            "Likelihood (H/M/L)": likelihood,
            "Impact (H/M/L)": impact,
            "Risk Rating": calculate_risk_rating(likelihood, impact),
            "Risk Status": existing_row.get("Risk Status", "Open"),
            "Remarks": existing_row.get("Remarks", ""),
        })

    return pd.DataFrame(rows)


def build_pra_output(risk_register_df: pd.DataFrame) -> pd.DataFrame:
    """Return the reporting view of the risk register."""
    if risk_register_df.empty:
        return pd.DataFrame()

    columns = [
        "#",
        "Risk",
        "Uncertainty/Causes",
        "Impact/Consequence",
        "Resolution Plan",
        "Action Owner",
        "Likelihood (H/M/L)",
        "Impact (H/M/L)",
        "Risk Rating",
        "Risk Status",
        "Remarks",
    ]
    available = [
        column for column in columns
        if column in risk_register_df.columns
    ]
    return risk_register_df[available].copy()

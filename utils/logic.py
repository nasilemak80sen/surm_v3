"""
utils/logic.py
The cascade engine that mirrors Excel's auto-population formulas.
All scoring and ranking logic lives here, cleanly separated from UI.
"""
import streamlit as st
import pandas as pd

RATING_VALUE = {"H": 3, "M": 2, "L": 1, "NA": 0}
RATING_RANK  = {"HH":1,"HM":2,"HL":3,"MH":4,"MM":5,"ML":6,"LH":7,"LM":8,"LL":9}

# ── Rating bin thresholds (mirrors Excel Setup sheet) ─────────────────
def compute_bin_thresholds():
    max_v, min_v = 3.0, 1.0
    third = (max_v - min_v) / 3
    return {
        "High": (min_v + 2 * third, max_v),
        "Mid":  (min_v + third,     min_v + 2 * third),
        "Low":  (min_v,             min_v + third),
    }

BINS = compute_bin_thresholds()

def score_to_bin(score: float) -> str:
    if score >= BINS["High"][0]:   return "H"
    elif score >= BINS["Mid"][0]:  return "M"
    else:                          return "L"

# ── Tab 3 → weighted score ────────────────────────────────────────────
def compute_weighted_score(impact_row: dict, decisions: list) -> float:
    """
    impact_row: {decision_name: H/M/L/NA, ...}
    decisions:  [{Key Decision, Weight (1-3)}, ...]
    Returns weighted average score (1.0 – 3.0).
    """
    total_weight = 0
    weighted_sum = 0.0
    for d in decisions:
        name   = d["Key Decision"]
        weight = d.get("Weight (1-3)", 1)
        val    = RATING_VALUE.get(impact_row.get(name, "NA"), 0)
        if val > 0:
            weighted_sum  += val * weight
            total_weight  += weight
    if total_weight == 0:
        return 1.0
    return weighted_sum / total_weight

def compute_combined_rating(deg_uncertainty: str, impact_bin: str) -> str:
    """e.g. deg=H, impact=M → HM"""
    d = deg_uncertainty.strip().upper() if deg_uncertainty else "L"
    i = impact_bin.strip().upper()      if impact_bin      else "L"
    if d not in ("H","M","L"): d = "L"
    if i not in ("H","M","L"): i = "L"
    return d + i

# ── Tab 3 → build full impact table ──────────────────────────────────
def build_impact_table() -> pd.DataFrame:
    """
    Reads session state for selected uncertainties & key decisions,
    merges with any existing impact_assessment data already entered by user,
    returns a clean DataFrame ready for st.data_editor().
    """
    selected    = [u for u in st.session_state["uncertainties"] if u["selected"]]
    decisions   = st.session_state["key_decisions"]
    existing    = {row["Uncertainty"]: row for row in st.session_state.get("impact_assessment", [])}

    decision_names = [d["Key Decision"] for d in decisions]

    rows = []
    for u in selected:
        name = u["name"]
        ex   = existing.get(name, {})
        row  = {
            "Uncertainty": name,
            "Degree of Uncertainty": ex.get("Degree of Uncertainty", ex.get("Degree of Uncertainty (H/M/L)", "L")),
        }
        for dn in decision_names:
            row[dn] = ex.get(dn, "NA")
        rows.append(row)

    return pd.DataFrame(rows) if rows else pd.DataFrame()

# ── Tab 4 → rank uncertainties ────────────────────────────────────────
def compute_key_uncertainties(impact_df: pd.DataFrame, decisions: list) -> pd.DataFrame:
    """
    Takes the filled impact assessment DataFrame,
    returns ranked DataFrame for Tab 4.
    """
    if impact_df.empty:
        return pd.DataFrame()

    degree_col = "Degree of Uncertainty"
    if degree_col not in impact_df.columns:
        degree_col = "Degree of Uncertainty (H/M/L)"

    rows = []
    for _, r in impact_df.iterrows():
        deg    = r.get(degree_col, "L")
        score  = compute_weighted_score(r.to_dict(), decisions)
        impact_bin = score_to_bin(score)
        rating = compute_combined_rating(deg, impact_bin)
        rows.append({
            "Uncertainty":           r["Uncertainty"],
            "Degree of Uncertainty": deg,
            "Impact (Weighted)":     round(score, 3),
            "Impact Bin":            impact_bin,
            "Combined Rating":       rating,
            "Rank":                  RATING_RANK.get(rating, 9),
            "Include in Plan":       True,
            "Resolution Achieved":   False,
        })

    df = pd.DataFrame(rows).sort_values("Rank").reset_index(drop=True)
    return df

# ── Tab 5 → init resolution matrix ───────────────────────────────────
def build_resolution_matrix(key_unc_df: pd.DataFrame) -> pd.DataFrame:
    """
    Rows = selected key uncertainties.
    Columns = resolution options from master mapping.
    Values = Y / (empty).
    """
    if key_unc_df.empty:
        return pd.DataFrame()

    options  = st.session_state["_mapping"]["resolution_options"]
    existing = st.session_state.get("resolution_list", {})

    rows = []
    for _, r in key_unc_df.iterrows():
        name = r["Uncertainty"]
        ex   = existing.get(name, {})
        row  = {"Uncertainty": name, "Rating": r["Combined Rating"]}
        for opt in options:
            row[opt] = ex.get(opt, "")
        rows.append(row)
    return pd.DataFrame(rows)

# ── Tab 6 → build resolution planner ─────────────────────────────────
def build_resolution_planner(resolution_df: pd.DataFrame) -> pd.DataFrame:
    """
    Reads resolution matrix, groups by resolution action,
    lists which uncertainties it addresses.
    """
    if resolution_df.empty:
        return pd.DataFrame()

    options  = st.session_state["_mapping"]["resolution_options"]
    existing = {row["Resolution Action"]: row for row in st.session_state.get("resolution_planner", [])}

    rows = []
    for i, opt in enumerate(options, 1):
        if opt not in resolution_df.columns:
            continue
        # which uncertainties selected Y for this resolution?
        mask  = resolution_df[opt] == "Y"
        assoc = resolution_df.loc[mask, "Uncertainty"].tolist()
        rates = resolution_df.loc[mask, "Rating"].tolist()
        if not assoc:
            continue
        ex = existing.get(opt, {})
        rows.append({
            "#":                       i,
            "Resolution Action":       opt,
            "Associated Uncertainties": "; ".join(assoc),
            "Ratings":                 "; ".join(rates),
            "Description":             ex.get("Description", ""),
            "Duration (months)":       ex.get("Duration (months)", 0),
            "Resources":               ex.get("Resources", ""),
            "Constraints":             ex.get("Constraints", ""),
            "Start Date":              ex.get("Start Date", ""),
            "Required Completion":     ex.get("Required Completion", ""),
            "Progress (0-1)":          ex.get("Progress (0-1)", 0.0),
            "Action Owner":            ex.get("Action Owner", ""),
            "Part of Workplan":        ex.get("Part of Workplan", True),
            "Remarks":                 ex.get("Remarks", ""),
        })
    return pd.DataFrame(rows)

# ── Tab 7 → build risk register ──────────────────────────────────────
def build_risk_register(key_unc_df: pd.DataFrame, resolution_df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per L2 Risk.
    Links uncertainties and their resolutions for each risk.
    """
    if key_unc_df.empty:
        return pd.DataFrame()

    all_risks  = st.session_state["_mapping"]["risks"]
    options    = st.session_state["_mapping"]["resolution_options"]
    unc_detail = {u["name"]: u for u in st.session_state["uncertainties"]}
    existing   = {row["Risk"]: row for row in st.session_state.get("risk_register", [])}

    # Build lookup: uncertainty → selected resolutions
    res_lookup = {}
    if not resolution_df.empty:
        for _, r in resolution_df.iterrows():
            uname = r["Uncertainty"]
            selected_res = [opt for opt in options if r.get(opt) == "Y"]
            res_lookup[uname] = selected_res

    rows = []
    for i, risk in enumerate(all_risks, 1):
        # which key uncertainties are linked to this risk?
        linked_uncs = []
        for _, r in key_unc_df.iterrows():
            u_detail = unc_detail.get(r["Uncertainty"], {})
            if risk in u_detail.get("risks", []):
                linked_uncs.append(r["Uncertainty"])
        if not linked_uncs:
            continue

        # collect unique resolutions for this risk
        all_res = []
        for u in linked_uncs:
            all_res.extend(res_lookup.get(u, []))
        unique_res = list(dict.fromkeys(all_res))  # preserve order, deduplicate

        ex = existing.get(risk, {})
        rows.append({
            "#":                    i,
            "Risk":                 risk,
            "Uncertainty/Causes":   "\n".join([f"{j+1}. {u}" for j, u in enumerate(linked_uncs)]),
            "Resolution Plan":      "\n".join([f"- {r}" for r in unique_res]) if unique_res else "",
            "Action Owner":         ex.get("Action Owner", ""),
            "Contingency Plan":     ex.get("Contingency Plan", ""),
            "Impact/Consequence":   ex.get("Impact/Consequence", ""),
            "Likelihood (H/M/L)":   ex.get("Likelihood (H/M/L)", "M"),
            "Impact (H/M/L)":       ex.get("Impact (H/M/L)", "M"),
            "Risk Rating":          ex.get("Risk Rating", ""),
            "Risk Status":          ex.get("Risk Status", "Open"),
            "Remarks":              ex.get("Remarks", ""),
        })
    return pd.DataFrame(rows)

# ── PRA output ────────────────────────────────────────────────────────
def build_pra_output(risk_register_df: pd.DataFrame) -> pd.DataFrame:
    if risk_register_df.empty:
        return pd.DataFrame()
    cols = [
        "#", "Risk", "Uncertainty/Causes", "Impact/Consequence",
        "Resolution Plan", "Action Owner", "Likelihood (H/M/L)",
        "Impact (H/M/L)", "Risk Rating", "Risk Status", "Remarks"
    ]
    available = [c for c in cols if c in risk_register_df.columns]
    return risk_register_df[available].copy()

"""
utils/session.py
Initialises all st.session_state keys on first load.
Acts as the single source of truth for app-wide state.
"""
import streamlit as st
import json, os

# Public set of default session keys (populated in init_session)
DEFAULT_SESSION_KEYS = set()

def load_master_mapping():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "surm_master_mapping.json")
    with open(path, "r") as f:
        return json.load(f)

def init_session():
    """Call once at the top of app.py — idempotent."""
    mapping = load_master_mapping()

    # ── Project meta ─────────────────────────────────────────────────
    defaults = {
        "project_name":        "",
        "field_name":          "",
        "project_phase":       "",
        "prep_name":           "",
        "prep_role":           "",
        "prep_date":           "",
        "rev_gg_name":         "",
        "rev_gg_role":         "",
        "rev_gg_date":         "",
        "rev_re_name":         "",
        "rev_re_role":         "",
        "rev_re_date":         "",
        "rev_pp_name":         "",
        "rev_pp_role":         "",
        "rev_pp_date":         "",
        "endorsed_name":       "",
        "endorsed_role":       "",
        "endorsed_date":       "",
        "team_members":        [{"Name": "", "Function / Role": "", "Date": ""}],

        # ── Tab 1: Uncertainties ──────────────────────────────────────
        # List of dicts: {id, discipline, name, selected, custom}
        "uncertainties":       _build_default_uncertainties(mapping),

        # ── Tab 2: Key decisions ──────────────────────────────────────
        # List of dicts: {decision, weight, description}
        "key_decisions":       [
            {"Key Decision": "No. of reactivated producers", "Weight (1-3)": 3, "Description": "How many wells to reactivate"},
            {"Key Decision": "No. of injectors",             "Weight (1-3)": 2, "Description": "VRR requirements, disposal vs injector, no of slots, injector placement"},
            {"Key Decision": "WAG injector pattern orientation", "Weight (1-3)": 2, "Description": "Follow the geological orientation"},
            {"Key Decision": "Injection strategy",           "Weight (1-3)": 1, "Description": "WAG injection cycle, rates, timing"},
        ],

        # ── Tab 3: Impact assessment ──────────────────────────────────
        # Populated dynamically from tabs 1 & 2; stored here for persistence within session
        "impact_assessment":   [],

        # ── Tab 4: Key uncertainties ──────────────────────────────────
        # Derived from tab 3 scoring; user marks which to carry forward
        "key_uncertainties":   [],

        # ── Tab 5: Resolution list ────────────────────────────────────
        # {uncertainty_name: [selected_resolutions]}
        "resolution_list":     {},

        # ── Tab 6: Resolution planner ─────────────────────────────────
        # List of dicts with full planner fields
        "resolution_planner":  [],

        # ── Tab 7: Risk register ──────────────────────────────────────
        # Auto-populated; user fills contingency & consequence
        "risk_register":       [],

        # ── PRA output ───────────────────────────────────────────────
        "pra_output":          [],

        # ── Master reference data (read-only) ─────────────────────────
        "_mapping":            mapping,

        # ── Persistence tracking ───────────────────────────────────────
        "_last_saved":         "",
        "_last_save_auto":     False,
        "_auto_save_enabled":  True,
        # ── UI customisation
        "ui_primary_color":    "#1F6B3A",
        "ui_background_color": "#F8FBFC",
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def _build_default_uncertainties(mapping):
    rows = []
    for u in mapping["uncertainties"]:
        rows.append({
            "id":         u["id"],
            "discipline": u["discipline"],
            "name":       u["name"],
            "selected":   False,
            "custom":     False,
            "risks":      u["risks"],
        })
    return rows

def get_selected_uncertainties():
    """Returns only the uncertainties the user has ticked in Tab 1."""
    return [u for u in st.session_state["uncertainties"] if u["selected"]]

def get_active_decisions():
    """Returns key decisions with weight > 0."""
    return [d for d in st.session_state["key_decisions"] if d.get("Weight (1-3)", 0) > 0]

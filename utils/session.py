"""
utils/session.py
Initialises all st.session_state keys on first load.

The module owns the interactive workspace defaults, while StudyDocument owns
the durable representation of the same study.
"""
import json
import os
from copy import deepcopy
from uuid import uuid4

import streamlit as st

from utils.coercion import safe_int


SURM_METHODOLOGY_VERSION = "SURM-2026.01"


DEFAULT_SESSION_STATE = {
    "project_name",
    "field_name",
    "project_phase",
    "study_id",
    "study_owner",
    "methodology_version",
    "study_mode",
    "current_page",
    "top_navigation",
    "study_access_mode",
    "prep_name",
    "prep_role",
    "prep_date",
    "rev_gg_name",
    "rev_gg_role",
    "rev_gg_date",
    "rev_re_name",
    "rev_re_role",
    "rev_re_date",
    "rev_pp_name",
    "rev_pp_role",
    "rev_pp_date",
    "endorsed_name",
    "endorsed_role",
    "endorsed_date",
    "team_members",
    "uncertainties",
    "key_decisions",
    "impact_assessment",
    "key_uncertainties",
    "resolution_list",
    "resolution_planner",
    "risk_register",
    "pra_output",
    "bowtie_register",
    "study_lifecycle",
    "study_revision",
    "study_change_log",
    "workflow_revisions",
    "workflow_snapshots",
    "ui_primary_color",
    "ui_background_color",
}


def load_master_mapping():
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "surm_master_mapping.json",
    )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def init_session():
    """Call once at the top of surm.py — idempotent."""
    mapping = load_master_mapping()

    defaults = {
        "project_name": "",
        "field_name": "",
        "project_phase": "",
        "study_id": str(uuid4()),
        "study_owner": os.environ.get("SURM_USER", "local-user"),
        "methodology_version": SURM_METHODOLOGY_VERSION,
        "study_mode": "new",
        "study_access_mode": "edit",
        "current_page": "📋 Overview",
        "top_navigation": "📋 Overview",
        "prep_name": "",
        "prep_role": "",
        "prep_date": "",
        "rev_gg_name": "",
        "rev_gg_role": "",
        "rev_gg_date": "",
        "rev_re_name": "",
        "rev_re_role": "",
        "rev_re_date": "",
        "rev_pp_name": "",
        "rev_pp_role": "",
        "rev_pp_date": "",
        "endorsed_name": "",
        "endorsed_role": "",
        "endorsed_date": "",
        "team_members": [
            {"Name": "", "Function / Role": "", "Date": ""}
        ],

        # Tab 1
        "uncertainties": _build_default_uncertainties(mapping),

        # Tab 2
        "key_decisions": [
            {
                "decision_id": "DEC-001",
                "Key Decision": "No. of reactivated producers",
                "Weight (1-3)": 3,
                "Description": "How many wells to reactivate",
            },
            {
                "decision_id": "DEC-002",
                "Key Decision": "No. of injectors",
                "Weight (1-3)": 2,
                "Description": "VRR requirements, disposal vs injector, no of slots, injector placement",
            },
            {
                "decision_id": "DEC-003",
                "Key Decision": "WAG injector pattern orientation",
                "Weight (1-3)": 2,
                "Description": "Follow the geological orientation",
            },
            {
                "decision_id": "DEC-004",
                "Key Decision": "Injection strategy",
                "Weight (1-3)": 1,
                "Description": "WAG injection cycle, rates, timing",
            },
        ],

        # Tab 3+
        "impact_assessment": [],
        "key_uncertainties": [],
        "resolution_list": {},
        "resolution_planner": [],
        "risk_register": [],
        "pra_output": [],
        "bowtie_register": {},

        # Study governance
        "study_lifecycle": "Draft",
        "study_revision": 0,
        "study_change_log": [],
        "workflow_revisions": {},
        "workflow_snapshots": {},

        # Master reference data
        "_mapping": mapping,

        # Persistence tracking
        "_last_saved": "",
        "_last_save_auto": False,
        "_auto_save_enabled": True,

        # UI customisation
        "ui_primary_color": "#1F6B3A",
        "ui_background_color": "#F8FBFC",
    }

    DEFAULT_SESSION_STATE.update(defaults)

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = deepcopy(value)

    if "_mapping" not in st.session_state:
        st.session_state["_mapping"] = mapping

    normalize_entity_ids()


def create_new_study() -> None:
    """Replace the current workspace with a fresh, unsaved study."""
    st.session_state.clear()
    init_session()


def _build_default_uncertainties(mapping):
    rows = []
    for u in mapping["uncertainties"]:
        numeric_id = safe_int(u.get("id"), default=len(rows) + 1)
        rows.append({
            "id": numeric_id,
            "uncertainty_id": f"UNC-{numeric_id:03d}",
            "discipline": u["discipline"],
            "name": u["name"],
            "selected": False,
            "custom": False,
            "risks": u["risks"],
        })
    return rows


def normalize_entity_ids() -> None:
    """Backfill stable IDs for legacy studies without changing their names/data."""
    uncertainties = st.session_state.get("uncertainties", [])
    used_uncertainty_ids = set()

    for item in uncertainties:
        if not isinstance(item, dict):
            continue
        existing = str(item.get("uncertainty_id") or "").strip()
        if existing:
            used_uncertainty_ids.add(existing)
            continue

        raw_id = item.get("id")
        if isinstance(raw_id, int) or str(raw_id).isdigit():
            candidate = f"UNC-{int(raw_id):03d}"
        else:
            candidate = f"UNC-CUSTOM-{uuid4().hex[:8].upper()}"

        while candidate in used_uncertainty_ids:
            candidate = f"UNC-CUSTOM-{uuid4().hex[:8].upper()}"

        item["uncertainty_id"] = candidate
        used_uncertainty_ids.add(candidate)

    decisions = st.session_state.get("key_decisions", [])
    used_decision_ids = set()

    for index, item in enumerate(decisions, start=1):
        if not isinstance(item, dict):
            continue
        existing = str(item.get("decision_id") or "").strip()
        if existing:
            used_decision_ids.add(existing)
            continue

        candidate = f"DEC-{index:03d}"
        while candidate in used_decision_ids:
            candidate = f"DEC-{uuid4().hex[:8].upper()}"
        item["decision_id"] = candidate
        used_decision_ids.add(candidate)


def get_selected_uncertainties():
    """Return only the uncertainties the user has ticked in Tab 1."""
    return [
        u
        for u in st.session_state["uncertainties"]
        if u.get("selected")
    ]


def get_active_decisions():
    """Return key decisions with a usable weight."""
    return [
        d
        for d in st.session_state["key_decisions"]
        if safe_int(d.get("Weight (1-3)", 0), default=0) > 0
        and str(d.get("Key Decision", "")).strip()
    ]

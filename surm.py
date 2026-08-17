"""
SURM Toolkit
Subsurface Uncertainty & Risk Management Plan Toolkit

Application shell / navigation layer.

Run:
    streamlit run surm.py

Notes:
- Existing SURM workflow modules are intentionally preserved.
- This file manages application layout, navigation, study health,
  persistence state, export, and shared UI.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from html import escape
from typing import Any

import streamlit as st


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="SURM Toolkit | PETRONAS Carigali",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# APPLICATION CONSTANTS
# ============================================================================

APP_NAME = "SURM Toolkit"
APP_VERSION = "2.0"

PRIMARY = "#006C35"
PRIMARY_DARK = "#004F27"
ACCENT = "#00A88F"

STATUS_SUCCESS = "#16803C"
STATUS_WARNING = "#B7791F"
STATUS_DANGER = "#C53030"
STATUS_INFO = "#2563EB"

MODULES = {
    "overview": {
        "label": "Overview",
        "icon": "⌂",
        "group": "Study",
    },
    "frontpage": {
        "label": "Project Setup",
        "icon": "01",
        "group": "Study",
    },
    "documentation": {
        "label": "Documentation",
        "icon": "02",
        "group": "Study",
    },
    "how_to_use": {
        "label": "How to Use",
        "icon": "03",
        "group": "Study",
    },
    "uncertainties": {
        "label": "Identify Uncertainties",
        "icon": "04",
        "group": "Workflow",
    },
    "key_decisions": {
        "label": "Key Decisions",
        "icon": "05",
        "group": "Workflow",
    },
    "impact": {
        "label": "Impact Assessment",
        "icon": "06",
        "group": "Workflow",
    },
    "key_uncertainties": {
        "label": "Prioritise Key Uncertainties",
        "icon": "07",
        "group": "Workflow",
    },
    "resolution_list": {
        "label": "Resolution List",
        "icon": "08",
        "group": "Workflow",
    },
    "resolution_planner": {
        "label": "Resolution Planner",
        "icon": "09",
        "group": "Workflow",
    },
    "risk_register": {
        "label": "Risk Register",
        "icon": "10",
        "group": "Workflow",
    },
    "pra": {
        "label": "PRA Output",
        "icon": "→",
        "group": "Output",
    },
}


# ============================================================================
# CSS LOADER
# ============================================================================

def load_css() -> None:
    """Load the application stylesheet from assets/style.css."""

    css_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "assets",
        "style.css",
    )

    if not os.path.exists(css_path):
        st.warning(
            "The SURM stylesheet could not be found at "
            f"`{css_path}`. The application will continue using Streamlit defaults."
        )
        return

    try:
        with open(css_path, "r", encoding="utf-8") as css_file:
            st.markdown(
                f"<style>{css_file.read()}</style>",
                unsafe_allow_html=True,
            )
    except OSError as exc:
        st.warning(f"Unable to load SURM stylesheet: {exc}")


load_css()


# ============================================================================
# EXISTING APPLICATION SERVICES
# ============================================================================

from utils.session import init_session
from utils.persistence import (
    delete_session,
    list_sessions,
    load_session_record,
    resume_latest_session,
    save_session,
)
from utils.export_excel import build_excel_export


# ============================================================================
# EXISTING SURM MODULES
# ============================================================================

from modules.tab_frontpage import render as render_frontpage
from modules.tab_documentation import render as render_documentation
from modules.tab_how_to_use import render as render_how_to_use
from modules.tab1_uncertainties import render as render_uncertainties
from modules.tab2_key_decisions import render as render_key_decisions
from modules.tab3_impact_assessment import render as render_impact
from modules.tab4_key_uncertainties import render as render_key_uncertainties
from modules.tab5_resolution_list import render as render_resolution_list
from modules.tab6_resolution_planner import render as render_resolution_planner
from modules.tab7_risk_register import render as render_risk_register
from modules.tab_pra_output import render as render_pra


# ============================================================================
# SESSION INITIALISATION
# ============================================================================

init_session()
resume_latest_session()


# ============================================================================
# SESSION HELPERS
# ============================================================================

INTERNAL_STATE_KEYS = {
    "_last_saved",
    "_last_save_auto",
    "_auto_save_enabled",
    "_state_hash_at_save",
    "_navigation",
    "_session_initialized",
    "_resume_attempted",
    "_save_error",
    "_delete_confirmation",
    "_selected_saved_session",
}


def _serialise_for_hash(value: Any) -> Any:
    """
    Convert common session-state values into deterministic serialisable data.

    This is intentionally defensive because Streamlit session state may contain
    objects that cannot be JSON serialised directly.
    """

    if isinstance(value, dict):
        return {
            str(key): _serialise_for_hash(val)
            for key, val in sorted(value.items(), key=lambda item: str(item[0]))
            if str(key) not in INTERNAL_STATE_KEYS
        }

    if isinstance(value, (list, tuple)):
        return [_serialise_for_hash(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    try:
        return str(value)
    except Exception:
        return repr(value)


def compute_state_hash() -> str:
    """Return a deterministic hash representing the current study state."""

    payload = _serialise_for_hash(dict(st.session_state))

    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def current_save_status() -> str:
    """
    Determine whether the current study is:
    - NEW
    - SAVED
    - UNSAVED
    """

    ss = st.session_state

    project_name = str(ss.get("project_name", "") or "").strip()

    if not project_name:
        return "NEW"

    current_hash = compute_state_hash()
    saved_hash = ss.get("_state_hash_at_save")

    if not saved_hash:
        return "UNSAVED"

    if current_hash == saved_hash:
        return "SAVED"

    return "UNSAVED"


def mark_state_saved() -> None:
    """Record the current application state as the last saved state."""

    st.session_state["_state_hash_at_save"] = compute_state_hash()


def format_save_time(value: str | None) -> str:
    """Convert ISO timestamp to a compact display format."""

    if not value:
        return "Never"

    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%d %b %Y, %H:%M")
    except Exception:
        return value


# ============================================================================
# STUDY STATISTICS
# ============================================================================

def get_study_statistics() -> dict[str, int]:
    """Calculate high-level study statistics from existing session state."""

    ss = st.session_state

    uncertainties = ss.get("uncertainties", []) or []
    decisions = ss.get("key_decisions", []) or []
    key_uncertainties = ss.get("key_uncertainties", []) or []
    resolution_actions = ss.get("resolution_planner", []) or []
    risks = ss.get("risk_register", []) or []
    team_members = ss.get("team_members", []) or []

    selected_uncertainties = sum(
        1
        for item in uncertainties
        if isinstance(item, dict) and item.get("selected")
    )

    valid_decisions = sum(
        1
        for item in decisions
        if isinstance(item, dict)
        and str(item.get("Key Decision", "")).strip()
    )

    valid_key_uncertainties = sum(
        1
        for item in key_uncertainties
        if isinstance(item, dict)
        and item.get("Include in Plan")
    )

    valid_team_members = sum(
        1
        for item in team_members
        if isinstance(item, dict)
        and str(item.get("Name", "")).strip()
    )

    return {
        "uncertainties_total": len(uncertainties),
        "uncertainties_selected": selected_uncertainties,
        "decisions": valid_decisions,
        "key_uncertainties": valid_key_uncertainties,
        "resolution_actions": len(resolution_actions),
        "risks": len(risks),
        "team_members": valid_team_members,
    }


# ============================================================================
# WORKFLOW COMPLETION
# ============================================================================

def _stage_completion(
    name: str,
    completed: bool,
    weight: float,
    detail: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "completed": completed,
        "weight": weight,
        "detail": detail,
    }


def get_workflow_progress() -> dict[str, Any]:
    """
    Calculate weighted workflow completion.

    This deliberately replaces the previous binary 8-checkbox calculation.
    A stage now represents a meaningful part of the SURM process.
    """

    ss = st.session_state
    stats = get_study_statistics()

    project_complete = bool(
        str(ss.get("project_name", "") or "").strip()
        and str(ss.get("field_name", "") or "").strip()
    )

    uncertainty_complete = (
        stats["uncertainties_total"] > 0
        and stats["uncertainties_selected"] > 0
    )

    decision_complete = stats["decisions"] > 0

    impact_complete = bool(ss.get("impact_assessment"))

    key_uncertainty_complete = stats["key_uncertainties"] > 0

    resolution_list_complete = bool(ss.get("resolution_list"))

    planner_complete = stats["resolution_actions"] > 0

    risk_complete = stats["risks"] > 0

    stages = [
        _stage_completion(
            "Project Setup",
            project_complete,
            0.10,
            "Field and project information",
        ),
        _stage_completion(
            "Uncertainty Identification",
            uncertainty_complete,
            0.15,
            f"{stats['uncertainties_selected']} selected uncertainties",
        ),
        _stage_completion(
            "Key Decisions",
            decision_complete,
            0.15,
            f"{stats['decisions']} key decisions",
        ),
        _stage_completion(
            "Impact Assessment",
            impact_complete,
            0.15,
            "Decision impact assessment",
        ),
        _stage_completion(
            "Key Uncertainties",
            key_uncertainty_complete,
            0.15,
            f"{stats['key_uncertainties']} prioritised uncertainties",
        ),
        _stage_completion(
            "Resolution Strategy",
            resolution_list_complete,
            0.10,
            "Resolution list established",
        ),
        _stage_completion(
            "Resolution Planning",
            planner_complete,
            0.10,
            f"{stats['resolution_actions']} planned actions",
        ),
        _stage_completion(
            "Risk Register",
            risk_complete,
            0.10,
            f"{stats['risks']} risks",
        ),
    ]

    percentage = round(
        sum(stage["weight"] for stage in stages if stage["completed"]) * 100
    )

    return {
        "percentage": percentage,
        "stages": stages,
    }


# ============================================================================
# STUDY HEALTH
# ============================================================================

def get_study_health() -> dict[str, Any]:
    """
    Produce a simple health assessment.

    This is intentionally conservative. It does not claim engineering risk
    severity that is not available in the existing data model.
    """

    stats = get_study_statistics()
    progress = get_workflow_progress()

    attention: list[dict[str, str]] = []

    if not st.session_state.get("project_name"):
        attention.append(
            {
                "type": "warning",
                "message": "Project name has not been defined.",
                "target": "frontpage",
            }
        )

    if stats["uncertainties_total"] == 0:
        attention.append(
            {
                "type": "warning",
                "message": "No uncertainties have been entered.",
                "target": "uncertainties",
            }
        )
    elif stats["uncertainties_selected"] == 0:
        attention.append(
            {
                "type": "warning",
                "message": "No uncertainties have been selected for further assessment.",
                "target": "uncertainties",
            }
        )

    if stats["decisions"] == 0:
        attention.append(
            {
                "type": "warning",
                "message": "No key decisions have been defined.",
                "target": "key_decisions",
            }
        )

    if not st.session_state.get("impact_assessment"):
        attention.append(
            {
                "type": "warning",
                "message": "Impact assessment has not been completed.",
                "target": "impact",
            }
        )

    if stats["key_uncertainties"] == 0:
        attention.append(
            {
                "type": "warning",
                "message": "No key uncertainties have been prioritised.",
                "target": "key_uncertainties",
            }
        )

    if stats["resolution_actions"] == 0:
        attention.append(
            {
                "type": "warning",
                "message": "No resolution actions have been planned.",
                "target": "resolution_planner",
            }
        )

    if stats["risks"] == 0:
        attention.append(
            {
                "type": "info",
                "message": "Risk register does not contain any entries yet.",
                "target": "risk_register",
            }
        )

    if progress["percentage"] >= 80:
        health = "GOOD"
    elif progress["percentage"] >= 50:
        health = "IN PROGRESS"
    else:
        health = "NEEDS ATTENTION"

    return {
        "status": health,
        "attention": attention,
    }


# ============================================================================
# NAVIGATION
# ============================================================================

def navigate_to(page: str) -> None:
    """Set the active navigation page."""

    st.session_state["_navigation"] = page


def get_current_page() -> str:
    """Return the active page."""

    return st.session_state.get("_navigation", "overview")


def render_navigation_button(
    page: str,
    *,
    compact: bool = False,
) -> None:
    """Render a sidebar navigation button."""

    metadata = MODULES[page]
    current = get_current_page()

    active = current == page

    label = (
        f"{metadata['icon']}   {metadata['label']}"
        if not compact
        else metadata["label"]
    )

    button_type = "primary" if active else "secondary"

    if st.sidebar.button(
        label,
        key=f"nav_{page}",
        use_container_width=True,
        type=button_type,
    ):
        navigate_to(page)
        st.rerun()


# ============================================================================
# SIDEBAR
# ============================================================================

def _sidebar():
    ss = st.session_state

    # ================================================================
    # LOGO
    # ================================================================

    st.sidebar.markdown("""
        <div style="text-align:center;padding:16px 0 10px 0;">
            <div style="font-size:36px;line-height:1;">🛢️</div>
            <div style="
                font-size:15px;
                font-weight:700;
                letter-spacing:0.5px;
                margin-top:6px;
            ">
                SURM Toolkit
            </div>
            <div style="
                font-size:10px;
                opacity:0.7;
                margin-top:2px;
                letter-spacing:1px;
            ">
                PETRONAS CARIGALI
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.divider()

    # ================================================================
    # PROJECT INFORMATION
    # ================================================================

    field = ss.get("field_name") or "—"
    project = ss.get("project_name") or "—"
    phase = ss.get("project_phase") or "—"

    st.sidebar.markdown(
        f"""
        <div style="padding:4px 0;">

            <div style="
                font-size:10px;
                opacity:0.65;
                text-transform:uppercase;
                letter-spacing:0.8px;
            ">
                Field
            </div>

            <div style="
                font-size:14px;
                font-weight:700;
                margin-bottom:8px;
            ">
                {field}
            </div>

            <div style="
                font-size:10px;
                opacity:0.65;
                text-transform:uppercase;
                letter-spacing:0.8px;
            ">
                Project
            </div>

            <div style="
                font-size:13px;
                margin-bottom:8px;
            ">
                {project}
            </div>

            <div style="
                font-size:10px;
                opacity:0.65;
                text-transform:uppercase;
                letter-spacing:0.8px;
            ">
                Phase
            </div>

            <div style="font-size:13px;">
                <span style="
                    background:rgba(255,255,255,0.2);
                    padding:2px 10px;
                    border-radius:10px;
                    font-weight:700;
                ">
                    {phase}
                </span>
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.divider()

    # ================================================================
    # SESSION CONTROLS
    # ================================================================

    st.sidebar.markdown(
        """
        <div style="
            font-size:10px;
            opacity:0.65;
            text-transform:uppercase;
            letter-spacing:0.8px;
            margin-bottom:8px;
        ">
            Session
        </div>
        """,
        unsafe_allow_html=True,
    )

    from utils.persistence import save_session

    if st.sidebar.button(
        "💾 Save Session",
        key="_save_session"
    ):
        if not ss.get("project_name", "").strip():
            st.sidebar.warning(
                "Set a Project Name on the Front Page first."
            )
        else:
            ok = save_session(auto=False)

            if ok:
                st.sidebar.success("✅ Saved!")
            else:
                st.sidebar.error(
                    "Save failed — check permissions."
                )

    # IMPORTANT:
    # Streamlit owns this widget state.
    # Do not manually assign _auto_save_enabled afterwards.
    st.sidebar.checkbox(
        "Enable auto-save",
        key="_auto_save_enabled",
        help=(
            "Automatically save the current SURM session "
            "when enabled."
        ),
    )

    # ================================================================
    # LAST SAVE STATUS
    # ================================================================

    last_saved = ss.get("_last_saved", "")
    last_auto = ss.get("_last_save_auto", False)

    if last_saved:
        ts = last_saved.replace("T", " ")

        label = (
            f"{'Auto-saved' if last_auto else 'Saved'}: "
            f"{ts[11:19]}"
        )

        st.sidebar.markdown(
            f"""
            <div style="
                font-size:10px;
                opacity:0.7;
                text-align:center;
                margin-top:4px;
            ">
                ✅ {label}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            """
            <div style="
                font-size:10px;
                opacity:0.55;
                text-align:center;
                margin-top:4px;
            ">
                ⚠️ Not saved yet
            </div>
            """,
            unsafe_allow_html=True,
        )

# ============================================================================
# MAIN HEADER
# ============================================================================

def render_header() -> None:
    """Render the compact application header."""

    ss = st.session_state

    field = escape(str(ss.get("field_name", "") or "Field pending"))
    project = escape(str(ss.get("project_name", "") or "Project pending"))
    phase = escape(str(ss.get("project_phase", "") or "Phase pending"))

    status = current_save_status()

    status_map = {
        "NEW": ("Draft", "status-neutral"),
        "SAVED": ("Saved", "status-success"),
        "UNSAVED": ("Unsaved changes", "status-warning"),
    }

    status_text, status_class = status_map[status]

    st.markdown(
        f"""
        <div class="surm-header">
            <div class="surm-header-main">
                <div class="surm-header-kicker">
                    SUBSURFACE UNCERTAINTY &amp; RISK MANAGEMENT
                </div>

                <h1>SURM Toolkit</h1>

                <p>
                    {field}
                    <span class="header-separator">•</span>
                    {project}
                </p>
            </div>

            <div class="surm-header-meta">
                <span class="surm-badge">{phase}</span>

                <span class="surm-save-state {status_class}">
                    <span class="status-dot"></span>
                    {status_text}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# KPI CARDS
# ============================================================================

def render_kpi_cards() -> None:
    """Render study KPI cards."""

    stats = get_study_statistics()

    columns = st.columns(4)

    cards = [
        (
            "Uncertainties",
            stats["uncertainties_selected"],
            f"{stats['uncertainties_total']} identified",
            "uncertainties",
        ),
        (
            "Key Decisions",
            stats["decisions"],
            "Decisions defined",
            "key_decisions",
        ),
        (
            "Resolution Actions",
            stats["resolution_actions"],
            "Actions planned",
            "resolution_planner",
        ),
        (
            "Risks",
            stats["risks"],
            "Risks registered",
            "risk_register",
        ),
    ]

    for column, (label, value, detail, target) in zip(columns, cards):
        with column:
            st.markdown(
                f"""
                <div class="surm-kpi-card">
                    <div class="surm-kpi-label">{escape(label)}</div>
                    <div class="surm-kpi-value">{value}</div>
                    <div class="surm-kpi-detail">{escape(detail)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                f"Open {label}",
                key=f"kpi_{target}",
                use_container_width=True,
            ):
                navigate_to(target)
                st.rerun()


# ============================================================================
# WORKFLOW PROGRESS
# ============================================================================

def render_workflow_progress() -> None:
    """Render the weighted workflow progress."""

    progress = get_workflow_progress()

    st.markdown(
        """
        <div class="surm-section-heading">
            <div>
                <div class="surm-eyebrow">Workflow</div>
                <h2>Study Progress</h2>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="surm-progress-summary">
            <div>
                <span class="surm-progress-number">
                    {progress['percentage']}%
                </span>
                <span class="surm-progress-label">
                    overall completion
                </span>
            </div>

            <div class="surm-large-progress-track">
                <div
                    class="surm-large-progress-value"
                    style="width:{progress['percentage']}%;"
                ></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for index, stage in enumerate(progress["stages"], start=1):
        completed = stage["completed"]

        icon = "✓" if completed else str(index).zfill(2)
        state_class = "complete" if completed else "pending"

        st.markdown(
            f"""
            <div class="surm-workflow-row {state_class}">
                <div class="surm-workflow-number">
                    {icon}
                </div>

                <div class="surm-workflow-content">
                    <strong>{escape(stage['name'])}</strong>
                    <span>{escape(stage['detail'])}</span>
                </div>

                <div class="surm-workflow-state">
                    {"Complete" if completed else "Pending"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================================
# ACTION REQUIRED
# ============================================================================

def render_action_required() -> None:
    """Render study attention items."""

    health = get_study_health()

    st.markdown(
        """
        <div class="surm-section-heading">
            <div>
                <div class="surm-eyebrow">Study Health</div>
                <h2>Action Required</h2>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not health["attention"]:
        st.success(
            "No immediate workflow gaps detected. "
            "The study is progressing normally."
        )
        return

    for index, item in enumerate(health["attention"]):
        item_type = item["type"]

        if item_type == "warning":
            icon = "⚠"
        elif item_type == "info":
            icon = "i"
        else:
            icon = "!"

        cols = st.columns([0.06, 0.78, 0.16])

        with cols[0]:
            st.markdown(
                f'<div class="surm-alert-icon {item_type}">{icon}</div>',
                unsafe_allow_html=True,
            )

        with cols[1]:
            st.markdown(
                f'<div class="surm-alert-text">{escape(item["message"])}</div>',
                unsafe_allow_html=True,
            )

        with cols[2]:
            if st.button(
                "Review",
                key=f"action_review_{index}",
                use_container_width=True,
            ):
                navigate_to(item["target"])
                st.rerun()


# ============================================================================
# STUDY DETAILS
# ============================================================================

def render_study_details() -> None:
    """Render current study metadata."""

    ss = st.session_state

    project = ss.get("project_name", "") or "Not defined"
    field = ss.get("field_name", "") or "Not defined"
    phase = ss.get("project_phase", "") or "Not defined"

    last_saved = ss.get("_last_saved")
    save_text = format_save_time(last_saved)

    st.markdown(
        """
        <div class="surm-section-heading">
            <div>
                <div class="surm-eyebrow">Study</div>
                <h2>Study Details</h2>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)

    values = [
        ("Field", field),
        ("Project", project),
        ("Project Phase", phase),
        ("Last Saved", save_text),
    ]

    for column, (label, value) in zip(cols, values):
        with column:
            st.markdown(
                f"""
                <div class="surm-detail-card">
                    <span>{escape(label)}</span>
                    <strong>{escape(str(value))}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

# Quick save button and autosave indicator
col_quick, col_hint = st.columns([1, 5])
with col_quick:
    if st.button("💾 Save Progress (Quick)"):
        if not ss.get("project_name","").strip():
            st.warning("Enter a Project Name before saving.")
        else:
            ok = save_session(auto=False)
            st.success("Saved.") if ok else st.error("Save failed.")
with col_hint:
    last_saved = ss.get("_last_saved","")
    last_auto = ss.get("_last_save_auto", False)
    auto_on = ss.get("_auto_save_enabled", True)
    if last_saved:
        ts = last_saved.replace("T"," ")
        st.markdown(f"<div style='font-size:12px;opacity:0.8;'>Last saved: {ts[11:19]} {'(auto)' if last_auto else ''}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:12px;margin-top:2px;'>Auto-save: <b>{'ON' if auto_on else 'OFF'}</b></div>", unsafe_allow_html=True)

# Top-level quick theme controls (visible at the top of the page)
with st.expander('Appearance — Quick Theme Controls', expanded=False):
    c1, c2, c3 = st.columns([1,1,1])
    primary_top = c1.color_picker('Primary', value=st.session_state.get('ui_primary_color','#1F6B3A'))
    bg_top = c2.color_picker('Background', value=st.session_state.get('ui_background_color','#F8FBFC'))
    if c3.button('Apply Theme (Top)'):
        st.session_state['ui_primary_color'] = primary_top
        st.session_state['ui_background_color'] = bg_top
        _apply_dynamic_theme()
        st.success('Theme applied')


# ============================================================================
# OVERVIEW
# ============================================================================

def render_overview() -> None:
    """Render the new SURM study dashboard."""

    progress = get_workflow_progress()
    health = get_study_health()

    st.markdown(
        f"""
        <div class="surm-welcome">
            <div>
                <div class="surm-eyebrow">Study Overview</div>

                <h2>
                    {escape(
                        str(
                            st.session_state.get(
                                "project_name",
                                "",
                            )
                            or "Start your SURM study"
                        )
                    )}
                </h2>

                <p>
                    Track uncertainty, decisions, impact, resolution and risk
                    through a single structured workflow.
                </p>
            </div>

            <div class="surm-health-card">
                <span>Study Health</span>
                <strong>{escape(health['status'])}</strong>
                <small>{progress['percentage']}% complete</small>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_kpi_cards()

    st.markdown("<div class='surm-section-gap'></div>", unsafe_allow_html=True)

    left, right = st.columns([1.35, 1])

    with left:
        render_workflow_progress()

    with right:
        render_action_required()

    st.markdown("<div class='surm-section-gap'></div>", unsafe_allow_html=True)

    render_study_details()

    st.markdown("<div class='surm-section-gap'></div>", unsafe_allow_html=True)

    # ------------------------------------------------------------------------
    # Continue Study
    # ------------------------------------------------------------------------

    st.markdown(
        """
        <div class="surm-section-heading">
            <div>
                <div class="surm-eyebrow">Next Step</div>
                <h2>Continue Your Study</h2>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if progress["percentage"] < 100:
        next_stage = next(
            (
                stage
                for stage in progress["stages"]
                if not stage["completed"]
            ),
            None,
        )

        if next_stage:
            st.info(
                f"Recommended next step: **{next_stage['name']}** — "
                f"{next_stage['detail']}."
            )

            next_page_map = {
                "Project Setup": "frontpage",
                "Uncertainty Identification": "uncertainties",
                "Key Decisions": "key_decisions",
                "Impact Assessment": "impact",
                "Key Uncertainties": "key_uncertainties",
                "Resolution Strategy": "resolution_list",
                "Resolution Planning": "resolution_planner",
                "Risk Register": "risk_register",
            }

            target = next_page_map.get(next_stage["name"])

            if target and st.button(
                f"Continue to {next_stage['name']}",
                type="primary",
                use_container_width=False,
            ):
                navigate_to(target)
                st.rerun()
    else:
        st.success(
            "The core SURM workflow is complete. "
            "Review the PRA Output before finalising the study."
        )


# ============================================================================
# MODULE ROUTER
# ============================================================================

def render_current_page() -> None:
    """Render only the currently selected workflow page."""

    page = get_current_page()

    renderers = {
        "overview": render_overview,
        "frontpage": render_frontpage,
        "documentation": render_documentation,
        "how_to_use": render_how_to_use,
        "uncertainties": render_uncertainties,
        "key_decisions": render_key_decisions,
        "impact": render_impact,
        "key_uncertainties": render_key_uncertainties,
        "resolution_list": render_resolution_list,
        "resolution_planner": render_resolution_planner,
        "risk_register": render_risk_register,
        "pra": render_pra,
    }

    renderer = renderers.get(page)

    if renderer is None:
        st.error(
            f"Unknown SURM page: `{page}`. "
            "Returning to Overview."
        )
        st.session_state["_navigation"] = "overview"
        st.rerun()

    renderer()


# ============================================================================
# SAVE STATUS BAR
# ============================================================================

def render_status_bar() -> None:
    """Render a non-intrusive application status bar."""

    status = current_save_status()

    status_map = {
        "NEW": "Draft study",
        "SAVED": "All changes saved",
        "UNSAVED": "Unsaved changes",
    }

    status_text = status_map[status]

    last_saved = format_save_time(
        st.session_state.get("_last_saved")
    )

    st.markdown(
        f"""
        <div class="surm-status-bar">
            <div>
                <strong>SURM Toolkit</strong>
                <span>v{APP_VERSION}</span>
            </div>

            <div>
                <span>{escape(status_text)}</span>
                <span class="status-divider">•</span>
                <span>Last saved: {escape(last_saved)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# APPLICATION
# ============================================================================

def main() -> None:
    """Application entry point."""

    _sidebar()
    render_header()

    # Main content
    render_current_page()

    # Footer/status
    render_status_bar()


if __name__ == "__main__":
    main()
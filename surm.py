"""
SURM Toolkit
Subsurface Uncertainty & Risk Management Plan Toolkit

Application entry point.

Run:
    streamlit run surm.py
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================

APP_NAME = "SURM Toolkit"
APP_VERSION = "1.0.0"
APP_SUBTITLE = "Subsurface Uncertainty & Risk Management"

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title=f"{APP_NAME} | PETRONAS Carigali",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# IMPORT APPLICATION SERVICES
# ============================================================================

from utils.session import init_session
from utils.persistence import resume_latest_session


# ============================================================================
# IMPORT PAGE MODULES
# ============================================================================

from modules.tab_frontpage import render as render_frontpage
from modules.tab_documentation import render as render_documentation
from modules.tab_how_to_use import render as render_how_to_use
from modules.tab1_uncertainties import render as render_uncertainties
from modules.tab2_key_decisions import render as render_key_decisions
from modules.tab3_impact_assessment import render as render_impact_assessment
from modules.tab4_key_uncertainties import render as render_key_uncertainties
from modules.tab5_resolution_list import render as render_resolution_list
from modules.tab6_resolution_planner import render as render_resolution_planner
from modules.tab7_risk_register import render as render_risk_register
from modules.tab_pra_output import render as render_pra_output


# ============================================================================
# CSS
# ============================================================================

def load_css() -> None:
    """
    Load the application's external stylesheet.

    CSS must live in assets/style.css.
    No raw CSS should be embedded in this Python file.
    """

    css_path = ASSETS_DIR / "style.css"

    if not css_path.exists():
        st.warning(
            f"Stylesheet not found: {css_path}"
        )
        return

    try:
        css = css_path.read_text(encoding="utf-8")

        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True,
        )

    except OSError as exc:
        st.error(
            f"Unable to load application stylesheet: {exc}"
        )


# ============================================================================
# THEME
# ============================================================================

def apply_theme() -> None:
    """
    Apply theme variables from session state.

    Phase 1 intentionally keeps this simple.
    Full theme customisation will be addressed in Phase 2.
    """

    primary = st.session_state.get(
        "ui_primary_color",
        "#176B3A",
    )

    background = st.session_state.get(
        "ui_background_color",
        "#F5F7F6",
    )

    st.markdown(
        f"""
        <style>

        :root {{
            --surm-primary: {primary};
            --surm-background: {background};
        }}

        .stApp {{
            background: var(--surm-background);
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# APPLICATION HEADER
# ============================================================================

def render_header() -> None:
    """
    Render the persistent application header.
    """

    ss = st.session_state

    field = ss.get("field_name", "").strip()
    project = ss.get("project_name", "").strip()
    phase = ss.get("project_phase", "").strip()

    field_label = field if field else "Field not configured"
    project_label = project if project else "Project not configured"
    phase_label = phase if phase else "Phase not configured"

    saved = bool(ss.get("_last_saved"))

    status_label = "Saved" if saved else "Draft"
    status_class = "saved" if saved else "draft"

    st.markdown(
        f"""
        <div class="surm-header">

            <div class="surm-header-brand">

                <div class="surm-logo">
                    🛢️
                </div>

                <div>
                    <div class="surm-eyebrow">
                        PETRONAS CARIGALI
                    </div>

                    <div class="surm-title">
                        {APP_NAME}
                    </div>

                    <div class="surm-subtitle">
                        {APP_SUBTITLE}
                    </div>
                </div>

            </div>

            <div class="surm-header-meta">

                <div class="surm-meta-item">
                    <span class="surm-meta-label">
                        Field
                    </span>

                    <span class="surm-meta-value">
                        {field_label}
                    </span>
                </div>

                <div class="surm-meta-item">
                    <span class="surm-meta-label">
                        Project
                    </span>

                    <span class="surm-meta-value">
                        {project_label}
                    </span>
                </div>

                <div class="surm-meta-item">
                    <span class="surm-meta-label">
                        Phase
                    </span>

                    <span class="surm-meta-value">
                        {phase_label}
                    </span>
                </div>

                <span class="surm-status {status_class}">
                    {status_label}
                </span>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# STUDY STATISTICS
# ============================================================================

def calculate_study_progress() -> dict:
    """
    Calculate basic study statistics.

    This function only reads session state.
    It does not mutate anything.
    """

    ss = st.session_state

    uncertainties = ss.get("uncertainties", [])
    key_decisions = ss.get("key_decisions", [])
    key_uncertainties = ss.get("key_uncertainties", [])
    resolution_planner = ss.get("resolution_planner", [])
    risk_register = ss.get("risk_register", [])
    team_members = ss.get("team_members", [])

    selected_uncertainties = sum(
        1
        for item in uncertainties
        if isinstance(item, dict)
        and item.get("selected")
    )

    total_uncertainties = len(uncertainties)

    decisions = sum(
        1
        for item in key_decisions
        if isinstance(item, dict)
        and str(item.get("Key Decision", "")).strip()
    )

    included_key_uncertainties = sum(
        1
        for item in key_uncertainties
        if isinstance(item, dict)
        and item.get("Include in Plan")
    )

    actions = len(resolution_planner)

    risks = len(risk_register)

    team = sum(
        1
        for item in team_members
        if isinstance(item, dict)
        and str(item.get("Name", "")).strip()
    )

    checks = [
        bool(ss.get("project_name", "").strip()),
        selected_uncertainties > 0,
        decisions > 0,
        bool(ss.get("impact_assessment")),
        included_key_uncertainties > 0,
        bool(ss.get("resolution_list")),
        actions > 0,
        risks > 0,
    ]

    progress = round(
        (sum(checks) / len(checks)) * 100
    )

    return {
        "selected_uncertainties": selected_uncertainties,
        "total_uncertainties": total_uncertainties,
        "key_decisions": decisions,
        "key_uncertainties": included_key_uncertainties,
        "resolution_actions": actions,
        "risks": risks,
        "team_members": team,
        "progress": progress,
    }


# ============================================================================
# SIDEBAR
# ============================================================================

def render_sidebar() -> None:
    """
    Render the application's persistent sidebar.

    The sidebar owns:
        - project context
        - progress
        - session controls
        - export
    """

    from utils.persistence import (
        save_session,
        list_sessions,
        load_session_record,
        delete_session,
    )

    from utils.export_excel import build_excel_export

    ss = st.session_state
    stats = calculate_study_progress()

    with st.sidebar:

        # --------------------------------------------------------------------
        # BRAND
        # --------------------------------------------------------------------

        st.markdown(
            """
            <div class="sidebar-brand">

                <div class="sidebar-brand-icon">
                    🛢️
                </div>

                <div>
                    <div class="sidebar-brand-title">
                        SURM Toolkit
                    </div>

                    <div class="sidebar-brand-subtitle">
                        PETRONAS CARIGALI
                    </div>
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # --------------------------------------------------------------------
        # PROJECT CONTEXT
        # --------------------------------------------------------------------

        st.markdown(
            '<div class="sidebar-section-title">Current Study</div>',
            unsafe_allow_html=True,
        )

        field = ss.get("field_name", "").strip()
        project = ss.get("project_name", "").strip()
        phase = ss.get("project_phase", "").strip()

        st.markdown(
            f"""
            <div class="sidebar-study">

                <div class="sidebar-study-row">
                    <span>Field</span>
                    <strong>{field or "Not configured"}</strong>
                </div>

                <div class="sidebar-study-row">
                    <span>Project</span>
                    <strong>{project or "Not configured"}</strong>
                </div>

                <div class="sidebar-study-row">
                    <span>Phase</span>
                    <strong>{phase or "Not configured"}</strong>
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # --------------------------------------------------------------------
        # PROGRESS
        # --------------------------------------------------------------------

        st.markdown(
            '<div class="sidebar-section-title">Study Progress</div>',
            unsafe_allow_html=True,
        )

        progress = stats["progress"]

        st.progress(
            progress / 100,
            text=f"{progress}% complete",
        )

        st.caption(
            "Progress is based on completion of the core study stages."
        )

        # --------------------------------------------------------------------
        # STATISTICS
        # --------------------------------------------------------------------

        stat_items = [
            (
                "Uncertainties",
                f'{stats["selected_uncertainties"]} / '
                f'{stats["total_uncertainties"]}',
            ),
            (
                "Key Decisions",
                stats["key_decisions"],
            ),
            (
                "Key Uncertainties",
                stats["key_uncertainties"],
            ),
            (
                "Resolution Actions",
                stats["resolution_actions"],
            ),
            (
                "Risks",
                stats["risks"],
            ),
            (
                "Team Members",
                stats["team_members"],
            ),
        ]

        for label, value in stat_items:
            col_label, col_value = st.columns([3, 1])

            with col_label:
                st.caption(label)

            with col_value:
                st.markdown(
                    f"<div class='sidebar-stat-value'>{value}</div>",
                    unsafe_allow_html=True,
                )

        st.divider()

        # --------------------------------------------------------------------
        # SESSION
        # --------------------------------------------------------------------

        st.markdown(
            '<div class="sidebar-section-title">Session</div>',
            unsafe_allow_html=True,
        )

        if st.button(
            "💾 Save Session",
            key="sidebar_save_session",
            use_container_width=True,
            type="primary",
        ):

            if not project:
                st.warning(
                    "Set a Project Name before saving."
                )

            else:
                success = save_session(auto=False)

                if success:
                    st.success("Session saved.")
                else:
                    st.error(
                        "Unable to save the session."
                    )

        # IMPORTANT:
        # Streamlit owns this widget's state.
        # We never assign st.session_state["_auto_save_enabled"]
        # after creating the widget.

        st.checkbox(
            "Enable auto-save",
            key="_auto_save_enabled",
            help="Automatically save the current study when supported.",
        )

        last_saved = ss.get("_last_saved", "")

        if last_saved:
            st.caption(
                f"Last saved: {last_saved.replace('T', ' ')[:19]}"
            )
        else:
            st.caption("No save recorded yet.")

        st.divider()

        # --------------------------------------------------------------------
        # SAVED SESSIONS
        # --------------------------------------------------------------------

        st.markdown(
            '<div class="sidebar-section-title">Saved Sessions</div>',
            unsafe_allow_html=True,
        )

        sessions = list_sessions()

        if sessions:

            labels = [
                (
                    f'{session.get("project_name", "Unnamed")} — '
                    f'{session.get("field_name", "Unknown")}'
                )
                for session in sessions
            ]

            selected_label = st.selectbox(
                "Saved studies",
                labels,
                key="saved_session_selector",
            )

            selected_index = labels.index(selected_label)
            selected_session = sessions[selected_index]

            col_load, col_delete = st.columns(2)

            with col_load:

                if st.button(
                    "Load",
                    key="load_saved_session",
                    use_container_width=True,
                ):

                    success = load_session_record(
                        selected_session
                    )

                    if success:
                        st.success("Session loaded.")
                        st.rerun()
                    else:
                        st.error("Unable to load session.")

            with col_delete:

                if st.button(
                    "Delete",
                    key="delete_saved_session",
                    use_container_width=True,
                ):

                    success = delete_session(
                        selected_session.get(
                            "project_name",
                            "",
                        ),
                        selected_session.get(
                            "field_name",
                            "",
                        ),
                    )

                    if success:
                        st.success("Session deleted.")
                        st.rerun()
                    else:
                        st.error("Unable to delete session.")

        else:
            st.caption("No saved sessions found.")

        st.divider()

        # --------------------------------------------------------------------
        # EXPORT
        # --------------------------------------------------------------------

        st.markdown(
            '<div class="sidebar-section-title">Export</div>',
            unsafe_allow_html=True,
        )

        try:
            excel_data = build_excel_export()

            filename = (
                f"SURM_{field.replace(' ', '_')}.xlsx"
                if field
                else "SURM_Output.xlsx"
            )

            st.download_button(
                "📥 Download Excel",
                data=excel_data,
                file_name=filename,
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
            )

        except Exception as exc:
            st.warning(
                f"Excel export unavailable: {exc}"
            )

        st.divider()

        st.caption(
            f"{APP_NAME} v{APP_VERSION}"
        )


# ============================================================================
# PAGE ROUTER
# ============================================================================

PAGE_DEFINITIONS = {
    "📋 Overview": render_frontpage,
    "👥 Team": render_documentation,
    "📖 How to Use": render_how_to_use,
    "1️⃣ Uncertainties": render_uncertainties,
    "2️⃣ Key Decisions": render_key_decisions,
    "3️⃣ Impact Assessment": render_impact_assessment,
    "4️⃣ Key Uncertainties": render_key_uncertainties,
    "5️⃣ Resolution List": render_resolution_list,
    "6️⃣ Resolution Planner": render_resolution_planner,
    "7️⃣ Risk Register": render_risk_register,
    "📄 PRA Output": render_pra_output,
}


def render_navigation() -> None:
    """
    Render page navigation.

    Phase 1 keeps navigation simple and reliable.
    Phase 2 will redesign this into the full workflow UI.
    """

    page_names = list(PAGE_DEFINITIONS.keys())

    selected_page = st.sidebar.radio(
        "Study workflow",
        page_names,
        key="current_page",
    )

    renderer = PAGE_DEFINITIONS[selected_page]

    renderer()


# ============================================================================
# FOOTER
# ============================================================================

def render_footer() -> None:

    st.markdown(
        f"""
        <div class="surm-footer">

            <strong>🛢️ SURM Toolkit</strong>

            <span>
                PETRONAS Carigali
            </span>

            <span>
                Subsurface Uncertainty & Risk Management
            </span>

            <span>
                v{APP_VERSION}
            </span>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# APPLICATION
# ============================================================================

def main() -> None:
    """
    Main application lifecycle.

    The order is deliberate:

        1. Initialise session
        2. Restore persisted session
        3. Load CSS
        4. Apply theme
        5. Render sidebar
        6. Render header
        7. Render current page
        8. Render footer
    """

    # ------------------------------------------------------------------------
    # 1. Initialise session state
    # ------------------------------------------------------------------------

    init_session()

    # ------------------------------------------------------------------------
    # 2. Restore persisted session
    # ------------------------------------------------------------------------

    resume_latest_session()

    # ------------------------------------------------------------------------
    # 3. Load external CSS
    # ------------------------------------------------------------------------

    load_css()

    # ------------------------------------------------------------------------
    # 4. Apply theme
    # ------------------------------------------------------------------------

    apply_theme()

    # ------------------------------------------------------------------------
    # 5. Render sidebar
    # ------------------------------------------------------------------------

    render_sidebar()

    # ------------------------------------------------------------------------
    # 6. Render header
    # ------------------------------------------------------------------------

    render_header()

    # ------------------------------------------------------------------------
    # 7. Render page
    # ------------------------------------------------------------------------

    render_navigation()

    # ------------------------------------------------------------------------
    # 8. Render footer
    # ------------------------------------------------------------------------

    render_footer()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
"""
SURM Toolkit
Subsurface Uncertainty & Risk Management Plan Toolkit

Application entry point.

Run:
    streamlit run surm.py
"""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any, cast
import streamlit as st

from components.header import render_header as render_shared_header
from components.workflow import render_page_frame, render_workflow_list
from utils.analytics import build_study_analytics
from utils.assurance import study_is_editable
from utils.auth import auth_required, can_delete_study, can_edit_study, current_user_label, resolve_identity
from utils.styles import load_css
from utils.workflow import current_stage, stage_results, validate_stage


# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================

APP_NAME = "SURM Toolkit"
APP_VERSION = "1.2.0"
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

from utils.session import create_new_study, init_session


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
from modules.tab_study_repository import render as render_study_repository
from modules.tab_intelligence import render as render_intelligence
from modules.tab_barrier_management import render as render_barrier_management
from modules.tab_assurance import render as render_assurance
from modules.tab_revision_history import render as render_revision_history


# ============================================================================
# CSS
# ============================================================================

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

    render_shared_header(
        field=ss.get("field_name"),
        project=ss.get("project_name"),
        phase=ss.get("project_phase"),
        app_name=APP_NAME,
        subtitle=APP_SUBTITLE,
        saved=bool(ss.get("_last_saved")),
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

    stages = stage_results(ss)
    progress = round(
        (sum(stage.complete for stage in stages) / len(stages)) * 100
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


def _load_selected_session(session_meta: dict) -> None:
    """Streamlit callback for explicit saved-study loading."""
    from utils.persistence import load_session_record

    if not load_session_record(session_meta):
        st.session_state["_resume_message"] = "Unable to load the selected study."


def _delete_selected_session(project_name: str, field_name: str) -> None:
    """Streamlit callback for deleting a saved study."""
    from utils.persistence import delete_session

    allowed, reason = can_delete_study()
    if not allowed:
        st.error(reason)
        return

    if delete_session(project_name, field_name):
        if (
            st.session_state.get("project_name", "").strip() == project_name
            and st.session_state.get("field_name", "").strip() == field_name
        ):
            create_new_study()
    else:
        st.session_state["_resume_message"] = "Unable to delete the selected study."


def _render_read_only_page(page_name: str) -> None:
    """Render study data without creating editable Streamlit widgets."""
    section_keys = {
        "📋 Overview": ["project_name", "field_name", "project_phase", "study_lifecycle", "study_revision"],
        "👥 Team": ["team_members"],
        "1️⃣ Uncertainties": ["uncertainties"],
        "2️⃣ Key Decisions": ["key_decisions"],
        "3️⃣ Impact Assessment": ["impact_assessment"],
        "4️⃣ Key Uncertainties": ["key_uncertainties"],
        "5️⃣ Resolution List": ["resolution_list"],
        "6️⃣ Resolution Planner": ["resolution_planner"],
        "7️⃣ Risk Register": ["risk_register"],
        "📄 PRA Output": ["pra_output"],
        "📊 Intelligence": ["risk_register", "resolution_planner", "bowtie_register", "barrier_register"],
        "🛡️ Barrier Management": ["barrier_register", "bowtie_register"],
        "✅ Assurance & Review": ["study_reviews", "study_lifecycle"],
        "🕘 Revision History": ["study_change_log", "study_revision"],
    }
    st.info("Read-only view. Select Edit Study to unlock changes.")
    for key in section_keys.get(page_name, []):
        value = st.session_state.get(key, "")
        st.markdown(f"### {key.replace('_', ' ').title()}")
        if isinstance(value, (list, dict)):
            st.dataframe(value, use_container_width=True, hide_index=True)
        else:
            st.write(value or "Not configured")


def _enable_edit_mode() -> None:
    allowed, reason = can_edit_study(dict(st.session_state))
    if not allowed:
        st.error(reason)
        return
    st.session_state["study_access_mode"] = "edit"
    st.rerun()


# ============================================================================
# SIDEBAR
# ============================================================================

def _sidebar_nav_item(page: str, label: str, *, state: str = "available") -> None:
    """Render one compact, clearly stateful sidebar navigation item."""
    current_page = st.session_state.get("current_page")
    if state == "current":
        st.markdown(
            f"""
            <div class="surm-sidebar-nav-item surm-sidebar-nav-current">
                <span class="surm-sidebar-nav-indicator">●</span>
                <span class="surm-sidebar-nav-label">{html.escape(label)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if state == "completed":
        indicator = "✓"
    elif state == "locked":
        indicator = "🔒"
    else:
        indicator = "•"

    disabled = state == "locked"
    if st.button(
        f"{indicator}  {label}",
        key=f"sidebar_nav_{page}",
        use_container_width=True,
        disabled=disabled,
        type="secondary",
    ):
        st.session_state["current_page"] = page
        st.rerun()


def _render_sidebar_nav_group(
    title: str,
    pages: list[tuple[str, str, str]],
) -> None:
    """Render a small labelled group of primary navigation destinations."""
    st.markdown(
        f'<div class="surm-sidebar-nav-group-title">{html.escape(title)}</div>',
        unsafe_allow_html=True,
    )
    for page, label, state in pages:
        _sidebar_nav_item(page, label, state=state)


def _build_sidebar_navigation() -> dict[str, list[tuple[str, str, str]]]:
    """Build grouped navigation while keeping workflow availability authoritative."""
    session = cast(dict[str, Any], dict(st.session_state))
    stage_map = {
        page: stage
        for page, stage in zip(WORKFLOW_PAGES, stage_results(session))
    }
    current_page = st.session_state.get("current_page")

    def nav_state(page: str) -> str:
        if page == current_page:
            return "current"
        stage = stage_map.get(page)
        if stage is not None:
            if stage.complete:
                return "completed"
            if not stage.available:
                return "locked"
        return "available"

    def item(page: str, label: str) -> tuple[str, str, str]:
        return page, label, nav_state(page)

    return {
        "Study": [
            item("🗂️ Study Repository", "Study Repository"),
            item("📋 Overview", "Overview"),
            item("👥 Team", "Team"),
        ],
        "Workflow": [
            item(page, page.split(" ", 1)[-1])
            for page in WORKFLOW_PAGES
        ],
        "Insights & governance": [
            item("📊 Intelligence", "Intelligence"),
            item("🛡️ Barrier Management", "Barrier Management"),
            item("✅ Assurance & Review", "Assurance & Review"),
            item("🕘 Revision History", "Revision History"),
        ],
        "Support": [
            item("📖 How to Use", "How to Use"),
        ],
    }


def render_sidebar() -> None:
    """Render a calm, task-oriented sidebar with one primary navigation system."""
    from utils.persistence import save_session
    from utils.export_excel import build_excel_export

    ss = st.session_state
    stats = calculate_study_progress()
    session = cast(dict[str, Any], dict(ss))

    with st.sidebar:
        # ------------------------------------------------------------------
        # Brand
        # ------------------------------------------------------------------
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-brand-icon">🛢️</div>
                <div>
                    <div class="sidebar-brand-title">SURM Toolkit</div>
                    <div class="sidebar-brand-subtitle">PETRONAS CARIGALI</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ------------------------------------------------------------------
        # Study context — always visible because it anchors the user's place.
        # ------------------------------------------------------------------
        field = str(ss.get("field_name", "") or "").strip()
        project = str(ss.get("project_name", "") or "").strip()
        phase = str(ss.get("project_phase", "") or "").strip()
        lifecycle = str(ss.get("study_lifecycle", "Draft") or "Draft").strip()
        access_mode = "Edit" if study_is_editable(session) else "View"
        progress = stats["progress"]

        st.markdown(
            f"""
            <div class="surm-sidebar-study-card">
                <div class="surm-sidebar-study-kicker">CURRENT STUDY</div>
                <div class="surm-sidebar-study-title">{html.escape(project or "Untitled Study")}</div>
                <div class="surm-sidebar-study-meta">{html.escape(field or "Field not configured")}</div>
                <div class="surm-sidebar-study-chips">
                    <span>{html.escape(phase or "Phase —")}</span>
                    <span>{html.escape(lifecycle)}</span>
                    <span>{html.escape(access_mode)}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.progress(progress / 100, text=f"{progress}% workflow complete")

        # ------------------------------------------------------------------
        # Primary navigation — one source of truth.
        # ------------------------------------------------------------------
        st.markdown(
            '<div class="surm-sidebar-nav-label">Navigate</div>',
            unsafe_allow_html=True,
        )
        navigation = _build_sidebar_navigation()

        _render_sidebar_nav_group("Study", navigation["Study"])
        _render_sidebar_nav_group("Workflow", navigation["Workflow"])

        with st.expander("Insights & governance", expanded=False):
            for page, label, state in navigation["Insights & governance"]:
                _sidebar_nav_item(page, label, state=state)

        _render_sidebar_nav_group("Support", navigation["Support"])

        # ------------------------------------------------------------------
        # Frequent study actions stay visible; secondary options are collapsed.
        # ------------------------------------------------------------------
        st.markdown('<div class="surm-sidebar-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="surm-sidebar-nav-label">Study actions</div>',
            unsafe_allow_html=True,
        )

        action_col, new_col = st.columns([1.35, 1], gap="small")
        with action_col:
            if st.button(
                "💾 Save",
                key="sidebar_save_session",
                use_container_width=True,
                type="primary",
            ):
                if not project:
                    st.warning("Set a Project Name before saving.")
                elif save_session(auto=False):
                    st.success("Study saved.")
                else:
                    st.error("Unable to save the study.")
        with new_col:
            if st.button(
                "＋ New",
                key="sidebar_new_study",
                use_container_width=True,
                type="secondary",
            ):
                create_new_study()
                st.rerun()

        with st.expander("Session & export", expanded=False):
            st.checkbox(
                "Enable auto-save",
                key="_auto_save_enabled",
                help="Automatically save the current study when supported.",
            )

            last_saved = ss.get("_last_saved", "")
            st.caption(
                f"Last saved: {last_saved.replace('T', ' ')[:19]}"
                if last_saved
                else "No save recorded yet."
            )

            if ss.get("_resume_message"):
                st.success(ss["_resume_message"])

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
                st.warning(f"Excel export unavailable: {exc}")

        with st.expander("Account & access", expanded=False):
            st.caption(f"Active user: {current_user_label()}")
            if auth_required():
                st.caption("Authentication: enforced")
                if resolve_identity().authenticated:
                    st.button(
                        "Log out",
                        key="sidebar_logout",
                        use_container_width=True,
                        on_click=st.logout,
                        type="secondary",
                    )
            else:
                st.caption("Authentication: local development mode")

        st.caption(f"{APP_NAME} v{APP_VERSION}")


# ============================================================================
# PAGE ROUTER
# ============================================================================

PAGE_DEFINITIONS = {
    "🗂️ Study Repository": render_study_repository,
    "📖 How to Use": render_how_to_use,
    "📋 Overview": render_frontpage,
    "👥 Team": render_documentation,
    "1️⃣ Uncertainties": render_uncertainties,
    "2️⃣ Key Decisions": render_key_decisions,
    "3️⃣ Impact Assessment": render_impact_assessment,
    "4️⃣ Key Uncertainties": render_key_uncertainties,
    "5️⃣ Resolution List": render_resolution_list,
    "6️⃣ Resolution Planner": render_resolution_planner,
    "7️⃣ Risk Register": render_risk_register,
    "📄 PRA Output": render_pra_output,
    "📊 Intelligence": render_intelligence,
    "🛡️ Barrier Management": render_barrier_management,
    "✅ Assurance & Review": render_assurance,
    "🕘 Revision History": render_revision_history,
}
 
WORKFLOW_PAGES = [
    "1️⃣ Uncertainties",
    "2️⃣ Key Decisions",
    "3️⃣ Impact Assessment",
    "4️⃣ Key Uncertainties",
    "5️⃣ Resolution List",
    "6️⃣ Resolution Planner",
    "7️⃣ Risk Register",
    "📄 PRA Output",
]


def render_navigation() -> None:
    """
    Render page navigation.

    Navigation remains intentionally simple and reliable; workflow state and
    form guidance are provided by the shared workflow engine.
    """

    page_names = list(PAGE_DEFINITIONS.keys())
    selected_page = st.session_state.get("current_page", page_names[0])
    if selected_page not in PAGE_DEFINITIONS:
        selected_page = page_names[0]

    selected_index = page_names.index(selected_page)
    is_workflow_page = selected_page in WORKFLOW_PAGES
    workflow_index = WORKFLOW_PAGES.index(selected_page) if is_workflow_page else -1
    title = selected_page.split(" ", 1)[-1]
    descriptions = {
        "🗂️ Study Repository": "Browse, view, and edit saved field studies.",
        "📋 Overview": "A live view of study progress, outputs, and the next recommended step.",
        "👥 Team": "Maintain the people and roles contributing to this study.",
        "📖 How to Use": "A concise guide to the SURM study workflow.",
        "1️⃣ Uncertainties": "Select and refine the subsurface uncertainties relevant to the study.",
        "2️⃣ Key Decisions": "Define the decisions that the uncertainty assessment must support.",
        "3️⃣ Impact Assessment": "Rate uncertainty degree and decision impact to build the ranking.",
        "4️⃣ Key Uncertainties": "Review the ranked uncertainties and select those for resolution planning.",
        "5️⃣ Resolution List": "Map selected uncertainties to the actions that can resolve them.",
        "6️⃣ Resolution Planner": "Turn selected resolution actions into an owned, trackable workplan.",
        "7️⃣ Risk Register": "Convert study outputs into a managed risk register and bowtie view.",
        "📄 PRA Output": "Review the read-only portfolio output generated from the risk register.",
        "📊 Intelligence": "See study health, risk portfolio, actions, barriers, QA and traceability in one place.",
        "🛡️ Barrier Management": "Manage owners, status, verification and administrative health for Bowtie barriers.",
        "✅ Assurance & Review": "Control study lifecycle, review decisions, validation and approval readiness.",
        "🕘 Revision History": "Inspect immutable study revisions and compare durable changes.",
    }

    if is_workflow_page:
        session = cast(dict[str, Any], dict(st.session_state))
        stage_key = stage_results(session)[workflow_index].key
        allowed, reason = validate_stage(session, stage_key)
        if not allowed:
            render_page_frame(title, descriptions.get(selected_page, "SURM study workspace."), step=workflow_index + 1)
            st.warning(f"This stage is not ready yet. {reason}")
            current = current_stage(session)
            st.info(f"Current study stage: **{current.label}** — {current.guidance}")
            return

    custom_header_pages = {
        "🗂️ Study Repository",
        "📖 How to Use",
        "📋 Overview",
        "👥 Team",
        "📊 Intelligence",
        "🛡️ Barrier Management",
        "✅ Assurance & Review",
        "🕘 Revision History",
    }
    if not is_workflow_page and selected_page not in custom_header_pages:
        render_page_frame(
            title,
            descriptions.get(selected_page, "SURM study workspace."),
        )

    if (
        not study_is_editable(dict(st.session_state))
        and selected_page != "🗂️ Study Repository"
    ):
        edit_col, _ = st.columns([1, 5])
        with edit_col:
            st.button("✏️ Edit Study", key="view_page_edit_study", type="primary", on_click=_enable_edit_mode)
        _render_read_only_page(selected_page)
    else:
        PAGE_DEFINITIONS[selected_page]()



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

    # ------------------------------------------------------------------------
    # 1. Initialise session
    # ------------------------------------------------------------------------
    load_css()
    init_session()

    if auth_required() and not resolve_identity().authenticated:
        st.title("SURM Toolkit")
        st.info("Authentication is required for this deployment.")
        st.button("Log in", on_click=st.login, type="primary")
        st.stop()

    # Saved studies are loaded explicitly from the sidebar.


    # Reserve the header's visual position so page edits can refresh the
    # context shown in the global header and sidebar.
    header_slot = st.empty()
    render_navigation()

    with header_slot.container():
        render_header()

    render_sidebar()

    # ------------------------------------------------------------------------
    # 8. Footer
    # ------------------------------------------------------------------------

    render_footer()
# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
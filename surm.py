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
# IMPORT APPLICATION COMPONENTS
# ============================================================================
# All application-local imports intentionally happen after set_page_config so
# no imported module can accidentally issue a Streamlit command first.

from components.header import render_header as render_shared_header
from components.workflow import render_page_frame
from utils.assurance import study_is_editable
from utils.auth import (
    auth_required,
    can_edit_study,
    current_user_label,
    resolve_identity,
)
from utils.styles import load_css
from utils.workflow import current_stage, stage_results, validate_stage


# ============================================================================
# APPLICATION SERVICES + PAGE MODULES
# ============================================================================

from utils.session import create_new_study, init_session, study_has_unsaved_changes

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
# APPLICATION HEADER
# ============================================================================
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
        workspace=str(ss.get("current_page", "Workspace")).split(" ", 1)[-1],
        app_name=APP_NAME,
        subtitle=APP_SUBTITLE,
        saved=bool(ss.get("_last_saved")) and not study_has_unsaved_changes(ss),
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

def render_sidebar() -> None:
    """Render a compact engineering-workspace sidebar with one navigation control."""
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

        field = str(ss.get("field_name", "") or "").strip()
        project = str(ss.get("project_name", "") or "").strip()
        phase = str(ss.get("project_phase", "") or "").strip()
        lifecycle = str(ss.get("study_lifecycle", "Draft") or "Draft").strip()
        access_mode = "Edit" if study_is_editable(session) else "View"

        # ------------------------------------------------------------------
        # Current study
        # ------------------------------------------------------------------
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

        progress = stats["progress"]
        st.progress(progress / 100, text=f"{progress}% workflow complete")

        # ------------------------------------------------------------------
        # Primary navigation — intentionally one control.
        # ------------------------------------------------------------------
        current_page = st.session_state.get("current_page", "📋 Overview")
        try:
            current_index = NAVIGATION_ORDER.index(current_page)
        except ValueError:
            current_index = 0

        # Keep the selector aligned with navigation from pager buttons and
        # other page-level actions before the widget is instantiated.
        ss["sidebar_page_selector"] = current_page

        stage_map = {
            page: stage
            for page, stage in zip(
                WORKFLOW_PAGES,
                stage_results(session),
            )
        }

        def navigation_label(page: str) -> str:
            stage = stage_map.get(page)
            if page == current_page:
                marker = "●"
            elif stage is not None and stage.complete:
                marker = "✓"
            elif stage is not None and not stage.available:
                marker = "🔒"
            else:
                marker = "•"

            label = page.split(" ", 1)[-1]
            if page in WORKFLOW_PAGES:
                step_no = WORKFLOW_PAGES.index(page) + 1
                label = f"{step_no:02d}  {label}"
            return f"{marker}  {label}"

        selected_page = st.selectbox(
            "Navigate",
            NAVIGATION_ORDER,
            index=current_index,
            key="sidebar_page_selector",
            format_func=navigation_label,
            help="Use one control to move anywhere in the study workspace.",
        )

        if selected_page != current_page:
            st.session_state["current_page"] = selected_page
            st.rerun()

        try:
            position = NAVIGATION_ORDER.index(current_page) + 1
        except ValueError:
            position = 1
        st.caption(f"Workspace page {position} of {len(NAVIGATION_ORDER)}")

        # ------------------------------------------------------------------
        # Primary study actions
        # ------------------------------------------------------------------
        action_col, new_col = st.columns(2, gap="small")
        with action_col:
            if st.button(
                "💾 Save study",
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
                "＋ New study",
                key="sidebar_new_study",
                use_container_width=True,
                type="secondary",
            ):
                create_new_study()
                st.rerun()

        # ------------------------------------------------------------------
        # Secondary tools and access — one collapsed surface, no nested cards.
        # ------------------------------------------------------------------
        with st.expander("More", expanded=False):
            st.markdown(
                '<div class="surm-sidebar-section-label">SESSION</div>',
                unsafe_allow_html=True,
            )
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

            st.markdown(
                '<div class="surm-sidebar-section-label">EXPORT</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "⚙ Prepare Excel export",
                key="prepare_excel_export",
                use_container_width=True,
                type="secondary",
                help="Build the current study workbook when you are ready to export it.",
            ):
                try:
                    with st.spinner("Preparing Excel workbook..."):
                        ss["_excel_export_data"] = build_excel_export()
                    st.success("Excel workbook prepared.")
                except Exception as exc:
                    ss.pop("_excel_export_data", None)
                    st.error(f"Excel export unavailable: {exc}")

            excel_data = ss.get("_excel_export_data")
            if excel_data:
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

            st.markdown(
                '<div class="surm-sidebar-section-label">ACCOUNT & ACCESS</div>',
                unsafe_allow_html=True,
            )
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
# READ-ONLY VIEW
# ============================================================================

def _render_read_only_page(page_name: str) -> None:
    """Render a safe, widget-free snapshot for view-only study sessions.

    Loaded studies intentionally enter ``study_access_mode='view'``. The
    read-only path must never call editable page renderers because those pages
    create Streamlit widgets and can mutate session state on rerun.
    """

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

    st.info("Read-only view. Select **Edit Study** to unlock changes.")

    for key in section_keys.get(page_name, []):
        value = st.session_state.get(key, "")
        st.markdown(f"### {key.replace('_', ' ').title()}")

        if isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                st.dataframe(value, use_container_width=True, hide_index=True)
            else:
                st.write(value or "No records.")
        elif isinstance(value, dict):
            if value:
                st.json(value)
            else:
                st.caption("No records.")
        else:
            st.write(value if str(value).strip() else "Not configured")


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


NAVIGATION_ORDER = [
    "🗂️ Study Repository",
    "📋 Overview",
    "👥 Team",
    "1️⃣ Uncertainties",
    "2️⃣ Key Decisions",
    "3️⃣ Impact Assessment",
    "4️⃣ Key Uncertainties",
    "5️⃣ Resolution List",
    "6️⃣ Resolution Planner",
    "7️⃣ Risk Register",
    "📄 PRA Output",
    "📊 Intelligence",
    "🛡️ Barrier Management",
    "✅ Assurance & Review",
    "🕘 Revision History",
    "📖 How to Use",
]


def _navigation_target(offset: int) -> str | None:
    """Return the adjacent page in the consistent application sequence."""
    current = st.session_state.get("current_page", "📋 Overview")
    try:
        index = NAVIGATION_ORDER.index(current)
    except ValueError:
        return None
    target = index + offset
    if target < 0 or target >= len(NAVIGATION_ORDER):
        return None
    return NAVIGATION_ORDER[target]


def render_page_pager(*, location: str) -> None:
    """Render consistent Previous / Next controls on every application page."""
    current = st.session_state.get("current_page", "📋 Overview")
    try:
        position = NAVIGATION_ORDER.index(current) + 1
    except ValueError:
        position = 1

    previous_page = _navigation_target(-1)
    next_page = _navigation_target(1)
    previous_text = (
        f"← {previous_page.split(' ', 1)[-1]}"
        if previous_page else "← Previous"
    )
    next_text = (
        f"{next_page.split(' ', 1)[-1]} →"
        if next_page else "Next →"
    )

    container = st.container()
    with container:
        left, center, right = st.columns([1.35, 2.3, 1.35], gap="small")
        with left:
            st.button(
                previous_text,
                key=f"pager_previous_{location}",
                use_container_width=True,
                disabled=previous_page is None,
                on_click=(
                    (lambda page=previous_page: st.session_state.update(
                        current_page=page
                    ))
                    if previous_page
                    else None
                ),
            )
        with center:
            st.markdown(
                f"""
                <div class="surm-page-pager">
                    <span class="surm-page-pager-kicker">STUDY NAVIGATION</span>
                    <strong class="surm-page-pager-title">
                        {html.escape(current.split(" ", 1)[-1])}
                    </strong>
                    <span class="surm-page-pager-meta">
                        Page {position} of {len(NAVIGATION_ORDER)}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            st.button(
                next_text,
                key=f"pager_next_{location}",
                use_container_width=True,
                disabled=next_page is None,
                type="primary" if next_page else "secondary",
                on_click=(
                    (lambda page=next_page: st.session_state.update(
                        current_page=page
                    ))
                    if next_page
                    else None
                ),
            )



def render_navigation() -> None:
    """
    Render page navigation.

    Navigation remains intentionally simple and reliable; workflow state and
    form guidance are provided by the shared workflow engine.
    """

    page_names = list(PAGE_DEFINITIONS.keys())

    # Repository resume has priority over the page that rendered the load
    # action. Consume it once, then let normal sidebar navigation take over.
    pending_page = st.session_state.pop("_pending_navigation_page", None)
    if pending_page in PAGE_DEFINITIONS:
        st.session_state["current_page"] = pending_page

    selected_page = st.session_state.get("current_page", page_names[0])
    if selected_page not in PAGE_DEFINITIONS:
        selected_page = page_names[0]

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

    blocked = False
    if is_workflow_page:
        session = cast(dict[str, Any], dict(st.session_state))
        stage_key = stage_results(session)[workflow_index].key
        allowed, reason = validate_stage(session, stage_key)
        if not allowed:
            render_page_frame(
                title,
                descriptions.get(selected_page, "SURM study workspace."),
                step=workflow_index + 1,
            )
            st.warning(f"This stage is not ready yet. {reason}")
            current = current_stage(session)
            st.info(
                f"Current study stage: **{current.label}** — {current.guidance}"
            )
            blocked = True

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

    render_page_pager(location="top")

    if not blocked:
        if (
            not study_is_editable(dict(st.session_state))
            and selected_page != "🗂️ Study Repository"
        ):
            edit_col, _ = st.columns([1, 5])
            with edit_col:
                st.button(
                    "✏️ Edit Study",
                    key="view_page_edit_study",
                    type="primary",
                    on_click=_enable_edit_mode,
                )
            _render_read_only_page(selected_page)
        else:
            PAGE_DEFINITIONS[selected_page]()

    render_page_pager(location="bottom")



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

    # Keep the Streamlit element tree stable across reruns: render the
    # persistent header directly before the page content instead of creating
    # an empty placeholder and filling it after the page has rendered.
    render_header()
    render_sidebar()
    render_navigation()

    # ------------------------------------------------------------------------
    # 8. Footer
    # ------------------------------------------------------------------------

    render_footer()
# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
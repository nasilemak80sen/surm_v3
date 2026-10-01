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
    completed_stages = sum(stage.complete for stage in stages)
    total_stages = len(stages)
    progress = round(
        (completed_stages / total_stages) * 100
    ) if total_stages else 0

    return {
        "selected_uncertainties": selected_uncertainties,
        "total_uncertainties": total_uncertainties,
        "key_decisions": decisions,
        "key_uncertainties": included_key_uncertainties,
        "resolution_actions": actions,
        "risks": risks,
        "team_members": team,
        "completed_stages": completed_stages,
        "total_stages": total_stages,
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
    """Render a visual, contextual navigation rail for the study workspace."""
    from streamlit_extras.grid import grid
    from utils.export_excel import build_excel_export
    from utils.persistence import save_session

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
                <div class="sidebar-brand-icon">◈</div>
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
        lifecycle = str(
            ss.get("study_lifecycle", "Draft") or "Draft"
        ).strip()
        access_mode = "EDIT" if study_is_editable(session) else "VIEW"
        progress = stats["progress"]
        completed_stages = stats["completed_stages"]
        total_stages = stats["total_stages"]

        # ------------------------------------------------------------------
        # Current study identity
        # ------------------------------------------------------------------
        with st.container(key="sidebar-study-context", border=False):
            st.markdown(
                f"""
                <div class="sidebar-context-kicker">CURRENT STUDY</div>
                <div class="sidebar-context-title">
                    {html.escape(project or "Untitled Study")}
                </div>
                <div class="sidebar-context-meta">
                    {html.escape(field or "Field not configured")}
                    <span>·</span>
                    {html.escape(phase or "Phase —")}
                </div>
                <div class="sidebar-context-status">
                    <span>{html.escape(lifecycle)}</span>
                    <span>{html.escape(access_mode)}</span>
                </div>
                <div class="sidebar-stage-progress">
                    <div class="sidebar-stage-progress-header">
                        <span>STUDY STAGES</span>
                        <strong>{progress}%</strong>
                    </div>
                    <div class="sidebar-stage-progress-summary">
                        {completed_stages} of {total_stages} stages complete
                    </div>
                    <div
                        class="sidebar-stage-progress-track"
                        role="progressbar"
                        aria-label="Study stage completion"
                        aria-valuemin="0"
                        aria-valuemax="{total_stages}"
                        aria-valuenow="{completed_stages}"
                    >
                        <div
                            class="sidebar-stage-progress-fill"
                            style="width: {progress}%"
                        ></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ------------------------------------------------------------------
        # Contextual navigation
        # ------------------------------------------------------------------
        current_page = st.session_state.get(
            "current_page",
            "📋 Overview",
        )
        if current_page not in NAVIGATION_ORDER:
            current_page = "📋 Overview"
            st.session_state["current_page"] = current_page

        study_pages = [
            "🗂️ Study Repository",
            "📋 Overview",
            "👥 Team",
        ]
        insight_pages = [
            "📄 PRA Output",
            "📊 Intelligence",
            "🛡️ Barrier Management",
            "✅ Assurance & Review",
            "🕘 Revision History",
        ]
        support_pages = ["📖 How to Use"]

        if current_page in study_pages:
            active_area = "Study"
        elif current_page in WORKFLOW_PAGES:
            active_area = "Workflow"
        elif current_page in insight_pages:
            active_area = "Insights"
        else:
            active_area = "Support"

        # Keep the workspace selector aligned with the page on entry, but do
        # not overwrite a user selection before Streamlit can deliver it.
        if ss.get("sidebar_area_selector") not in {"Study", "Workflow", "Insights", "Support"}:
            ss["sidebar_area_selector"] = active_area

        stage_map = {
            page: stage
            for page, stage in zip(
                WORKFLOW_PAGES,
                stage_results(session),
            )
        }

        area_pages = {
            "Study": study_pages,
            "Workflow": WORKFLOW_PAGES,
            "Insights": insight_pages,
            "Support": support_pages,
        }

        area = st.segmented_control(
            "Workspace area",
            ["Study", "Workflow", "Insights", "Support"],
            key="sidebar_area_selector",
            label_visibility="collapsed",
        )

        if area and area != active_area:
            st.session_state["current_page"] = area_pages[area][0]
            st.rerun()

        pages = area_pages.get(area or active_area, study_pages)

        def _go_to(page: str) -> None:
            _set_current_page(page)

        def _page_title(page: str) -> str:
            return page.split(" ", 1)[-1]

        # ------------------------------------------------------------------
        # Journey header
        # ------------------------------------------------------------------
        with st.container(key="sidebar-navigation", border=False):
            area_title = area or active_area
            st.markdown(
                f"""
                <div class="sidebar-journey-header">
                    <div>
                        <div class="sidebar-section-title">
                            {html.escape(area_title.upper())}
                        </div>
                        <div class="sidebar-journey-title">
                            {(
                                "Build the study"
                                if area_title == "Study"
                                else "Work through the gates"
                                if area_title == "Workflow"
                                else "Review and assure"
                                if area_title == "Insights"
                                else "Reference and guidance"
                            )}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if area_title == "Workflow":
                completed_count = sum(
                    1 for stage in stage_map.values()
                    if stage.complete
                )
                next_stage = next(
                    (
                        page
                        for page in WORKFLOW_PAGES
                        if stage_map.get(page)
                        and not stage_map[page].complete
                        and stage_map[page].available
                    ),
                    None,
                )

                st.markdown(
                    f"""
                    <div class="sidebar-workflow-summary">
                        <span>WORKFLOW PROGRESS</span>
                        <strong>{completed_count}/{len(WORKFLOW_PAGES)}</strong>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if next_stage and next_stage != current_page:
                    if st.button(
                        f"Continue · {_page_title(next_stage)}  →",
                        key="sidebar_continue_next_stage",
                        type="primary",
                        use_container_width=True,
                        on_click=_go_to,
                        args=(next_stage,),
                    ):
                        pass

            page_labels = {
                "🗂️ Study Repository": ("Repository", "Saved studies"),
                "📋 Overview": ("Overview", "Study control center"),
                "👥 Team": ("Team", "Roles and ownership"),
                "📄 PRA Output": ("PRA Output", "Decision-ready output"),
                "📊 Intelligence": ("Intelligence", "Signals and analytics"),
                "🛡️ Barrier Management": ("Barrier Management", "Controls and barriers"),
                "✅ Assurance & Review": ("Assurance & Review", "Governance checkpoints"),
                "🕘 Revision History": ("Revision History", "Change trace"),
                "📖 How to Use": ("How to Use", "Workflow guidance"),
            }

            for index, page in enumerate(pages):
                stage = stage_map.get(page)
                if stage is not None:
                    if stage.complete:
                        state = "COMPLETE"
                        icon = "✓"
                    elif stage.available:
                        state = "READY"
                        icon = "→"
                    else:
                        state = "LOCKED"
                        icon = "—"
                    step = f"{WORKFLOW_PAGES.index(page) + 1:02d}"
                    title = _page_title(page)
                    subtitle = stage.guidance
                    disabled = not stage.available and not stage.complete
                else:
                    label, subtitle = page_labels.get(
                        page,
                        (_page_title(page), ""),
                    )
                    title = label
                    state = "CURRENT" if page == current_page else "OPEN"
                    icon = "●" if page == current_page else "○"
                    step = f"{index + 1:02d}"
                    disabled = False

                selected = page == current_page
                if selected:
                    state = "CURRENT"

                if stage is not None:
                    nav_label = f"{icon}  {step}  {title}  ·  {state}"
                else:
                    nav_label = f"{icon}  {title}  ·  {state}"

                st.button(
                    nav_label,
                    key=f"sidebar_page_{index}_{page}",
                    use_container_width=True,
                    disabled=disabled,
                    type="primary" if selected else "secondary",
                    on_click=_go_to,
                    args=(page,),
                )

            if area_title == "Workflow":
                st.caption(
                    "Locked stages become available when their upstream gate is satisfied."
                )
            elif area_title == "Study":
                st.caption("Set up the study, manage the team, then enter the workflow.")
            elif area_title == "Insights":
                st.caption("Use these pages for output, intelligence, barriers and assurance.")
            else:
                st.caption("Reference material and workflow guidance.")

        # ------------------------------------------------------------------
        # Primary actions
        # ------------------------------------------------------------------
        with st.container(key="sidebar-actions", border=False):
            action_grid = grid(2, gap="small", vertical_align="center")
            save_clicked = action_grid.button(
                "Save",
                key="sidebar_save_session",
                type="primary",
                use_container_width=True,
            )
            new_clicked = action_grid.button(
                "＋ New",
                key="sidebar_new_study",
                use_container_width=True,
            )

            if save_clicked:
                if not project:
                    st.warning("Set a Project Name before saving.")
                elif save_session(auto=False):
                    st.success("Study saved.")
                else:
                    st.error("Unable to save the study.")

            if new_clicked:
                create_new_study()
                st.rerun()

        # ------------------------------------------------------------------
        # Secondary utilities
        # ------------------------------------------------------------------
        with st.expander("Utilities & access", expanded=False):
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

            st.markdown(
                '<div class="surm-sidebar-section-label">EXPORT</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Prepare Excel export",
                key="prepare_excel_export",
                use_container_width=True,
                type="secondary",
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
                    "Download Excel",
                    data=excel_data,
                    file_name=filename,
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    use_container_width=True,
                )

            st.markdown(
                '<div class="surm-sidebar-section-label">ACCOUNT</div>',
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

PAGE_AREAS = {
    "Study": (
        "🗂️ Study Repository",
        "📋 Overview",
        "👥 Team",
    ),
    "Workflow": tuple(WORKFLOW_PAGES),
    "Insights": (
        "📄 PRA Output",
        "📊 Intelligence",
        "🛡️ Barrier Management",
        "✅ Assurance & Review",
        "🕘 Revision History",
    ),
    "Support": ("📖 How to Use",),
}


def _set_current_page(page: str) -> None:
    """Keep the sidebar workspace selector synchronized with navigation."""
    if page not in PAGE_DEFINITIONS:
        return
    st.session_state["current_page"] = page
    st.session_state["sidebar_area_selector"] = next(
        area for area, pages in PAGE_AREAS.items() if page in pages
    )


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


def render_page_pager() -> None:
    """Render Previous / Next controls at the top of each application page."""
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

    container = st.container(key="page-navigation")
    with container:
        left, center, right = st.columns([1.35, 2.3, 1.35], gap="small")
        with left:
            st.button(
                previous_text,
                key="pager_previous",
                use_container_width=True,
                disabled=previous_page is None,
                on_click=_set_current_page if previous_page else None,
                args=(previous_page,) if previous_page else (),
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
                key="pager_next",
                use_container_width=True,
                disabled=next_page is None,
                type="primary" if next_page else "secondary",
                on_click=_set_current_page if next_page else None,
                args=(next_page,) if next_page else (),
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
    blocked_reason = ""
    blocked_stage = None
    if is_workflow_page:
        session = cast(dict[str, Any], dict(st.session_state))
        stage_key = stage_results(session)[workflow_index].key
        allowed, reason = validate_stage(session, stage_key)
        if not allowed:
            blocked = True
            blocked_reason = reason
            blocked_stage = current_stage(session)

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

    render_page_pager()

    if blocked:
        render_page_frame(
            title,
            descriptions.get(selected_page, "SURM study workspace."),
            step=workflow_index + 1,
        )
        st.warning(f"This stage is not ready yet. {blocked_reason}")
        if blocked_stage is not None:
            st.info(
                f"Current study stage: **{blocked_stage.label}** — "
                f"{blocked_stage.guidance}"
            )

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
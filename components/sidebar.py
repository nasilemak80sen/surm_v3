"""
SURM Sidebar Component.

Responsible for application navigation and high-level study context.
"""

from __future__ import annotations

import html
from collections.abc import Callable

import streamlit as st

from components.status import status_html
from components.workflow import render_workflow_list
from utils.ui import render_html


# ============================================================================
# DEFAULT WORKFLOW
# ============================================================================

DEFAULT_WORKFLOW = [
    {
        "number": 1,
        "label": "Uncertainties",
        "page": "1️⃣ Uncertainties",
    },
    {
        "number": 2,
        "label": "Key Decisions",
        "page": "2️⃣ Key Decisions",
    },
    {
        "number": 3,
        "label": "Impact Assessment",
        "page": "3️⃣ Impact Assessment",
    },
    {
        "number": 4,
        "label": "Key Uncertainties",
        "page": "4️⃣ Key Uncertainties",
    },
    {
        "number": 5,
        "label": "Resolution List",
        "page": "5️⃣ Resolution List",
    },
    {
        "number": 6,
        "label": "Resolution Planner",
        "page": "6️⃣ Resolution Planner",
    },
    {
        "number": 7,
        "label": "Risk Register",
        "page": "7️⃣ Risk Register",
    },
]


# ============================================================================
# STUDY STATISTICS
# ============================================================================

def get_study_statistics() -> dict:
    """
    Read basic study statistics from session state.
    """

    ss = st.session_state

    uncertainties = ss.get(
        "uncertainties",
        [],
    )

    key_decisions = ss.get(
        "key_decisions",
        [],
    )

    key_uncertainties = ss.get(
        "key_uncertainties",
        [],
    )

    resolution_planner = ss.get(
        "resolution_planner",
        [],
    )

    risk_register = ss.get(
        "risk_register",
        [],
    )

    team_members = ss.get(
        "team_members",
        [],
    )

    selected_uncertainties = sum(
        1
        for item in uncertainties
        if isinstance(item, dict)
        and item.get("selected")
    )

    decisions = sum(
        1
        for item in key_decisions
        if isinstance(item, dict)
        and str(
            item.get(
                "Key Decision",
                "",
            )
        ).strip()
    )

    selected_key_uncertainties = sum(
        1
        for item in key_uncertainties
        if isinstance(item, dict)
        and item.get(
            "Include in Plan"
        )
    )

    return {
        "uncertainties": selected_uncertainties,
        "uncertainties_total": len(
            uncertainties
        ),
        "decisions": decisions,
        "key_uncertainties": selected_key_uncertainties,
        "actions": len(
            resolution_planner
        ),
        "risks": len(
            risk_register
        ),
        "team": sum(
            1
            for item in team_members
            if isinstance(item, dict)
            and str(
                item.get(
                    "Name",
                    "",
                )
            ).strip()
        ),
    }


# ============================================================================
# STUDY PROGRESS
# ============================================================================

def calculate_study_progress() -> float:
    """
    Calculate high-level study completion.
    """

    ss = st.session_state

    checks = [
        bool(
            str(
                ss.get(
                    "project_name",
                    "",
                )
            ).strip()
        ),

        len(
            ss.get(
                "uncertainties",
                [],
            )
        ) > 0,

        len(
            ss.get(
                "key_decisions",
                [],
            )
        ) > 0,

        bool(
            ss.get(
                "impact_assessment",
                [],
            )
        ),

        len(
            ss.get(
                "key_uncertainties",
                [],
            )
        ) > 0,

        bool(
            ss.get(
                "resolution_list",
                {},
            )
        ),

        len(
            ss.get(
                "resolution_planner",
                [],
            )
        ) > 0,

        len(
            ss.get(
                "risk_register",
                [],
            )
        ) > 0,
    ]

    if not checks:
        return 0.0

    return (
        sum(checks)
        / len(checks)
        * 100
    )


# ============================================================================
# SIDEBAR
# ============================================================================

def render_sidebar(
    page_names: list[str],
    *,
    workflow: list[dict] | None = None,
    on_save: Callable[[], bool] | None = None,
) -> str:
    """
    Render the SURM sidebar.

    Returns
    -------
    str
        Selected page.
    """

    ss = st.session_state

    workflow = (
        workflow
        if workflow is not None
        else DEFAULT_WORKFLOW
    )

    stats = get_study_statistics()
    progress = calculate_study_progress()

    current_page = ss.get(
        "current_page",
        page_names[0] if page_names else "",
    )

    with st.sidebar:

        # ====================================================================
        # BRAND
        # ====================================================================

        render_html(
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
            """)
        
        st.divider()

        # ====================================================================
        # CURRENT STUDY
        # ====================================================================

        render_html(
            """
            <div class="sidebar-section-title">
                Current Study
            </div>
            """,
             
        )

        field = str(
            ss.get(
                "field_name",
                "",
            )
        ).strip()

        project = str(
            ss.get(
                "project_name",
                "",
            )
        ).strip()

        phase = str(
            ss.get(
                "project_phase",
                "",
            )
        ).strip()

        st.markdown(
            f"""
            <div class="sidebar-study">

                <div class="sidebar-study-row">
                    <span>Field</span>
                    <strong>
                        {html.escape(field or "Not configured")}
                    </strong>
                </div>

                <div class="sidebar-study-row">
                    <span>Project</span>
                    <strong>
                        {html.escape(project or "Not configured")}
                    </strong>
                </div>

                <div class="sidebar-study-row">
                    <span>Phase</span>
                    <strong>
                        {html.escape(phase or "Not configured")}
                    </strong>
                </div>

            </div>
            """,
             
        )

        st.divider()

        # ====================================================================
        # PROGRESS
        # ====================================================================

        st.markdown(
            """
            <div class="sidebar-section-title">
                Study Progress
            </div>
            """,
             
        )

        st.progress(
            progress / 100,
            text=f"{progress:.0f}% complete",
        )

        # ====================================================================
        # WORKFLOW
        # ====================================================================

        st.markdown(
            """
            <div class="sidebar-section-title">
                Study Workflow
            </div>
            """,
             
        )

        render_workflow_list(
            workflow,
            current_page=current_page,
        )

        st.divider()

        # ====================================================================
        # STATISTICS
        # ====================================================================

        st.markdown(
            """
            <div class="sidebar-section-title">
                Study Summary
            </div>
            """,
             
        )

        statistics = [
            (
                "Uncertainties",
                (
                    f'{stats["uncertainties"]} / '
                    f'{stats["uncertainties_total"]}'
                ),
            ),
            (
                "Key Decisions",
                stats["decisions"],
            ),
            (
                "Key Uncertainties",
                stats["key_uncertainties"],
            ),
            (
                "Actions",
                stats["actions"],
            ),
            (
                "Risks",
                stats["risks"],
            ),
            (
                "Team",
                stats["team"],
            ),
        ]

        for label, value in statistics:

            left, right = st.columns(
                [3, 1]
            )

            with left:
                st.caption(label)

            with right:
                st.markdown(
                    f"""
                    <div class="sidebar-stat-value">
                        {html.escape(str(value))}
                    </div>
                    """,
                     
                )

        st.divider()

        # ====================================================================
        # NAVIGATION
        # ====================================================================

        selected_page = st.radio(
            "Navigation",
            page_names,
            index=(
                page_names.index(current_page)
                if current_page in page_names
                else 0
            ),
            key="surm_navigation",
            label_visibility="collapsed",
        )

        ss["current_page"] = selected_page

        # ====================================================================
        # SESSION ACTIONS
        # ====================================================================

        st.divider()

        st.markdown(
            """
            <div class="sidebar-section-title">
                Session
            </div>
            """,
             
        )

        if on_save is not None:

            if st.button(
                "💾 Save Session",
                key="sidebar_save_session_v2",
                use_container_width=True,
                type="primary",
            ):

                success = on_save()

                if success:
                    st.success(
                        "Session saved."
                    )
                else:
                    st.error(
                        "Unable to save session."
                    )

        st.checkbox(
            "Enable auto-save",
            key="_auto_save_enabled",
        )

        if ss.get("_last_saved"):

            st.caption(
                "Last saved: "
                + str(
                    ss["_last_saved"]
                ).replace(
                    "T",
                    " ",
                )[:19]
            )

        else:

            st.caption(
                "No save recorded yet."
            )

        return selected_page
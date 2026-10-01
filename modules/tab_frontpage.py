"""SURM report front page: identity, readiness, governance and export."""

from __future__ import annotations

from datetime import date
import html
import streamlit as st
from streamlit_extras.grid import grid

from utils.analytics import build_study_analytics, validation_warnings
from utils.assurance import LIFECYCLE_ORDER
from utils.form_ui import render_save_hint
from utils.persistence import save_session
from utils.workflow import current_stage, stage_results


_PHASES = ["", "PGR0", "PGR1", "PGR2", "PGR3/FID", "ITR2a", "ITR2b", "SBS", "SIR2a", "SIR2b", "PGR4"]


def _sync_widget_value(target_key: str, widget_key: str) -> None:
    """Copy a page widget's value into durable study state before rerun."""
    st.session_state[target_key] = st.session_state.get(widget_key, "")


def _ensure_widget_value(widget_key: str, target_key: str) -> None:
    """Seed a page-local widget from the durable study field when it reappears."""
    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state.get(target_key, "")


def _parse_signoff_date(value: str) -> date | None:
    if not value:
        return None
    try:
        day, month, year = (int(part) for part in value.split("/"))
        return date(year, month, day)
    except (TypeError, ValueError):
        return None


def render():
    """Render the Overview as a disciplined study control center."""
    ss = st.session_state
    stages = stage_results(ss)
    progress = (
        round(sum(stage.complete for stage in stages) / len(stages) * 100)
        if stages
        else 0
    )
    next_stage = current_stage(ss)
    analytics = build_study_analytics(dict(ss))
    warnings = validation_warnings(dict(ss))

    project = ss.get("project_name") or "Untitled Study"
    field = ss.get("field_name") or "Field not configured"
    phase = ss.get("project_phase") or "Phase not configured"
    lifecycle = str(ss.get("study_lifecycle", "Draft") or "Draft")
    revision = ss.get("study_revision", 0)

    workflow_counts = {
        "completed": sum(1 for stage in stages if stage.complete),
        "total": len(stages),
    }

    signoffs = [
        ("Prepared By", "prep"),
        ("Reviewed — G&G", "rev_gg"),
        ("Reviewed — RE", "rev_re"),
        ("Reviewed — PP", "rev_pp"),
        ("Endorsed — FDP Lead", "endorsed"),
    ]
    signoff_complete = 0
    for _, key in signoffs:
        if (
            str(ss.get(f"{key}_name", "") or "").strip()
            and str(ss.get(f"{key}_role", "") or "").strip()
            and str(ss.get(f"{key}_date", "") or "").strip()
        ):
            signoff_complete += 1

    # ------------------------------------------------------------------
    # 1. Study identity — compact, high-signal introduction.
    # ------------------------------------------------------------------
    with st.container(key="overview-hero", border=False):
        st.markdown(
            f"""
            <div class="overview-hero-inner">
                <div class="overview-hero-kicker">STUDY CONTROL CENTER</div>
                <div class="overview-hero-title">{html.escape(project)}</div>
                <div class="overview-hero-meta">
                    <span>{html.escape(field)}</span>
                    <span>{html.escape(phase)}</span>
                    <span>Revision {html.escape(str(revision))}</span>
                    <span>{html.escape(lifecycle)}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # 2. Executive snapshot — equal-weight KPIs.
    # ------------------------------------------------------------------
    st.markdown(
        '<div class="surm-overview-section-label">EXECUTIVE SNAPSHOT</div>',
        unsafe_allow_html=True,
    )

    metric_grid = grid(4, gap="medium", vertical_align="top")
    metric_grid.metric(
        "Workflow",
        f"{progress}%",
        delta=f"{workflow_counts['completed']} of {workflow_counts['total']} gates",
    )
    metric_grid.metric(
        "Selected uncertainties",
        sum(
            1
            for item in ss.get("uncertainties", [])
            if isinstance(item, dict) and item.get("selected")
        ),
    )
    metric_grid.metric(
        "Resolution actions",
        len(ss.get("resolution_planner", [])),
    )
    metric_grid.metric(
        "Risks",
        len(ss.get("risk_register", [])),
    )

    # ------------------------------------------------------------------
    # 3. Decision support — action gets slightly more width than signal.
    # ------------------------------------------------------------------
    action_col, signal_col = st.columns([1.2, 1], gap="large")

    with action_col:
        with st.container(key="overview-next-action", border=True):
            st.markdown(
                '<div class="surm-panel-kicker">NEXT ACTION</div>',
                unsafe_allow_html=True,
            )

            if next_stage.complete:
                action_title = "Core workflow complete"
                action_copy = (
                    "Review the PRA output and confirm the remaining governance "
                    "checkpoints."
                )
                action_page = "📄 PRA Output"
                action_label = "Open PRA Output"
            else:
                action_title = next_stage.label.split(" ", 1)[-1]
                action_copy = next_stage.guidance
                action_page = next_stage.label
                action_label = "Continue to next gate"

            st.markdown(
                f'<div class="overview-action-stage">{html.escape(action_title)}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="overview-action-copy">{html.escape(action_copy)}</div>',
                unsafe_allow_html=True,
            )

            if st.button(
                action_label,
                key="overview_continue",
                type="primary",
                use_container_width=True,
            ):
                st.session_state["current_page"] = action_page
                st.rerun()

    with signal_col:
        with st.container(key="overview-current-signal", border=True):
            st.markdown(
                '<div class="surm-panel-kicker">CURRENT SIGNAL</div>',
                unsafe_allow_html=True,
            )

            critical = analytics.get("critical_uncertainties", [])
            if critical:
                st.markdown(
                    '<div class="overview-signal-stack">'
                    + "".join(
                        f"""
                        <div class="overview-signal-row">
                            <span class="overview-signal-index">{idx:02d}</span>
                            <span>{html.escape(str(item))}</span>
                        </div>
                        """
                        for idx, item in enumerate(critical[:3], start=1)
                    )
                    + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="overview-empty-signal">'
                    "No ranked key uncertainties yet."
                    "</div>",
                    unsafe_allow_html=True,
                )

            st.progress(
                progress / 100,
                text=f"{progress}% workflow complete",
            )

    # ------------------------------------------------------------------
    # 4. Attention — only appears when there is something actionable.
    # ------------------------------------------------------------------
    if warnings:
        with st.container(key="overview-attention", border=True):
            st.markdown(
                '<div class="surm-panel-kicker">ATTENTION</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                "".join(
                    f"""
                    <div class="overview-attention-row">
                        <span class="overview-attention-marker">!</span>
                        <span>{html.escape(str(warning["message"]))}</span>
                    </div>
                    """
                    for warning in warnings[:4]
                ),
                unsafe_allow_html=True,
            )

    # ------------------------------------------------------------------
    # 5. Study setup — one clean row of identity/governance fields.
    # ------------------------------------------------------------------
    with st.container(key="overview-study-setup", border=True):
        st.markdown("### Study setup")
        st.caption(
            "Study identity is editable here. Lifecycle transitions are recorded "
            "through Assurance & Review."
        )

        _ensure_widget_value("project_name_input", "project_name")
        _ensure_widget_value("field_name_input", "field_name")
        _ensure_widget_value("project_phase_input", "project_phase")

        setup_grid = grid(
            [1.5, 1.4, 0.9, 1.0],
            gap="medium",
            vertical_align="top",
        )
        setup_grid.text_input(
            "Project Name",
            key="project_name_input",
            placeholder="e.g. Ledang FDP",
            on_change=_sync_widget_value,
            args=("project_name", "project_name_input"),
        )
        setup_grid.text_input(
            "Field Name",
            key="field_name_input",
            placeholder="e.g. Ledang",
            on_change=_sync_widget_value,
            args=("field_name", "field_name_input"),
        )
        setup_grid.selectbox(
            "Project Phase",
            _PHASES,
            key="project_phase_input",
            on_change=_sync_widget_value,
            args=("project_phase", "project_phase_input"),
        )

        lifecycle_value = lifecycle if lifecycle in LIFECYCLE_ORDER else "Draft"
        ss["study_lifecycle_input"] = lifecycle_value
        setup_grid.selectbox(
            "Study Lifecycle",
            LIFECYCLE_ORDER,
            index=LIFECYCLE_ORDER.index(lifecycle_value),
            key="study_lifecycle_input",
            disabled=True,
            help="Lifecycle transitions are controlled by Assurance & Review.",
        )

        action_grid = grid(
            [1.05, 1.05, 0.85, 2.45],
            gap="small",
            vertical_align="center",
        )
        save_clicked = action_grid.button(
            "Save study",
            key="fp_save",
            type="primary",
            use_container_width=True,
        )
        clear_clicked = action_grid.button(
            "Clear details",
            key="clear_study_details",
            use_container_width=True,
        )
        action_grid.markdown(
            f'<div class="overview-revision"><span>REVISION</span>'
            f'<strong>{html.escape(str(revision))}</strong></div>',
            unsafe_allow_html=True,
        )
        action_grid.caption("Changes remain session drafts until saved.")

        if save_clicked:
            if not ss.get("project_name", "").strip():
                st.warning("Enter a Project Name before saving.")
            elif save_session(auto=False):
                st.success("Study saved.")
            else:
                st.error("Save failed.")

        if clear_clicked:
            for key, widget_key in (
                ("project_name", "project_name_input"),
                ("field_name", "field_name_input"),
                ("project_phase", "project_phase_input"),
            ):
                ss[key] = ""
                ss[widget_key] = ""
            st.rerun()

    # ------------------------------------------------------------------
    # 6. Workflow progress — compact gate map, not a second dashboard.
    # ------------------------------------------------------------------
    with st.container(key="overview-workflow", border=True):
        st.markdown("### Workflow progress")
        st.caption("Seven core gates drive the authoritative completion percentage.")

        workflow_grid = grid(
            4,
            gap="medium",
            vertical_align="top",
        )
        for stage in stages:
            state = (
                "Complete"
                if stage.complete
                else ("Ready" if stage.available else "Locked")
            )
            icon = "✓" if stage.complete else ("•" if stage.available else "—")
            workflow_grid.markdown(
                f"""
                <div class="overview-workflow-item">
                    <div class="overview-workflow-label">
                        <span class="overview-workflow-icon">{icon}</span>
                        <span>{html.escape(stage.label)}</span>
                    </div>
                    <div class="overview-workflow-state">{state}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.progress(progress / 100, text=f"{progress}% complete")

    # ------------------------------------------------------------------
    # 7. Governance & sign-off — explicit checkpoints with a completion count.
    # ------------------------------------------------------------------
    with st.container(key="overview-governance", border=True):
        governance_head = st.columns([1.35, 0.65], gap="medium")
        with governance_head[0]:
            st.markdown("### Governance & sign-off")
            st.caption(
                "Record the responsible person, designation and date for each checkpoint."
            )
        with governance_head[1]:
            st.markdown(
                f"""
                <div class="overview-signoff-summary">
                    <span>SIGN-OFF</span>
                    <strong>{signoff_complete}/{len(signoffs)}</strong>
                    <small>checkpoints recorded</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

        header = st.columns(
            [1.25, 1.35, 1.35, 0.95],
            gap="small",
        )
        header[0].markdown("**CHECKPOINT**")
        header[1].markdown("**NAME**")
        header[2].markdown("**ROLE / DESIGNATION**")
        header[3].markdown("**DATE**")

        for label, key in signoffs:
            cols = st.columns(
                [1.25, 1.35, 1.35, 0.95],
                gap="small",
            )
            cols[0].markdown(
                f'<div class="surm-signoff-checkpoint">'
                f'{html.escape(label)}</div>',
                unsafe_allow_html=True,
            )

            name_widget_key = f"{key}_name_input"
            role_widget_key = f"{key}_role_input"
            date_widget_key = (
                f"{key}_date_picker_{ss.get('study_id', 'new')}"
            )
            _ensure_widget_value(name_widget_key, f"{key}_name")
            _ensure_widget_value(role_widget_key, f"{key}_role")

            with cols[1]:
                st.text_input(
                    "Name",
                    key=name_widget_key,
                    placeholder="Full name",
                    label_visibility="collapsed",
                    on_change=_sync_widget_value,
                    args=(f"{key}_name", name_widget_key),
                )
            with cols[2]:
                st.text_input(
                    "Role",
                    key=role_widget_key,
                    placeholder="Role / designation",
                    label_visibility="collapsed",
                    on_change=_sync_widget_value,
                    args=(f"{key}_role", role_widget_key),
                )
            with cols[3]:
                if date_widget_key not in ss:
                    ss[date_widget_key] = _parse_signoff_date(
                        ss.get(f"{key}_date", "")
                    )
                value = st.date_input(
                    "Date",
                    format="DD/MM/YYYY",
                    key=date_widget_key,
                    label_visibility="collapsed",
                )
                ss[f"{key}_date"] = (
                    value.strftime("%d/%m/%Y") if value else ""
                )

    # ------------------------------------------------------------------
    # 8. Developer controls remain hidden until explicitly requested.
    # ------------------------------------------------------------------
    with st.expander("Developer tools", expanded=False):
        if st.button("Load Demo Data", key="load_demo_data"):
            mapping = ss.get("_mapping", {})
            ulist = mapping.get("uncertainties", [])[:4]
            ss["project_name"] = "DEMO Project"
            ss["field_name"] = "Demo Field"
            ss["key_uncertainties"] = [
                {
                    "Uncertainty": u["name"],
                    "Degree of Uncertainty": "Medium",
                    "Impact (Weighted)": 0.5 + i * 0.1,
                    "Impact Bin": "Medium",
                    "Combined Rating": "HM" if i % 2 == 0 else "MM",
                    "Rank": i,
                    "Include in Plan": True,
                    "Resolution Achieved": False,
                }
                for i, u in enumerate(ulist, start=1)
            ]
            options = mapping.get("resolution_options", [])[:3]
            ss["resolution_list"] = {
                u["name"]: {
                    o: ("Y" if idx == 0 else "")
                    for idx, o in enumerate(options)
                }
                for u in ulist
            }
            ss["resolution_planner"] = []
            ss["risk_register"] = []
            ss["pra_output"] = []
            save_session(auto=True)
            st.success("Demo data loaded.")

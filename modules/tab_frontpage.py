"""SURM report front page: identity, readiness, governance and export."""

from __future__ import annotations

from datetime import date
import html
import streamlit as st

from utils.analytics import build_study_analytics, validation_warnings
from utils.form_ui import render_save_hint
from utils.persistence import save_session
from utils.study_export import snapshot_csv, snapshot_json
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


def _signoff_row(label: str, key: str) -> None:
    st.markdown(f"**{label}**")
    cols = st.columns([1.2, 1.2, 0.85])

    name_widget_key = f"{key}_name_input"
    role_widget_key = f"{key}_role_input"
    date_widget_key = f"{key}_date_picker_{st.session_state.get('study_id', 'new')}"

    _ensure_widget_value(name_widget_key, f"{key}_name")
    _ensure_widget_value(role_widget_key, f"{key}_role")

    with cols[0]:
        st.text_input(
            "Name",
            key=name_widget_key,
            placeholder="Full name",
            label_visibility="collapsed",
            on_change=_sync_widget_value,
            args=(f"{key}_name", name_widget_key),
        )
    with cols[1]:
        st.text_input(
            "Role",
            key=role_widget_key,
            placeholder="Role / designation",
            label_visibility="collapsed",
            on_change=_sync_widget_value,
            args=(f"{key}_role", role_widget_key),
        )
    with cols[2]:
        if date_widget_key not in st.session_state:
            st.session_state[date_widget_key] = _parse_signoff_date(
                st.session_state.get(f"{key}_date", "")
            )
        value = st.date_input(
            "Date",
            format="DD/MM/YYYY",
            key=date_widget_key,
            label_visibility="collapsed",
        )
        st.session_state[f"{key}_date"] = value.strftime("%d/%m/%Y") if value else ""


def render():
    """Render the study dashboard with a clear setup → progress → governance hierarchy."""
    ss = st.session_state
    stages = stage_results(ss)
    progress = round(sum(stage.complete for stage in stages) / len(stages) * 100) if stages else 0
    next_stage = current_stage(ss)
    analytics = build_study_analytics(dict(ss))
    warnings = validation_warnings(dict(ss))

    project = ss.get("project_name") or "Untitled Study"
    field = ss.get("field_name") or "Field not configured"
    phase = ss.get("project_phase") or "Phase not configured"
    lifecycle = ss.get("study_lifecycle", "Draft")

    # ------------------------------------------------------------------
    # 1. Identity banner
    # ------------------------------------------------------------------
    st.markdown(
        f"""
        <div class="overview-cover">
            <div class="overview-cover-kicker">SURM STUDY</div>
            <div class="overview-cover-title">{html.escape(project)}</div>
            <div class="overview-cover-meta">
                {html.escape(field)} · {html.escape(phase)} ·
                Revision {ss.get("study_revision", 0)} · {html.escape(lifecycle)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # 2. Executive glance
    # ------------------------------------------------------------------
    st.markdown('<div class="surm-overview-section-label">AT A GLANCE</div>', unsafe_allow_html=True)
    metric_cols = st.columns(4)
    metric_cols[0].metric(
        "Study progress",
        f"{progress}%",
        help="Completion is based on the authoritative workflow gates.",
    )
    metric_cols[1].metric(
        "Uncertainties",
        sum(1 for x in ss.get("uncertainties", []) if isinstance(x, dict) and x.get("selected")),
    )
    metric_cols[2].metric("Resolution actions", len(ss.get("resolution_planner", [])))
    metric_cols[3].metric("Risks", len(ss.get("risk_register", [])))

    # ------------------------------------------------------------------
    # 3. Next best action + current signal
    # ------------------------------------------------------------------
    left, right = st.columns([1.25, 1], gap="large")

    with left:
        with st.container(border=True):
            st.markdown('<div class="surm-panel-kicker">NEXT ACTION</div>', unsafe_allow_html=True)
            if next_stage.complete:
                st.success("Core workflow complete.")
                st.write("Review the PRA Output and confirm the study is ready for governance.")
                if st.button(
                    "Review PRA Output →",
                    key="overview_continue",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state["current_page"] = "📄 PRA Output"
                    st.rerun()
            else:
                st.markdown(f"### Continue with {next_stage.label}")
                st.write(next_stage.guidance)
                if st.button(
                    f"Continue to {next_stage.label.split(' ', 1)[-1]} →",
                    key="overview_continue",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state["current_page"] = next_stage.label
                    st.rerun()

            if warnings:
                st.markdown("#### Needs attention")
                for warning in warnings[:3]:
                    st.warning(warning["message"])

    with right:
        with st.container(border=True):
            st.markdown('<div class="surm-panel-kicker">CURRENT SIGNAL</div>', unsafe_allow_html=True)
            critical = analytics.get("critical_uncertainties", [])
            if critical:
                for item in critical[:4]:
                    st.markdown(f"• {item}")
            else:
                st.caption("No ranked key uncertainties yet.")
            st.progress(progress / 100, text=f"{progress}% of core workflow complete")

    # ------------------------------------------------------------------
    # 4. Study setup — the first data-entry destination on a new study.
    # ------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("### Study setup")
        render_save_hint(
            "Identity and governance fields are session drafts. Save the study when the details are ready to persist."
        )

        c1, c2, c3 = st.columns([1.15, 1.15, 0.8], gap="medium")
        _ensure_widget_value("project_name_input", "project_name")
        _ensure_widget_value("field_name_input", "field_name")
        _ensure_widget_value("project_phase_input", "project_phase")

        with c1:
            st.text_input(
                "Project Name",
                key="project_name_input",
                placeholder="e.g. Ledang FDP",
                on_change=_sync_widget_value,
                args=("project_name", "project_name_input"),
            )
        with c2:
            st.text_input(
                "Field Name",
                key="field_name_input",
                placeholder="e.g. Ledang",
                on_change=_sync_widget_value,
                args=("field_name", "field_name_input"),
            )
        with c3:
            st.selectbox(
                "Project Phase",
                _PHASES,
                key="project_phase_input",
                on_change=_sync_widget_value,
                args=("project_phase", "project_phase_input"),
            )

        save_col, clear_col, _ = st.columns([1.15, 1.1, 3.75])
        with save_col:
            if st.button("Save study", type="primary", key="fp_save", use_container_width=True):
                if not ss.get("project_name", "").strip():
                    st.warning("Enter a Project Name before saving.")
                elif save_session(auto=False):
                    st.success("Saved.")
                else:
                    st.error("Save failed.")
        with clear_col:
            if st.button("Clear details", key="clear_study_details", use_container_width=True):
                for key, widget_key in (
                    ("project_name", "project_name_input"),
                    ("field_name", "field_name_input"),
                    ("project_phase", "project_phase_input"),
                ):
                    ss[key] = ""
                    ss[widget_key] = ""
                st.rerun()

    # ------------------------------------------------------------------
    # 5. Workflow progress
    # ------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("### Workflow progress")
        st.caption("The sequence below mirrors the authoritative workflow gates.")

        for row_start in range(0, len(stages), 4):
            row_cols = st.columns(4, gap="medium")
            for col, stage in zip(row_cols, stages[row_start:row_start + 4]):
                state = "Complete" if stage.complete else ("Ready" if stage.available else "Locked")
                icon = "✓" if stage.complete else ("•" if stage.available else "🔒")
                col.markdown(f"**{icon} {stage.label}**")
                col.caption(state)

        st.progress(progress / 100, text=f"{progress}% complete")

    # ------------------------------------------------------------------
    # 6. Governance and sign-off are secondary until the study is ready.
    # ------------------------------------------------------------------
    with st.expander("Governance & sign-off", expanded=False):
        st.markdown("### Governance")
        render_save_hint(
            "Lifecycle and sign-off fields remain session drafts until you save the study."
        )
        life_col, rev_col = st.columns([1.1, 2], gap="large")
        with life_col:
            _ensure_widget_value("study_lifecycle_input", "study_lifecycle")
            st.selectbox(
                "Study lifecycle",
                ["Draft", "In Review", "Reviewed", "Approved", "Archived"],
                key="study_lifecycle_input",
                on_change=_sync_widget_value,
                args=("study_lifecycle", "study_lifecycle_input"),
            )
            st.caption(f"Revision {ss.get('study_revision', 0)}")

        with rev_col:
            st.caption("Sign-off")
            signoffs = [
                ("Prepared By", "prep"),
                ("Reviewed By — G&G", "rev_gg"),
                ("Reviewed By — RE", "rev_re"),
                ("Reviewed By — PP", "rev_pp"),
                ("Endorsed By — FDP Lead", "endorsed"),
            ]
            for label, key in signoffs:
                _signoff_row(label, key)

    # ------------------------------------------------------------------
    # 7. Developer controls remain hidden until explicitly requested.
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
                u["name"]: {o: ("Y" if idx == 0 else "") for idx, o in enumerate(options)}
                for u in ulist
            }
            ss["resolution_planner"] = []
            ss["risk_register"] = []
            ss["pra_output"] = []
            save_session(auto=True)
            st.success("Demo data loaded.")

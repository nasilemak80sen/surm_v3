"""SURM report front page: identity, readiness, governance and export."""

from __future__ import annotations

from datetime import date
import streamlit as st

from utils.analytics import build_study_analytics, validation_warnings
from utils.form_ui import render_save_hint
from utils.export_excel import build_excel_export
from utils.persistence import delete_session, list_sessions, load_session_record, save_session
from utils.session import create_new_study
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
    ss = st.session_state
    stages = stage_results(ss)
    progress = round(sum(stage.complete for stage in stages) / len(stages) * 100) if stages else 0
    next_stage = current_stage(ss)
    analytics = build_study_analytics(dict(ss))

    for warning in validation_warnings(dict(ss))[:2]:
        st.warning(warning["message"])

    project = ss.get("project_name") or "Untitled Study"
    field = ss.get("field_name") or "Field not configured"
    phase = ss.get("project_phase") or "Phase not configured"
    lifecycle = ss.get("study_lifecycle", "Draft")

    st.markdown(
        f"""
        <div class="overview-cover">
            <div class="overview-cover-kicker">SURM STUDY REPORT</div>
            <div class="overview-cover-title">{project}</div>
            <div class="overview-cover-meta">{field} · {phase} · Revision {ss.get("study_revision", 0)} · {lifecycle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Study progress", f"{progress}%")
    metric_cols[1].metric("Uncertainties", sum(1 for x in ss.get("uncertainties", []) if isinstance(x, dict) and x.get("selected")))
    metric_cols[2].metric("Resolution actions", len(ss.get("resolution_planner", [])))
    metric_cols[3].metric("Risks", len(ss.get("risk_register", [])))

    left, right = st.columns([1.45, 1], gap="large")
    with left:
        st.markdown("### Study identity")
        render_save_hint(
            "Study identity and governance inputs are session drafts until you click Save study. "
            "Exports reflect the current session draft; they do not persist it to the saved study."
        )
        c1, c2, c3 = st.columns(3)

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

        save_col, clear_col, _ = st.columns([1.2, 1.1, 3])
        with save_col:
            if st.button("Save study", type="primary", key="fp_save"):
                if not ss.get("project_name", "").strip():
                    st.warning("Enter a Project Name before saving.")
                elif save_session(auto=False):
                    st.success("Saved.")
                else:
                    st.error("Save failed.")
        with clear_col:
            if st.button("Clear details", key="clear_study_details"):
                ss["project_name"] = ""
                ss["field_name"] = ""
                ss["project_phase"] = ""
                ss["project_name_input"] = ""
                ss["field_name_input"] = ""
                ss["project_phase_input"] = ""
                st.rerun()

    with right:
        st.markdown("### What needs attention")
        if next_stage.complete:
            st.success("Workflow complete. Review PRA Output.")
        else:
            st.warning(f"Next: **{next_stage.label}**")
            st.caption(next_stage.guidance)
        st.progress(progress / 100)
        st.caption("Progress follows the authoritative workflow gates, not manual page visits.")

        st.markdown("### Current signal")
        critical = analytics.get("critical_uncertainties", [])
        if critical:
            st.write(" · ".join(critical[:4]))
        else:
            st.caption("No ranked key uncertainties yet.")

    st.markdown("### Workflow at a glance")
    flow_cols = st.columns(4)
    for index, stage in enumerate(stages):
        col = flow_cols[index % 4]
        state = "✓" if stage.complete else ("•" if stage.available else "—")
        col.markdown(f"**{state} {stage.label}**")
        col.caption("Complete" if stage.complete else ("Ready" if stage.available else "Locked"))

    st.markdown("### Governance")
    render_save_hint(
        "Lifecycle and sign-off fields are also session drafts. Use Save study above to persist the complete front-page record."
    )
    life_col, rev_col = st.columns([1.2, 2])
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

    export_col, session_col = st.columns([1, 1], gap="large")
    with export_col:
        st.markdown("### Export")
        field_name = ss.get("field_name") or "Output"
        st.download_button(
            "Download SURM workbook",
            data=build_excel_export(),
            file_name=f"SURM_{field_name.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.download_button(
            "Download study JSON",
            data=snapshot_json(dict(ss)),
            file_name=f"SURM_{project.replace(' ', '_')}.json",
            mime="application/json",
            use_container_width=True,
        )
        st.download_button(
            "Download relationships CSV",
            data=snapshot_csv(dict(ss)),
            file_name=f"SURM_{project.replace(' ', '_')}_relationships.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with session_col:
        st.markdown("### Saved studies")
        sessions = list_sessions()
        if not sessions:
            st.caption("No saved studies yet.")
            if st.button("Create new study", type="secondary", key="overview_create_new_session"):
                create_new_study()
                st.rerun()
        else:
            for session_index, saved in enumerate(sessions[:8]):
                label = f'{saved.get("project_name", "Unnamed")} · {saved.get("field_name", "Unknown")}'
                meta = f'{saved.get("phase", "—")} · {saved.get("completion", 0)}%'
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.caption(label)
                    st.caption(meta)
                with c2:
                    if st.button("Load", key=f"load_saved_study_{session_index}"):
                        if load_session_record(saved):
                            st.rerun()
                        else:
                            st.error("Load failed.")
                with c3:
                    if st.button("Delete", key=f"delete_saved_study_{session_index}"):
                        delete_session(saved.get("project_name", ""), saved.get("field_name", ""))
                        st.rerun()

    with st.expander("Developer Tools", expanded=False):
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

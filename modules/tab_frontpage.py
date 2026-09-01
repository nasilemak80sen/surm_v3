"""modules/tab_frontpage.py — Project info, sign-off, session manager"""
import streamlit as st
from datetime import date
from utils.export_excel import build_excel_export
from utils.persistence import save_session, list_sessions, load_session_record, delete_session
from utils.session import create_new_study
from components.metrics import render_metric_grid, render_progress_card
from components.cards import render_card
from utils.study_export import snapshot_csv, snapshot_json
from utils.analytics import build_study_analytics, validation_warnings

_PHASES = ["","PGR0","PGR1","PGR2","PGR3/FID","ITR2a","ITR2b","SBS","SIR2a","SIR2b","PGR4"]


def _parse_signoff_date(value: str) -> date | None:
    """Convert the persisted DD/MM/YYYY value for Streamlit's date picker."""
    if not value:
        return None
    try:
        day, month, year = (int(part) for part in value.split("/"))
        return date(year, month, day)
    except (TypeError, ValueError):
        return None

def render():
    ss = st.session_state
    selected_uncertainties = sum(
        1 for item in ss.get("uncertainties", [])
        if isinstance(item, dict) and item.get("selected")
    )
    key_decisions = sum(
        1 for item in ss.get("key_decisions", [])
        if isinstance(item, dict) and str(item.get("Key Decision", "")).strip()
    )
    resolution_actions = len(ss.get("resolution_planner", []))
    risks = len(ss.get("risk_register", []))
    checks = [
        bool(str(ss.get("project_name", "")).strip()),
        selected_uncertainties > 0,
        key_decisions > 0,
        bool(ss.get("impact_assessment")),
        bool(ss.get("key_uncertainties")),
        bool(ss.get("resolution_list")),
        resolution_actions > 0,
        risks > 0,
    ]
    progress = round(sum(checks) / len(checks) * 100) if checks else 0
    workflow_pages = [
        ("1️⃣ Uncertainties", selected_uncertainties > 0),
        ("2️⃣ Key Decisions", key_decisions > 0),
        ("3️⃣ Impact Assessment", bool(ss.get("impact_assessment"))),
        ("4️⃣ Key Uncertainties", bool(ss.get("key_uncertainties"))),
        ("5️⃣ Resolution List", bool(ss.get("resolution_list"))),
        ("6️⃣ Resolution Planner", resolution_actions > 0),
        ("7️⃣ Risk Register", risks > 0),
    ]
    next_step = next((label for label, complete in workflow_pages if not complete), "📄 PRA Output")
    analytics = build_study_analytics(dict(ss))
    for warning in validation_warnings(dict(ss))[:5]:
        st.warning(warning["message"])

    render_metric_grid([
        {"title": "Uncertainties", "value": selected_uncertainties, "description": "Selected for study", "variant": "primary"},
        {"title": "Key Decisions", "value": key_decisions, "description": "Decision drivers"},
        {"title": "Resolution Actions", "value": resolution_actions, "description": "In the workplan"},
        {"title": "Risks", "value": risks, "description": "In the register", "variant": "warning"},
    ])
    render_progress_card("Study Progress", progress, description="Completion across the eight core study stages.")
    context_col, next_col = st.columns([1.35, 1], gap="large")
    with context_col:
        render_card(
            "Current Study",
            "Active context for this workspace and its exports.",
            content=(
                f'<div class="overview-context-grid">'
                f'<div><span>Field</span><strong>{ss.get("field_name") or "Not configured"}</strong></div>'
                f'<div><span>Project</span><strong>{ss.get("project_name") or "Not configured"}</strong></div>'
                f'<div><span>Phase</span><strong>{ss.get("project_phase") or "Not configured"}</strong></div>'
                f'</div>'
            ),
            variant="info",
        )
    with next_col:
        render_card(
            "Next Step",
            f"Continue with {next_step}.",
            content='<div class="overview-next-step">Keep stages in order to keep downstream outputs current.</div>',
            variant="success",
        )
    critical_items = analytics["critical_uncertainties"] or ["No ranked uncertainties yet"]
    critical_col, status_col = st.columns([1.35, 1], gap="large")
    with critical_col:
        render_card(
            "Critical Uncertainties",
            "Highest-ranked items currently carried into the study plan.",
            content="<ol class=\"overview-critical-list\">" + "".join(
                f"<li>{item}</li>" for item in critical_items
            ) + "</ol>",
            variant="warning",
        )
    status_text = " · ".join(
        f"{status}: {count}" for status, count in analytics["resolution_status"].items()
    ) or "No resolution actions recorded yet"
    with status_col:
        render_card(
            "Resolution Status",
            status_text,
            content="Derived from the current study records.",
            variant="info",
        )
    affected_decisions = sorted({
        item["target"] for item in analytics["relationships"]
        if item["type"] == "affects"
    })
    render_card(
        "Decision Trace",
        "Recorded uncertainty-to-decision links.",
        content=(
            "<div class=\"overview-next-step\">"
            + (" · ".join(affected_decisions) if affected_decisions else "No high or medium impact decision links recorded yet")
            + "</div>"
        ),
        variant="info",
    )

    st.markdown('<div class="surm-section-header">Study Governance</div>', unsafe_allow_html=True)
    gov_col, export_col = st.columns([2, 1])
    with gov_col:
        st.selectbox(
            "Study lifecycle",
            ["Draft", "In Review", "Reviewed", "Approved", "Archived"],
            key="study_lifecycle",
            help="Governance state for this study output.",
        )
        st.caption(f"Revision {ss.get('study_revision', 0)}. Save the study to create an immutable revision snapshot.")
    with export_col:
        st.download_button(
            "Download Study JSON",
            data=snapshot_json(dict(ss)),
            file_name=f"SURM_{(ss.get('project_name') or 'Study').replace(' ', '_')}.json",
            mime="application/json",
            use_container_width=True,
        )
        st.download_button(
            "Download Relationships CSV",
            data=snapshot_csv(dict(ss)),
            file_name=f"SURM_{(ss.get('project_name') or 'Study').replace(' ', '_')}_relationships.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.info("Start with project details, then complete the workflow from Uncertainties through PRA Output. Save before loading another study.")

    # ── Saved sessions panel ─────────────────────────────────────────
    sessions = list_sessions()
    if sessions:
        st.markdown('<div class="surm-section-header">📂 Saved Sessions</div>', unsafe_allow_html=True)
        st.info("Choose Load to restore a saved study. Any current unsaved changes will be replaced.")

        for session_index, s in enumerate(sessions):
            pct         = s["completion"]
            bar_clr     = "#1F6B3A" if pct >= 80 else "#FFD700" if pct >= 40 else "#FF8C00"
            ts          = s["saved_at"].replace("T", " ")[:16] if s["saved_at"] else "—"
            auto_tag    = ' <span style="font-size:9px;background:#E8F5E9;color:#1F6B3A;padding:1px 5px;border-radius:8px;">auto</span>' if s["auto_saved"] else ""

            col_info, col_pbar, col_load, col_del = st.columns([4, 3, 1, 1])
            with col_info:
                st.markdown(f"""
                    <div style="padding:6px 0;">
                        <div style="font-size:13px;font-weight:700;">{s['project_name']}</div>
                        <div style="font-size:11px;color:#888;">{s['field_name']} &nbsp;·&nbsp; {s['phase']} &nbsp;·&nbsp; Saved: {ts}{auto_tag}</div>
                    </div>
                """, unsafe_allow_html=True)
            with col_pbar:
                st.markdown(f"""
                    <div style="padding:10px 0 0 0;">
                        <div style="background:#E8E8E8;border-radius:4px;height:8px;">
                            <div style="width:{pct}%;background:{bar_clr};height:8px;border-radius:4px;"></div>
                        </div>
                        <div style="font-size:10px;color:#888;margin-top:2px;">{pct}% complete</div>
                    </div>
                """, unsafe_allow_html=True)
            with col_load:
                if st.button("📂 Load", key=f"load_saved_study_{session_index}"):
                    ok = load_session_record(s)
                    if ok:
                        st.success(f"Loaded: {s['project_name']}")
                        st.session_state["_resume_attempted"] = True
                        st.rerun()
                    else:
                        st.error("Load failed.")
            with col_del:
                if st.button("🗑️", key=f"delete_saved_study_{session_index}", help="Delete this saved study"):
                    delete_session(s["project_name"], s["field_name"])
                    st.rerun()

        st.divider()
    else:
        st.markdown('<div class="surm-section-header">📂 Saved Sessions</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.info("No saved sessions yet. Create a new session, complete the study, and save it here.")
            if st.button("＋ Create New Session", key="overview_create_new_session", type="primary"):
                create_new_study()
                st.rerun()

    # Developer helper: load demo data for testing flows (not shown in production)
    with st.expander("Developer Tools", expanded=False):
        if st.button("🔁 Load Demo Data", key="load_demo_data"):
            # minimal demo dataset to exercise Tab 5/6/7 flows
            demo_project = "DEMO Project"
            st.session_state["project_name"] = demo_project
            st.session_state["field_name"] = "Demo Field"
            # pick first 4 uncertainties from master mapping
            mapping = st.session_state.get("_mapping", {})
            ulist = mapping.get("uncertainties", [])[:4]
            ku = []
            for i, u in enumerate(ulist, start=1):
                ku.append({
                    "Uncertainty": u["name"],
                    "Degree of Uncertainty": "Medium",
                    "Impact (Weighted)": 0.5 + i*0.1,
                    "Impact Bin": "Medium",
                    "Combined Rating": "HM" if i%2==0 else "MM",
                    "Rank": i,
                    "Include in Plan": True,
                    "Resolution Achieved": False,
                })
            st.session_state["key_uncertainties"] = ku
            # build a simple resolution_list mapping using first two resolution options
            opts = mapping.get("resolution_options", [])[:3]
            rl = {u["name"]: {o: ("Y" if idx==0 else "") for idx,o in enumerate(opts)} for u in ulist}
            st.session_state["resolution_list"] = rl
            st.session_state["resolution_planner"] = []
            st.session_state["risk_register"] = []
            st.session_state["pra_output"] = []
            save_session(auto=True)
            st.success("Demo data loaded. Navigate to Tab 5 → Tab 6 → Tab 7 to test flows.")

    # ── Project info ─────────────────────────────────────────────────
    st.markdown('<div class="surm-section-header">📋 Project Information</div>', unsafe_allow_html=True)
    st.info("Enter the field, project, and phase first. These details identify the study and appear in exported reports.")

    st.session_state.setdefault("project_name", "")
    st.session_state.setdefault("field_name", "")
    st.session_state.setdefault("project_phase", "")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input(
            "Project Name",
            key="project_name",
            placeholder="e.g. Ledang FDP",
            help="Used as the saved session identifier")
    with c2:
        st.text_input(
            "Field Name",
            key="field_name",
            placeholder="e.g. Ledang")
    with c3:
        st.selectbox("Project Phase", _PHASES, key="project_phase")

    clear_col, _ = st.columns([1, 4])
    with clear_col:
        if st.button("Clear Study Details", key="clear_study_details"):
            st.session_state["project_name"] = ""
            st.session_state["field_name"] = ""
            st.session_state["project_phase"] = ""
            st.rerun()

    # ── Manual save on this page too ──────────────────────────────────
    col_save, col_hint = st.columns([1, 4])
    with col_save:
        save_clicked = st.button("💾 Save Session", type="primary", key="fp_save")
        if save_clicked:
            if not st.session_state.get("project_name", "").strip():
                st.warning("Enter a Project Name before saving.")
            else:
                ok = save_session(auto=False)
                st.success("✅ Session saved!") if ok else st.error("Save failed.")
    with col_hint:
        st.markdown('<div class="help-text" style="padding-top:10px;">Sessions are saved to the <code>sessions/</code> folder in the app directory. One file per project name — saving again overwrites it.</div>', unsafe_allow_html=True)

    # ── Sign-off ──────────────────────────────────────────────────────
    st.markdown('<div class="surm-section-header">✍️ Sign-Off Panel</div>', unsafe_allow_html=True)
    st.markdown('<div class="surm-instruction">ℹ️ Fill in name, role and date for each signatory.</div>', unsafe_allow_html=True)

    signoffs = [
        ("Prepared By",           "prep"),
        ("Reviewed By — G&G",     "rev_gg"),
        ("Reviewed By — RE",      "rev_re"),
        ("Reviewed By — PP",      "rev_pp"),
        ("Endorsed By (FDP Lead)","endorsed"),
    ]

    for label, key in signoffs:
        with st.expander(label, expanded=False):
            st.markdown('<div class="signoff-box">', unsafe_allow_html=True)
            st.text_input(
                "Name", key=f"{key}_name",
                placeholder="Full name", label_visibility="collapsed")
            st.text_input(
                "Role", key=f"{key}_role",
                placeholder="Designation", label_visibility="collapsed")
            date_value = st.date_input(
                "Date",
                value=_parse_signoff_date(ss.get(f"{key}_date", "")),
                format="DD/MM/YYYY",
                key=f"{key}_date_picker_{ss.get('study_id', 'new')}",
                label_visibility="collapsed",
                help="Choose a date from the calendar or type it directly as DD/MM/YYYY.",
            )
            ss[f"{key}_date"] = date_value.strftime("%d/%m/%Y") if date_value else ""
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Export ────────────────────────────────────────────────────────
    st.markdown('<div class="surm-section-header">📥 Export Full SURM Workbook</div>', unsafe_allow_html=True)
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        xlsx  = build_excel_export()
        field = st.session_state.get("field_name","") or "Output"
        st.download_button("📥 Download SURM (.xlsx)", data=xlsx,
            file_name=f"SURM_{field.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col_info:
        st.markdown("""<div style="background:#E8F5E9;border-left:4px solid #1F6B3A;padding:10px 14px;
            border-radius:0 4px 4px 0;font-size:12px;color:#2E7D32;margin-top:4px;">
            📄 Exports all 9 sheets in styled Excel format.</div>""", unsafe_allow_html=True)

    # ── Study at a glance ─────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="surm-section-header">📊 Study at a Glance</div>', unsafe_allow_html=True)
    ss = st.session_state
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Uncertainties Selected", sum(1 for u in ss.get("uncertainties",[]) if u.get("selected")))
    m2.metric("Key Uncertainties",       len([r for r in ss.get("key_uncertainties",[]) if r.get("Include in Plan")]))
    m3.metric("High Priority (HH/HM)",   sum(1 for r in ss.get("key_uncertainties",[]) if r.get("Combined Rating","") in ("HH","HM","MH")))
    m4.metric("Resolution Actions",       len(ss.get("resolution_planner",[])))
    m5.metric("Risks Identified",         len(ss.get("risk_register",[])))

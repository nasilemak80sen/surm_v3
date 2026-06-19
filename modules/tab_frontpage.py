"""modules/tab_frontpage.py — Project info, sign-off, session manager"""
import streamlit as st
from utils.export_excel import build_excel_export
from utils.persistence import save_session, list_sessions, load_session, delete_session

_PHASES = ["","PGR0","PGR1","PGR2","PGR3/FID","ITR2a","ITR2b","SBS","SIR2a","SIR2b","PGR4"]

def render():
    # ── Saved sessions panel ─────────────────────────────────────────
    sessions = list_sessions()
    if sessions:
        st.markdown('<div class="surm-section-header">📂 Resume a Saved Session</div>', unsafe_allow_html=True)
        st.markdown('<div class="surm-instruction">ℹ️ Click <b>Load</b> to restore a previously saved study. Your current unsaved work will be replaced.</div>', unsafe_allow_html=True)

        for s in sessions:
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
                if st.button("📂 Load", key=f"load_{s['filename']}"):
                    ok = load_session(s["filepath"])
                    if ok:
                        st.success(f"Loaded: {s['project_name']}")
                        st.rerun()
                    else:
                        st.error("Load failed.")
            with col_del:
                if st.button("🗑️", key=f"del_{s['filename']}", help="Delete this saved session"):
                    delete_session(s["filepath"])
                    st.rerun()

        st.divider()

    # ── Project info ─────────────────────────────────────────────────
    st.markdown('<div class="surm-section-header">📋 Project Information</div>', unsafe_allow_html=True)
    st.markdown('<div class="surm-instruction">ℹ️ Fill in the project details. These appear on the exported Excel cover page and identify your saved session.</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.session_state["project_name"] = st.text_input(
            "Project Name", value=st.session_state.get("project_name",""),
            placeholder="e.g. Ledang FDP",
            help="Used as the saved session identifier")
    with c2:
        st.session_state["field_name"] = st.text_input(
            "Field Name", value=st.session_state.get("field_name",""),
            placeholder="e.g. Ledang")
    with c3:
        cur_phase = st.session_state.get("project_phase","")
        idx = _PHASES.index(cur_phase) if cur_phase in _PHASES else 0
        st.session_state["project_phase"] = st.selectbox("Project Phase", _PHASES, index=idx)

    # ── Manual save on this page too ──────────────────────────────────
    col_save, col_hint = st.columns([1, 4])
    with col_save:
        if st.button("💾 Save Session", type="primary", key="fp_save"):
            if not st.session_state.get("project_name","").strip():
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
    cols = st.columns(5)
    for col, (label, key) in zip(cols, signoffs):
        with col:
            st.markdown(f'<div class="signoff-box"><div class="signoff-label">{label}</div>', unsafe_allow_html=True)
            st.session_state[f"{key}_name"] = st.text_input("Name",  key=f"si_{key}_n", value=st.session_state.get(f"{key}_name",""), placeholder="Full name",    label_visibility="collapsed")
            st.session_state[f"{key}_role"] = st.text_input("Role",  key=f"si_{key}_r", value=st.session_state.get(f"{key}_role",""), placeholder="Designation", label_visibility="collapsed")
            st.session_state[f"{key}_date"] = st.text_input("Date",  key=f"si_{key}_d", value=st.session_state.get(f"{key}_date",""), placeholder="DD/MM/YYYY",  label_visibility="collapsed")
            st.markdown("</div>", unsafe_allow_html=True)

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

"""modules/tab_documentation.py — Team roster"""
import streamlit as st
import pandas as pd
from utils.persistence import save_session

def render():
    st.markdown('<div class="surm-instruction">ℹ️ Record all team members who contributed to this SURM. This will appear in the Excel export documentation sheet.</div>', unsafe_allow_html=True)
    st.markdown('<div class="surm-section-header">👥 Team Members</div>', unsafe_allow_html=True)

    df = pd.DataFrame(st.session_state.get("team_members", [{"Name":"","Function / Role":"","Date":""}]))

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "Name":             st.column_config.TextColumn("Name", width="medium"),
            "Function / Role":  st.column_config.SelectboxColumn("Function / Role", width="medium",
                options=["","ES","PE","RE","G&G","PT","PP","FE","D&C","FDP Lead","Other"]),
            "Date":             st.column_config.TextColumn("Date (DD/MM/YYYY)", width="small"),
        },
        hide_index=True,
        key="team_editor",
    )
    # sanitize and persist team members: strip whitespace, remove empty rows
    raw = edited.to_dict("records")
    cleaned = []
    for r in raw:
        name = (r.get("Name") or "").strip()
        role = (r.get("Function / Role") or "").strip()
        date = (r.get("Date (DD/MM/YYYY)") or r.get("Date") or "").strip()
        if not name and not role and not date:
            continue
        cleaned.append({"Name": name, "Function / Role": role, "Date": date})

    st.session_state["team_members"] = cleaned or [{"Name": "", "Function / Role": "", "Date": ""}]
    st.metric("Team Size", len([r for r in cleaned if (r.get("Name") or "").strip()]))

    # Per-tab save button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Save Team", key="save_team"):
            if not st.session_state.get("project_name", "").strip():
                st.warning("Enter a Project Name before saving.")
            else:
                ok = save_session(auto=False)
                if ok:
                    st.success("✅ Team saved.")
                else:
                    st.error("Save failed.")
    with col2:
        st.write("")

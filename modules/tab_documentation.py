"""modules/tab_documentation.py — Team roster"""
import streamlit as st
import pandas as pd

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
    st.session_state["team_members"] = edited.to_dict("records")
    st.metric("Team Size", len([r for r in edited.to_dict("records") if (r.get("Name") or "").strip()]))

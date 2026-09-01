"""modules/tab_documentation.py — Team roster"""
import streamlit as st
import pandas as pd
from utils.persistence import save_session

def render():
    st.info("Add the people involved in this study. Their names and roles will appear in the exported documentation.")
    st.markdown('<div class="surm-section-header">👥 Team Members</div>', unsafe_allow_html=True)

    rows = st.session_state.get("team_members", [{"Name":"","Function / Role":"","Date":""}])
    df = pd.DataFrame(rows)
    if "Date (DD/MM/YYYY)" not in df.columns:
        df["Date (DD/MM/YYYY)"] = df.pop("Date") if "Date" in df.columns else ""

    editor_key = f"team_editor_{st.session_state.get('study_id', 'new')}"
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "Name":             st.column_config.TextColumn("Name", width="medium"),
            "Function / Role":  st.column_config.SelectboxColumn("Function / Role", width="medium",
                options=["","ES","PE","RE","G&G","PT","PP","FE","D&C","FDP Lead","Other"]),
            "Date (DD/MM/YYYY)": st.column_config.TextColumn("Date (DD/MM/YYYY)", width="small"),
        },
        hide_index=True,
        key=editor_key,
    )
    # Keep the editor's rows intact. Removing blank rows during render causes
    # Streamlit to reconcile the widget with stale data on the next rerun.
    raw = edited.to_dict("records")
    st.session_state["team_members"] = [
        {
            "Name": str(row.get("Name") or "").strip(),
            "Function / Role": str(row.get("Function / Role") or "").strip(),
            "Date": str(row.get("Date (DD/MM/YYYY)") or "").strip(),
        }
        for row in raw
    ] or [{"Name": "", "Function / Role": "", "Date": ""}]
    st.metric("Team Size", len([r for r in raw if str(r.get("Name") or "").strip()]))

    if st.button("Remove Empty Team Rows", key="remove_empty_team_rows"):
        st.session_state["team_members"] = [
            row for row in st.session_state["team_members"]
            if any(str(value).strip() for value in row.values())
        ] or [{"Name": "", "Function / Role": "", "Date": ""}]
        st.rerun()
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

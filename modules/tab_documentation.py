"""modules/tab_documentation.py — Team roster."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.form_ui import render_form_header
from utils.persistence import save_session


def render():
    render_form_header(
        "STUDY GOVERNANCE",
        "Team",
        "Record the people and roles contributing to the study. These details become part of the exported documentation.",
        next_step="Uncertainties",
    )

    rows = st.session_state.get(
        "team_members",
        [{"Name": "", "Function / Role": "", "Date": ""}],
    )
    df = pd.DataFrame(rows)
    if "Date (DD/MM/YYYY)" not in df.columns:
        df["Date (DD/MM/YYYY)"] = df.pop("Date") if "Date" in df.columns else ""

    edited = st.data_editor(
        df,
        num_rows="dynamic",
                use_container_width=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", width="medium"),
            "Function / Role": st.column_config.SelectboxColumn(
                "Function / Role",
                width="medium",
                options=["", "ES", "PE", "RE", "G&G", "PT", "PP", "FE", "D&C", "FDP Lead", "Other"],
            ),
            "Date (DD/MM/YYYY)": st.column_config.TextColumn(
                "Date (DD/MM/YYYY)",
                width="small",
            ),
        },
        hide_index=True,
        key=f"team_editor_{st.session_state.get('study_id', 'new')}",
    )

    raw = edited.to_dict("records")
    st.session_state["team_members"] = [
        {
            "Name": str(row.get("Name") or "").strip(),
            "Function / Role": str(row.get("Function / Role") or "").strip(),
            "Date": str(row.get("Date (DD/MM/YYYY)") or "").strip(),
        }
        for row in raw
    ] or [{"Name": "", "Function / Role": "", "Date": ""}]

    left, right = st.columns([1, 3], gap="large")
    with left:
        st.metric("Team size", len([r for r in raw if str(r.get("Name") or "").strip()]))
    with right:
        save_col, clean_col = st.columns(2)
        with save_col:
            if st.button("Save team", type="primary", key="save_team"):
                if not st.session_state.get("project_name", "").strip():
                    st.warning("Enter a Project Name on Overview first.")
                elif save_session(auto=False):
                    st.success("Saved.")
                else:
                    st.error("Save failed.")
        with clean_col:
            if st.button("Remove empty rows", key="remove_empty_team_rows"):
                st.session_state["team_members"] = [
                    row for row in st.session_state["team_members"]
                    if any(str(value).strip() for value in row.values())
                ] or [{"Name": "", "Function / Role": "", "Date": ""}]
                st.rerun()

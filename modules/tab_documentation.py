"""modules/tab_documentation.py — Team roster."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.form_ui import render_form_header, render_save_hint
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

    render_save_hint(
        "Edits are staged in this form until you submit them. "
        "Save team persists the roster; Remove empty rows only changes the current session draft."
    )

    with st.form("team_form", enter_to_submit=False):
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
        save_clicked = st.form_submit_button("Save team", type="primary", key="save_team")
        clean_clicked = st.form_submit_button("Remove empty rows", key="remove_empty_team_rows")

    if save_clicked or clean_clicked:
        raw = edited.to_dict("records")
        if clean_clicked:
            raw = [
                row for row in raw
                if any(str(value or "").strip() for value in row.values())
            ]

        st.session_state["team_members"] = [
            {
                "Name": str(row.get("Name") or "").strip(),
                "Function / Role": str(row.get("Function / Role") or "").strip(),
                "Date": str(row.get("Date (DD/MM/YYYY)") or "").strip(),
            }
            for row in raw
        ] or [{"Name": "", "Function / Role": "", "Date": ""}]

        if save_clicked:
            if not st.session_state.get("project_name", "").strip():
                st.warning("Enter a Project Name on Overview before saving the team roster.")
                return
            if not save_session(auto=False):
                st.error("Team roster could not be saved.")
                return
            st.success("✅ Team roster saved.")
        else:
            st.info("Draft updated. Click **Save team** to persist the roster.")
        st.rerun()

    raw = st.session_state.get("team_members", [])

"""modules/tab_documentation.py — Team roster."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.form_ui import render_form_header, render_save_hint
from utils.persistence import save_session


TEAM_ROLE_OPTIONS = [
    "",
    "ES",
    "PE",
    "RE",
    "G&G",
    "PT",
    "PP",
    "FE",
    "D&C",
    "FDP Lead",
    "Other",
]


def _team_date_value(value: object) -> date | None:
    """Convert stored roster dates to values accepted by DateColumn."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None
    for date_format in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid team date {text!r}; expected DD/MM/YYYY.")


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
    date_column = "Date (DD/MM/YYYY)"
    if date_column in df.columns:
        date_values = df[date_column]
    else:
        date_values = (
            df["Date"]
            if "Date" in df.columns
            else pd.Series(index=df.index, dtype=object)
        )
    df[date_column] = pd.Series(
        [_team_date_value(value) for value in date_values],
        index=df.index,
        dtype=object,
    )
    df = df.drop(columns=["Date"], errors="ignore")

    render_save_hint(
        "Edits are staged in this form until you submit them. "
        "Save team persists the roster; Remove empty rows only changes the current session draft."
    )

    with st.form("team_form", enter_to_submit=False):
        edited = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            height=360,
            row_height=38,
            column_config={
                "Name": st.column_config.TextColumn("Name", width="medium"),
                "Function / Role": st.column_config.SelectboxColumn(
                    "Function / Role",
                    width="medium",
                    options=TEAM_ROLE_OPTIONS,
                ),
                date_column: st.column_config.DateColumn(
                    date_column,
                    width="small",
                    format="DD/MM/YYYY",
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
                "Date": (
                    row[date_column].strftime("%d/%m/%Y")
                    if row.get(date_column) is not None and not pd.isna(row[date_column])
                    else ""
                ),
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

"""SURM managed barrier register."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from utils.form_ui import render_save_hint
from utils.intelligence import (
    apply_barrier_register_to_bowties,
    sync_barrier_register,
)
from utils.persistence import save_session


_COLUMNS = [
    "barrier_id",
    "name",
    "kind",
    "risk_ids",
    "resolution_id",
    "owner",
    "status",
    "progress",
    "due_date",
    "effectiveness",
    "health",
    "criticality",
    "verification_status",
    "evidence_count",
    "notes",
]


def render():
    if not st.session_state.get("bowtie_register"):
        st.info("Create at least one Bowtie in Tab 7 before managing barriers.")
        return

    register = sync_barrier_register(st.session_state)
    st.markdown("## 🛡️ Barrier Management")
    st.caption(
        "Administrative health and ownership of Bowtie barriers. This does not "
        "replace engineering verification or alter SURM risk scoring."
    )
    render_save_hint(
        "Barrier edits remain session drafts until you explicitly save the study."
    )

    rows = [register[key] for key in sorted(register)]
    frame = pd.DataFrame(rows, columns=_COLUMNS) if rows else pd.DataFrame(columns=_COLUMNS)

    with st.form("barrier_management_form", enter_to_submit=False):
        edited = st.data_editor(
            frame,
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            height=min(720, max(300, len(frame) * 72 + 120)),
            column_config={
                "barrier_id": st.column_config.TextColumn("Barrier ID", disabled=True),
                "name": st.column_config.TextColumn("Barrier", disabled=True),
                "kind": st.column_config.TextColumn("Type", disabled=True),
                "risk_ids": st.column_config.TextColumn("Risks", disabled=True),
                "resolution_id": st.column_config.TextColumn("Resolution ID", disabled=True),
                "owner": st.column_config.TextColumn("Owner"),
                "status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Planned", "Not Started", "In Progress", "Completed", "Closed", "On Hold"],
                ),
                "progress": st.column_config.NumberColumn("Progress", min_value=0.0, max_value=1.0, step=0.05),
                "due_date": st.column_config.TextColumn("Due Date"),
                "effectiveness": st.column_config.SelectboxColumn(
                    "Effectiveness",
                    options=["", "Low", "Medium", "High"],
                ),
                "health": st.column_config.SelectboxColumn(
                    "Health",
                    options=["Healthy", "At Risk", "Planned"],
                ),
                "criticality": st.column_config.SelectboxColumn(
                    "Criticality",
                    options=["Standard", "Important", "Critical"],
                ),
                "verification_status": st.column_config.SelectboxColumn(
                    "Verification",
                    options=["Pending", "In Review", "Verified", "Not Required"],
                ),
                "evidence_count": st.column_config.NumberColumn("Evidence", min_value=0, step=1),
                "notes": st.column_config.TextColumn("Notes"),
            },
            key=f"barrier_editor_{st.session_state.get('study_id', 'new')}",
        )
        save_clicked = st.form_submit_button(
            "Save barrier register",
            type="primary",
            key="save_barrier_register",
        )

    if not save_clicked:
        return

    updated = {}
    for row in edited.to_dict("records"):
        barrier_id = str(row.get("barrier_id", "")).strip()
        if not barrier_id:
            continue
        record = dict(register.get(barrier_id, {}))
        record.update(row)
        record["risk_ids"] = record.get("risk_ids") or []
        record["updated_at"] = datetime.now().isoformat(timespec="seconds")
        updated[barrier_id] = record

    st.session_state["barrier_register"] = updated
    apply_barrier_register_to_bowties(st.session_state)

    if save_session(auto=False):
        st.success("Barrier register saved with the study.")
    else:
        st.error("Barrier register could not be saved.")
    st.rerun()

"""SURM revision history and change comparison."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.history import diff_revisions, list_revisions, load_revision


def render():
    project = str(st.session_state.get("project_name", "")).strip()
    field = str(st.session_state.get("field_name", "")).strip()

    st.markdown("## 🕘 Revision History")
    if not project or not field:
        st.info("Set a Project Name and Field Name first.")
        return

    revisions = list_revisions(project, field)
    if not revisions:
        st.info("No immutable study revisions are stored yet. Save the study first.")
        return

    rev_frame = pd.DataFrame(revisions)
    st.dataframe(rev_frame, hide_index=True, use_container_width=True)

    revision_numbers = [int(item["revision"]) for item in revisions]
    current_default = revision_numbers[0]
    older_default = revision_numbers[1] if len(revision_numbers) > 1 else revision_numbers[0]

    c1, c2 = st.columns(2)
    with c1:
        newer = st.selectbox("Compare newer revision", revision_numbers, index=0)
    with c2:
        older = st.selectbox("Compare against", revision_numbers, index=revision_numbers.index(older_default))

    if newer == older:
        st.info("Select two different revisions to compare.")
        return

    newer_record = load_revision(project, field, newer)
    older_record = load_revision(project, field, older)
    changes = diff_revisions(older_record, newer_record)
    st.markdown(f"### Revision {older} → {newer}")
    if changes:
        st.dataframe(pd.DataFrame(changes), hide_index=True, use_container_width=True)
    else:
        st.success("No durable field-level changes detected between these revisions.")

    st.markdown("### Current change log")
    st.dataframe(
        pd.DataFrame(st.session_state.get("study_change_log", [])),
        hide_index=True,
        use_container_width=True,
    )

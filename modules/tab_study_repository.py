"""Saved study repository and explicit view/edit controls."""

from __future__ import annotations

import streamlit as st

from utils.form_ui import render_form_header
from utils.persistence import delete_session, list_sessions, load_session_record
from utils.session import create_new_study


def _last_edit(session: dict) -> tuple[str, str]:
    """Return the latest saved actor and timestamp from a study summary."""
    changes = session.get("study_change_log", []) or []
    if not changes:
        return session.get("study_owner", "local-user"), session.get("saved_at", "")
    latest = changes[-1]
    return latest.get("actor", "local-user"), latest.get("saved_at", session.get("saved_at", ""))


def _resume_page(session_meta: dict) -> str:
    """Return the last persisted study workspace, with a safe legacy fallback."""
    page = str((session_meta or {}).get("resume_page", "") or "").strip()
    valid_prefixes = (
        "📋 Overview",
        "👥 Team",
        "1️⃣ ",
        "2️⃣ ",
        "3️⃣ ",
        "4️⃣ ",
        "5️⃣ ",
        "6️⃣ ",
        "7️⃣ ",
        "📄 PRA Output",
        "📊 Intelligence",
        "🛡️ Barrier Management",
        "✅ Assurance & Review",
        "🕘 Revision History",
    )
    return page if page.startswith(valid_prefixes) else "📋 Overview"


def _load_for_view(session_meta: dict) -> None:
    if load_session_record(session_meta):
        st.session_state["study_access_mode"] = "view"
        st.session_state["current_page"] = _resume_page(session_meta)
        st.rerun()


def _delete_saved(project_name: str, field_name: str) -> None:
    if delete_session(project_name, field_name):
        if (st.session_state.get("project_name", ""), st.session_state.get("field_name", "")) == (project_name, field_name):
            create_new_study()
        st.rerun()


def render() -> None:
    render_form_header(
        "STUDY MANAGEMENT",
        "Study Repository",
        "Browse saved field studies, open a read-only view, or resume an editable study.",
        next_step="Overview",
    )

    sessions = list_sessions()
    if not sessions:
        with st.container(border=True):
            st.subheader("No saved studies yet")
            st.write("Create a new study, complete the workflow, and save it to build your study repository.")
            if st.button("＋ Create New Study", key="repository_create_new", type="primary"):
                create_new_study()
                st.session_state["current_page"] = "📋 Overview"
                st.rerun()
        return

    st.caption(f"{len(sessions)} saved study{'ies' if len(sessions) != 1 else ''}")
    for index, summary in enumerate(sessions):
        with st.container(border=True):
            title_col, status_col = st.columns([3, 1])
            with title_col:
                st.subheader(f"{summary.get('project_name', 'Unnamed study')} · {summary.get('field_name', 'Unknown field')}")
                st.caption(f"Phase: {summary.get('phase', '—')}  ·  Completion: {summary.get('completion', 0)}%")
            with status_col:
                st.metric("Lifecycle", summary.get("study_lifecycle", "Draft"))

            meta_col, action_col = st.columns([3, 1])
            with meta_col:
                actor = summary.get("last_edited_by", "local-user")
                edited_at = summary.get("last_edited_at", summary.get("saved_at", "—"))
                st.caption(
                    f"Revision {summary.get('study_revision', 0)} · "
                    f"Last edited by {actor} · {str(edited_at).replace('T', ' ')[:19]}"
                )
                st.caption(
                    f"Resume point: **{_resume_page(summary).split(' ', 1)[-1]}**"
                )
            with action_col:
                view_col, edit_col, delete_col = st.columns(3)
                with view_col:
                    if st.button(
                        "View",
                        key=f"repository_view_{index}",
                        use_container_width=True,
                        help=f"Open the saved study at {_resume_page(summary).split(' ', 1)[-1]} in read-only mode.",
                    ):
                        _load_for_view(summary)
                with edit_col:
                    if st.button(
                        "Resume",
                        key=f"repository_edit_{index}",
                        use_container_width=True,
                        type="primary",
                        help=f"Continue from the last saved workspace: {_resume_page(summary).split(' ', 1)[-1]}",
                    ):
                        if load_session_record(summary):
                            st.session_state["study_access_mode"] = "edit"
                            st.session_state["current_page"] = _resume_page(summary)
                            st.rerun()
                with delete_col:
                    if st.button("Delete", key=f"repository_delete_{index}", use_container_width=True):
                        _delete_saved(summary.get("project_name", ""), summary.get("field_name", ""))

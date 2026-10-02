"""Saved study repository and explicit view/edit controls."""

from __future__ import annotations

import html

import streamlit as st

from utils.form_ui import render_form_header
from utils.persistence import delete_session, list_sessions, load_session_record
from utils.session import create_new_study


_GALLERY_COLUMNS = 5
_GALLERY_PAGE_SIZE = 25


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


def _load_saved_study(session_meta: dict, *, edit: bool) -> None:
    """Load a saved study and route directly to its durable saved workspace."""
    if not load_session_record(session_meta):
        st.error("Unable to load this saved study.")
        return

    # persistence.load_session() has already resolved the canonical durable
    # last_saved_page. Read it back from session state rather than trusting
    # the repository summary/card that triggered the load.
    # New records expose last_saved_page directly. Older records only have
    # resume_page in their repository summary, so retain that safe fallback.
    persisted_page = st.session_state.get("last_saved_page")
    target = _resume_page(
        {"resume_page": persisted_page}
        if persisted_page
        else session_meta
    )
    st.session_state["current_page"] = target
    st.session_state["_pending_navigation_page"] = target
    st.session_state["study_access_mode"] = "edit" if edit else "view"
    st.rerun()


def _load_for_view(session_meta: dict) -> None:
    _load_saved_study(session_meta, edit=False)


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

    st.caption(
        f"{len(sessions)} saved "
        f"{'study' if len(sessions) == 1 else 'studies'}"
    )
    page_count = (len(sessions) + _GALLERY_PAGE_SIZE - 1) // _GALLERY_PAGE_SIZE
    page = min(
        max(int(st.session_state.get("repository_gallery_page", 0)), 0),
        page_count - 1,
    )
    st.session_state["repository_gallery_page"] = page
    page_start = page * _GALLERY_PAGE_SIZE
    page_sessions = sessions[page_start:page_start + _GALLERY_PAGE_SIZE]

    with st.container(key="study-repository-gallery"):
        for row_start in range(0, len(page_sessions), _GALLERY_COLUMNS):
            columns = st.columns(_GALLERY_COLUMNS, gap="small")
            for card_offset, (column, summary) in enumerate(zip(
                columns,
                page_sessions[row_start:row_start + _GALLERY_COLUMNS],
            )):
                index = page_start + row_start + card_offset
                project_name = str(summary.get("project_name", ""))
                field_name = str(summary.get("field_name", ""))
                study_key = (project_name, field_name)
                resume_page = _resume_page(summary).split(" ", 1)[-1]
                lifecycle = str(summary.get("study_lifecycle", "Draft") or "Draft")
                actor = str(summary.get("last_edited_by", "local-user") or "local-user")
                edited_at = str(
                    summary.get("last_edited_at", summary.get("saved_at", "—")) or "—"
                ).replace("T", " ")[:19]
                pending_delete = (
                    st.session_state.get("_repository_pending_delete") == study_key
                )
                title = (
                    f"{project_name or 'Unnamed study'} · "
                    f"{field_name or 'Unknown field'}"
                )

                with column:
                    with st.container(
                        key=f"repository-gallery-card-{index}",
                        border=True,
                    ):
                        st.markdown(
                            f"""
                            <div class="repository-gallery-heading">
                                <span class="repository-gallery-lifecycle">
                                    {html.escape(lifecycle)}
                                </span>
                                <strong>{html.escape(title)}</strong>
                                <span class="repository-gallery-hint">
                                    Hover or focus for study details
                                </span>
                            </div>
                            <div class="repository-gallery-details">
                                <div class="repository-gallery-detail-grid">
                                    <div class="repository-gallery-detail-item">
                                        <span>Field</span>
                                        <strong>{html.escape(field_name or "Unknown field")}</strong>
                                    </div>
                                    <div class="repository-gallery-detail-item">
                                        <span>Phase</span>
                                        <strong>{html.escape(str(summary.get("phase", "—") or "—"))}</strong>
                                    </div>
                                    <div class="repository-gallery-detail-item">
                                        <span>Complete</span>
                                        <strong>{int(summary.get("completion", 0) or 0)}%</strong>
                                    </div>
                                    <div class="repository-gallery-detail-item">
                                        <span>Revision</span>
                                        <strong>{int(summary.get("study_revision", 0) or 0)}</strong>
                                    </div>
                                </div>
                                <div class="repository-gallery-detail-meta">
                                    <div>
                                        <span>Last edited</span>
                                        <strong>{html.escape(actor)} · {html.escape(edited_at)}</strong>
                                    </div>
                                    <div>
                                        <span>Resume at</span>
                                        <strong>{html.escape(resume_page)}</strong>
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        with st.container(key=f"repository-gallery-actions-{index}"):
                            action_cols = st.columns(3, gap="small")
                            with action_cols[0]:
                                if st.button(
                                    "👁 View",
                                    key=f"repository_view_{index}",
                                    width="stretch",
                                    help=f"Open {title} in read-only mode.",
                                ):
                                    _load_for_view(summary)
                            with action_cols[1]:
                                if st.button(
                                    "✏️ Edit",
                                    key=f"repository_edit_{index}",
                                    width="stretch",
                                    type="primary",
                                    help=f"Continue editing from {resume_page}.",
                                ):
                                    _load_saved_study(summary, edit=True)
                            with action_cols[2]:
                                if st.button(
                                    "🗑 Delete",
                                    key=f"repository_delete_{index}",
                                    width="stretch",
                                    help=f"Delete {title}.",
                                ):
                                    st.session_state["_repository_pending_delete"] = study_key
                                    st.rerun()

                        if pending_delete:
                            with st.container(
                                key=f"repository-delete-confirmation-{index}"
                            ):
                                st.warning(
                                    "Delete this study permanently?",
                                    icon=":material/warning:",
                                )
                                confirm_col, cancel_col = st.columns(2, gap="small")
                                with confirm_col:
                                    if st.button(
                                        "Confirm",
                                        key=f"repository_confirm_delete_{index}",
                                        type="primary",
                                        width="stretch",
                                    ):
                                        _delete_saved(*study_key)
                                with cancel_col:
                                    if st.button(
                                        "Keep",
                                        key=f"repository_cancel_delete_{index}",
                                        width="stretch",
                                    ):
                                        st.session_state.pop(
                                            "_repository_pending_delete", None
                                        )
                                        st.rerun()

    if page_count > 1:
        previous_col, page_col, next_col = st.columns([1, 1, 1], gap="small")
        with previous_col:
            if st.button(
                "← Previous",
                key="repository_gallery_previous",
                disabled=page == 0,
                width="stretch",
            ):
                st.session_state["repository_gallery_page"] = page - 1
                st.rerun()
        with page_col:
            st.markdown(
                f'<div class="repository-gallery-pagination" aria-label="Page {page + 1} of {page_count}">'
                f"{page + 1} / {page_count}</div>",
                unsafe_allow_html=True,
            )
        with next_col:
            if st.button(
                "Next →",
                key="repository_gallery_next",
                disabled=page >= page_count - 1,
                width="stretch",
            ):
                st.session_state["repository_gallery_page"] = page + 1
                st.rerun()

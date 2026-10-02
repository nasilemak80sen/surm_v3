from __future__ import annotations

def _summary(index: int) -> dict:
    return {
        "project_name": f"Study {index:02d}",
        "field_name": f"Field {index:02d}",
        "phase": "PGR1",
        "completion": 75,
        "study_revision": 4,
        "study_lifecycle": "Draft",
        "last_edited_by": "test-user",
        "last_edited_at": "2026-10-01T10:30:00",
        "resume_page": "👥 Team",
    }


def _run_gallery(summaries: list[dict]):
    def app():
        import streamlit as st
        from modules import tab_study_repository as page
        from utils.session import init_session
        from unittest.mock import patch

        init_session()
        st.session_state.setdefault("_test_repository_summaries", [])
        st.session_state.setdefault("_test_repository_load_calls", [])
        st.session_state.setdefault("_test_repository_delete_calls", [])

        def load_record(metadata):
            st.session_state["_test_repository_load_calls"].append(metadata.copy())
            st.session_state["last_saved_page"] = metadata.get("resume_page")
            return True

        def delete_record(project, field):
            st.session_state["_test_repository_delete_calls"].append((project, field))
            return True

        with (
            patch.object(
                page,
                "list_sessions",
                lambda: st.session_state["_test_repository_summaries"],
            ),
            patch.object(page, "load_session_record", load_record),
            patch.object(page, "delete_session", delete_record),
        ):
            page.render()

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(app, default_timeout=15)
    at.session_state["_test_repository_summaries"] = summaries
    return at.run()


def test_study_repository_renders_five_by_five_gallery_pages():
    at = _run_gallery([_summary(index) for index in range(27)])

    assert not at.exception
    assert at.button(key="repository_view_0").label == "👁 View"
    assert at.button(key="repository_edit_0").label == "✏️ Edit"
    assert at.button(key="repository_delete_0").label == "🗑 Delete"
    gallery_markup = "\n".join(markdown.value for markdown in at.markdown)
    assert "repository-gallery-detail-grid" in gallery_markup
    assert "Last edited" in gallery_markup
    assert "Resume at" in gallery_markup
    assert len([button for button in at.button if button.key.startswith("repository_view_")]) == 25
    assert len([button for button in at.button if button.key.startswith("repository_edit_")]) == 25
    assert len([button for button in at.button if button.key.startswith("repository_delete_")]) == 25
    assert at.button(key="repository_gallery_previous").disabled
    assert at.button(key="repository_gallery_next")
    assert any("1 / 2" in markdown.value for markdown in at.markdown)

    at.button(key="repository_gallery_next").click().run()

    assert not at.exception
    assert at.session_state["repository_gallery_page"] == 1
    assert len([button for button in at.button if button.key.startswith("repository_view_")]) == 2
    assert at.button(key="repository_gallery_previous")
    assert at.button(key="repository_gallery_next").disabled
    assert any("2 / 2" in markdown.value for markdown in at.markdown)

    at.button(key="repository_gallery_previous").click().run()
    assert not at.exception
    assert at.session_state["repository_gallery_page"] == 0


def test_gallery_view_action_loads_study_read_only():
    at = _run_gallery([_summary(0)])

    at.button(key="repository_view_0").click().run()

    assert not at.exception
    assert at.session_state["_test_repository_load_calls"] == [_summary(0)]
    assert at.session_state["study_access_mode"] == "view"
    assert at.session_state["current_page"] == "👥 Team"
    assert at.session_state["_pending_navigation_page"] == "👥 Team"


def test_gallery_edit_action_loads_study_in_edit_mode():
    at = _run_gallery([_summary(0)])

    at.button(key="repository_edit_0").click().run()

    assert not at.exception
    assert at.session_state["_test_repository_load_calls"] == [_summary(0)]
    assert at.session_state["study_access_mode"] == "edit"
    assert at.session_state["current_page"] == "👥 Team"


def test_gallery_delete_requires_confirmation_and_can_be_cancelled():
    at = _run_gallery([_summary(0)])

    at.button(key="repository_delete_0").click().run()
    assert not at.exception
    assert at.session_state["_test_repository_delete_calls"] == []
    assert at.button(key="repository_confirm_delete_0")
    assert at.button(key="repository_cancel_delete_0")

    at.button(key="repository_cancel_delete_0").click().run()
    assert not at.exception
    assert at.session_state["_test_repository_delete_calls"] == []
    assert "_repository_pending_delete" not in at.session_state

    at.button(key="repository_delete_0").click().run()
    at.button(key="repository_confirm_delete_0").click().run()

    assert not at.exception
    assert at.session_state["_test_repository_delete_calls"] == [
        ("Study 00", "Field 00")
    ]

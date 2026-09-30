"""Full Streamlit entrypoint smoke coverage.

This test deliberately executes the real surm.py entrypoint so import-time or
startup-only regressions cannot hide behind module-level compile tests.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_full_surM_entrypoint_renders():
    project_root = Path(__file__).resolve().parents[1]
    app_path = project_root / "surm.py"

    at = AppTest.from_file(str(app_path), default_timeout=20).run()

    assert not at.exception, f"surm.py raised during startup: {at.exception}"
    assert at.markdown or at.title or at.info or at.success or at.warning
    assert at.text_input(key="project_name_input")
    assert at.text_input(key="field_name_input")
    assert at.selectbox(key="project_phase_input")
    assert at.button(key="fp_save")
    assert at.button(key="clear_study_details")


def test_full_entrypoint_survives_widget_reruns():
    project_root = Path(__file__).resolve().parents[1]
    at = AppTest.from_file(str(project_root / "surm.py"), default_timeout=20).run()

    assert not at.exception

    at.text_input(key="project_name_input").set_value("Smoke Stability Study").run()
    assert not at.exception
    assert at.session_state["project_name"] == "Smoke Stability Study"

    at.text_input(key="field_name_input").set_value("Smoke Field").run()
    assert not at.exception
    assert at.session_state["field_name"] == "Smoke Field"

    at.selectbox(key="project_phase_input").set_value("PGR1").run()
    assert not at.exception
    assert at.session_state["project_phase"] == "PGR1"

    # A second rerun must retain the durable values and the application shell.
    at.text_input(key="project_name_input").set_value("Smoke Stability Study 2").run()
    assert not at.exception
    assert at.session_state["project_name"] == "Smoke Stability Study 2"
    assert at.button(key="fp_save")

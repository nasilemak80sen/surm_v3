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

"""
SURM stylesheet loader.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st


def load_css() -> None:
    """
    Load the SURM global stylesheet.
    """

    project_root = Path(__file__).resolve().parents[1]

    css_path = (
        project_root
        / "assets"
        / "css"
        / "surm.css"
    )

    if not css_path.exists():

        st.warning(
            f"SURM stylesheet not found: {css_path}"
        )

        return

    css = css_path.read_text(
        encoding="utf-8"
    )

    st.markdown(
        f"""
        <style>
        {css}
        </style>
        """,
        unsafe_allow_html=True,
    )
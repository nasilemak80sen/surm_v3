"""
SURM UI Rendering Utilities.
Centralised helpers for rendering custom HTML/CSS
inside Streamlit. This module intentionally contains presentation logic only.
"""

from __future__ import annotations
import streamlit as st


def render_html(
    html: str,
) -> None:
    """
    Render raw HTML inside Streamlit.

    All SURM custom HTML should go through this helper.

    Parameters
    ----------
    html:
        HTML string to render.
    """

    if not isinstance(html, str):
        html = str(html)

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


def render_css(
    css: str,
) -> None:
    """
    Inject CSS into the Streamlit application.

    Parameters
    ----------
    css:
        CSS stylesheet contents.
    """

    if not isinstance(css, str):
        css = str(css)

    st.markdown(
        f"""
        <style>
        {css}
        </style>
        """,
        unsafe_allow_html=True,
    )
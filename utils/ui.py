"""
SURM UI Rendering Utilities.
Centralised helpers for rendering custom HTML/CSS
inside Streamlit. This module intentionally contains presentation logic only.
"""

from __future__ import annotations
import textwrap

import streamlit as st


def normalize_markup(value: str) -> str:
    """Return indented multiline markup in a form Streamlit can render."""

    if not isinstance(value, str):
        value = str(value)

    value = textwrap.dedent(value).strip()

    # Interpolated fragments can contain lines with less indentation than the
    # surrounding template, defeating dedent and triggering Markdown code
    # blocks. HTML does not require indentation, so remove it line by line.
    return "\n".join(line.lstrip() for line in value.splitlines())


_streamlit_markdown = st.markdown


def _safe_markdown(body, unsafe_allow_html=False, **kwargs):
    """Normalize legacy unsafe HTML calls before delegating to Streamlit."""

    if unsafe_allow_html:
        body = normalize_markup(body)

    return _streamlit_markdown(
        body,
        unsafe_allow_html=unsafe_allow_html,
        **kwargs,
    )


# Existing page modules still use st.markdown directly. Install the boundary
# adapter once so those legacy calls cannot regress into visible code blocks.
st.markdown = _safe_markdown


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

    html = normalize_markup(html)

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

    css = normalize_markup(css)

    st.markdown(
        f"""
        <style>
        {css}
        </style>
        """,
        unsafe_allow_html=True,
    )
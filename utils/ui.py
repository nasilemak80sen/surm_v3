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



def _install_markdown_adapter(streamlit_module):
    """Install the SURM markdown adapter without wrapping it again on reload.

    Streamlit's development file watcher can reload Python modules in-process.
    Storing the original implementation on the Streamlit module itself keeps
    repeated imports/reloads anchored to the real st.markdown function
    rather than to a previously wrapped adapter.
    """

    original = getattr(streamlit_module, "_surm_original_markdown", None)
    if original is None:
        original = streamlit_module.markdown
        setattr(streamlit_module, "_surm_original_markdown", original)

    def _safe_markdown(body, unsafe_allow_html=False, **kwargs):
        """Normalize legacy unsafe HTML calls before delegating to Streamlit."""

        if unsafe_allow_html:
            body = normalize_markup(body)

        return original(
            body,
            unsafe_allow_html=unsafe_allow_html,
            **kwargs,
        )

    streamlit_module.markdown = _safe_markdown
    return original


# Existing page modules still use st.markdown directly. Keep this adapter
# compatible with Streamlit's development reload cycle.
_install_markdown_adapter(st)



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
"""Compact UI primitives for SURM workflow forms."""

from __future__ import annotations

import html
import streamlit as st


def render_form_header(
    step: str,
    title: str,
    purpose: str,
    *,
    next_step: str | None = None,
) -> None:
    """Render a restrained page intro; navigation remains in the global nav."""
    next_hint = (
        f'<span class="surm-form-next">Next: {html.escape(next_step)}</span>'
        if next_step else ""
    )
    st.markdown(
        f"""
        <div class="surm-form-header">
            <div>
                <div class="surm-form-step">{html.escape(step)}</div>
                <div class="surm-form-title">{html.escape(title)}</div>
                <div class="surm-form-purpose">{html.escape(purpose)}</div>
            </div>
            {next_hint}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_save_hint(message: str = "Save your changes before moving to another stage.") -> None:
    """Render a quiet instruction, not a dominant card."""
    st.markdown(
        f'<div class="surm-save-hint">↳ {html.escape(message)}</div>',
        unsafe_allow_html=True,
    )


def render_stage_status(*, label: str, value: str, tone: str = "info") -> None:
    """Render a compact status line."""
    icons = {"success": "✓", "warning": "!", "error": "×", "info": "·"}
    icon = icons.get(tone, icons["info"])
    st.markdown(
        f"""
        <div class="surm-stage-status surm-stage-{html.escape(tone)}">
            <span class="surm-stage-status-icon">{icon}</span>
            <span><strong>{html.escape(label)}</strong> {html.escape(value)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

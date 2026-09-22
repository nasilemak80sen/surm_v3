"""Reusable form UX helpers for the SURM workflow pages.

The helpers in this module intentionally keep presentation concerns out of
business logic. They provide a consistent mental model for users filling in
SURM as a guided engineering form.
"""

from __future__ import annotations

import streamlit as st


def render_form_header(
    step: str,
    title: str,
    purpose: str,
    *,
    next_step: str | None = None,
) -> None:
    """Render a compact, consistent introduction for a workflow form."""
    next_hint = (
        f'<span class="surm-form-next"><strong>Next:</strong> {next_step}</span>'
        if next_step
        else ""
    )
    st.markdown(
        f"""
        <div style="
            background:#FFFFFF;
            border:1px solid #DDE7E1;
            border-left:5px solid #1F6B3A;
            border-radius:8px;
            padding:14px 18px;
            margin:0 0 14px 0;
        ">
            <div style="
                font-size:11px;
                font-weight:700;
                letter-spacing:.08em;
                text-transform:uppercase;
                color:#1F6B3A;
                margin-bottom:4px;
            ">{step}</div>
            <div style="font-size:22px;font-weight:700;color:#17352A;">
                {title}
            </div>
            <div style="font-size:13px;line-height:1.55;color:#5E6D66;margin-top:4px;">
                {purpose}
            </div>
            {next_hint}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_save_hint(message: str = "Save your changes before moving to another stage.") -> None:
    """Render a low-friction reminder immediately above a form."""
    st.markdown(
        f"""
        <div style="
            font-size:11px;
            color:#5E6D66;
            background:#F7FAF8;
            border:1px solid #E1EAE4;
            border-radius:6px;
            padding:8px 10px;
            margin-bottom:8px;
        ">
            💾 {message}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stage_status(
    *,
    label: str,
    value: str,
    tone: str = "info",
) -> None:
    """Render a small status card for form completion state."""
    palette = {
        "success": ("#E8F5E9", "#1F6B3A", "✓"),
        "warning": ("#FFF8E1", "#9A6700", "!"),
        "error": ("#FDECEC", "#B42318", "×"),
        "info": ("#EEF5F2", "#316B56", "i"),
    }
    background, foreground, icon = palette.get(tone, palette["info"])
    st.markdown(
        f"""
        <div style="
            display:flex;
            align-items:center;
            gap:10px;
            background:{background};
            border:1px solid {foreground}22;
            border-radius:7px;
            padding:8px 11px;
            margin-bottom:10px;
        ">
            <div style="
                width:22px;height:22px;border-radius:50%;
                display:flex;align-items:center;justify-content:center;
                background:{foreground};color:white;font-weight:700;font-size:12px;
            ">{icon}</div>
            <div>
                <div style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;
                            color:{foreground};font-weight:700;">{label}</div>
                <div style="font-size:12px;color:#33443C;">{value}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

"""
SURM Card Components.

Reusable content containers used throughout the application.
"""

from __future__ import annotations
from utils.ui import render_html
import html

import streamlit as st


# ============================================================================
# STANDARD CARD
# ============================================================================

def render_card(
    title: str | None = None,
    description: str | None = None,
    *,
    content: str | None = None,
    icon: str | None = None,
    variant: str = "default",
) -> None:
    """
    Render a standard SURM content card.

    Parameters
    ----------
    title:
        Card heading.

    description:
        Supporting text.

    content:
        Optional HTML content.

    icon:
        Optional icon displayed beside the title.

    variant:
        ``default``, ``success``, ``warning``, ``danger`` or ``info``.
    """

    allowed_variants = {
        "default",
        "success",
        "warning",
        "danger",
        "info",
    }

    if variant not in allowed_variants:
        variant = "default"

    safe_title = (
        html.escape(title)
        if title
        else ""
    )

    safe_description = (
        html.escape(description)
        if description
        else ""
    )

    safe_icon = (
        html.escape(icon)
        if icon
        else ""
    )

    title_html = ""

    if title:
        title_html = f"""
        <div class="surm-card-header">

            {
                f'<span class="surm-card-icon">{safe_icon}</span>'
                if icon
                else ""
            }

            <div>
                <div class="surm-card-title">
                    {safe_title}
                </div>

                {
                    f'<div class="surm-card-description">'
                    f'{safe_description}'
                    f'</div>'
                    if description
                    else ""
                }

            </div>

        </div>
        """

    content_html = content or ""

    st.markdown(
        f"""
        <div class="surm-card surm-card-{variant}">

            {title_html}

            {
                f'<div class="surm-card-content">'
                f'{content_html}'
                f'</div>'
                if content_html
                else ""
            }

        </div>
        """,
         
    )


# ============================================================================
# SECTION CARD
# ============================================================================

def render_section_header(
    title: str,
    description: str | None = None,
    *,
    eyebrow: str | None = None,
) -> None:
    """
    Render a page section heading.

    This intentionally isn't wrapped in a card.
    """

    eyebrow_html = ""

    if eyebrow:
        eyebrow_html = f"""
        <div class="surm-section-eyebrow">
            {html.escape(eyebrow)}
        </div>
        """

    description_html = ""

    if description:
        description_html = f"""
        <div class="surm-section-description">
            {html.escape(description)}
        </div>
        """

    st.markdown(
        f"""
        <div class="surm-section-header">

            {eyebrow_html}

            <div class="surm-section-title">
                {html.escape(title)}
            </div>

            {description_html}

        </div>
        """,
         
    )


# ============================================================================
# EMPTY STATE
# ============================================================================

def render_empty_state(
    title: str,
    description: str,
    *,
    icon: str = "○",
) -> None:
    """
    Render an empty-state panel.
    """

    st.markdown(
        f"""
        <div class="surm-empty-state">

            <div class="surm-empty-icon">
                {html.escape(icon)}
            </div>

            <div class="surm-empty-title">
                {html.escape(title)}
            </div>

            <div class="surm-empty-description">
                {html.escape(description)}
            </div>

        </div>
        """,
         
    )
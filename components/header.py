"""
SURM Header Component.

Responsible only for rendering the application header.

This module must NOT:
- modify business data
- modify assessment records
- perform persistence
- perform navigation
- create database connections
"""

from __future__ import annotations

import html
from typing import Any
from utils.ui import render_html
from components.status import status_html


def _safe(value: Any, fallback: str = "Not configured") -> str:
    """
    Convert a value to safe HTML text.

    Parameters
    ----------
    value:
        Value to display.

    fallback:
        Text displayed when value is empty.
    """

    if value is None:
        return fallback

    text = str(value).strip()

    if not text:
        return fallback

    return html.escape(text)


def render_header(
    *,
    field: str | None = None,
    project: str | None = None,
    phase: str | None = None,
    organisation: str = "PETRONAS CARIGALI",
    app_name: str = "SURM Toolkit",
    subtitle: str = "Subsurface Uncertainty & Risk Management",
    saved: bool = False,
) -> None:
    """
    Render the SURM application header.

    This function is presentation-only.
    """

    organisation_html = _safe(
        organisation,
        "PETRONAS CARIGALI",
    )

    app_name_html = _safe(
        app_name,
        "SURM Toolkit",
    )

    subtitle_html = _safe(
        subtitle,
        "Subsurface Uncertainty & Risk Management",
    )

    field_html = _safe(field)
    project_html = _safe(project)
    phase_html = _safe(phase)
    save_status = status_html("saved" if saved else "draft")

    render_html(
        f"""
        <div class="surm-header">

            <div class="surm-header-left">

                <div class="surm-logo">
                    🛢️
                </div>

                <div class="surm-header-brand">

                    <div class="surm-eyebrow">
                        {organisation_html}
                    </div>

                    <div class="surm-title">
                        {app_name_html}
                    </div>

                    <div class="surm-subtitle">
                        {subtitle_html}
                    </div>

                </div>

            </div>


            <div class="surm-header-meta">

                <div class="surm-meta-item">

                    <div class="surm-meta-label">
                        Field
                    </div>

                    <div class="surm-meta-value">
                        {field_html}
                    </div>

                </div>


                <div class="surm-meta-item">

                    <div class="surm-meta-label">
                        Project
                    </div>

                    <div class="surm-meta-value">
                        {project_html}
                    </div>

                </div>


                <div class="surm-meta-item">

                    <div class="surm-meta-label">
                        Phase
                    </div>

                    <div class="surm-meta-value">
                        {phase_html}
                    </div>

                </div>

                {save_status}

            </div>

        </div>
        """
    )
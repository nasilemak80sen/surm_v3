"""
SURM Metric Components.

Reusable KPI / metric cards.
"""

from __future__ import annotations

import html

from utils.ui import render_html
import streamlit as st


# ============================================================================
# METRIC CARD
# ============================================================================

def render_metric_card(
    title: str,
    value: str | int | float,
    *,
    description: str | None = None,
    icon: str | None = None,
    trend: str | None = None,
    variant: str = "default",
) -> None:
    """
    Render a SURM KPI card.
    """

    allowed_variants = {
        "default",
        "primary",
        "success",
        "warning",
        "danger",
        "info",
    }

    if variant not in allowed_variants:
        variant = "default"

    title_html = html.escape(str(title))
    value_html = html.escape(str(value))

    description_html = ""

    if description:
        description_html = f"""
        <div class="surm-metric-description">
            {html.escape(str(description))}
        </div>
        """

    icon_html = ""

    if icon:
        icon_html = f"""
        <div class="surm-metric-icon">
            {html.escape(str(icon))}
        </div>
        """

    trend_html = ""

    if trend:
        trend_html = f"""
        <div class="surm-metric-trend">
            {html.escape(str(trend))}
        </div>
        """

    render_html(
        f"""
        <div class="surm-metric-card surm-metric-{variant}">

            <div class="surm-metric-top">

                <div class="surm-metric-title">
                    {title_html}
                </div>

                {icon_html}

            </div>

            <div class="surm-metric-value">
                {value_html}
            </div>

            {description_html}

            {trend_html}

        </div>
        """,
         
    )


# ============================================================================
# METRIC GRID
# ============================================================================

def render_metric_grid(
    metrics: list[dict],
    *,
    columns: int = 4,
) -> None:
    """
    Render multiple metric cards in a responsive Streamlit grid.

    Example
    -------

    metrics = [
        {
            "title": "Uncertainties",
            "value": 24,
            "description": "Selected",
            "icon": "◈",
        },
    ]
    """

    if not metrics:
        return

    columns = max(
        1,
        min(columns, len(metrics)),
    )

    cols = st.columns(
        columns,
        gap="medium",
    )

    for index, metric in enumerate(metrics):

        with cols[index % columns]:

            render_metric_card(
                title=metric.get(
                    "title",
                    "",
                ),
                value=metric.get(
                    "value",
                    0,
                ),
                description=metric.get(
                    "description",
                ),
                icon=metric.get(
                    "icon",
                ),
                trend=metric.get(
                    "trend",
                ),
                variant=metric.get(
                    "variant",
                    "default",
                ),
            )


# ============================================================================
# PROGRESS CARD
# ============================================================================

def render_progress_card(
    title: str,
    progress: float,
    *,
    description: str | None = None,
) -> None:
    """
    Render a large study-progress card.

    ``progress`` is expected as a percentage from 0 to 100.
    """

    progress = max(
        0.0,
        min(100.0, float(progress)),
    )

    description_html = ""

    if description:
        description_html = f"""
        <div class="surm-progress-description">
            {html.escape(description)}
        </div>
        """

    render_html(
        f"""
        <div class="surm-progress-card">

            <div class="surm-progress-header">

                <div>
                    <div class="surm-progress-title">
                        {html.escape(title)}
                    </div>

                    {description_html}

                </div>

                <div class="surm-progress-value">
                    {progress:.0f}%
                </div>

            </div>

            <div class="surm-progress-track">

                <div
                    class="surm-progress-fill"
                    style="width: {progress:.1f}%"
                ></div>

            </div>

        </div>
        """,
         
    )


"""
SURM Workflow Components.

Provides reusable workflow navigation and progress indicators.
"""

from __future__ import annotations
import html

from utils.ui import render_html


# ============================================================================
# WORKFLOW ITEM
# ============================================================================

def render_workflow_item(
    number: int,
    label: str,
    *,
    state: str = "not_started",
    description: str | None = None,
) -> None:
    """
    Render a single workflow item.

    States:
        completed
        current
        not_started
        locked
    """

    allowed_states = {
        "completed",
        "current",
        "not_started",
        "locked",
    }

    if state not in allowed_states:
        state = "not_started"

    if state == "completed":
        indicator = "✓"

    elif state == "current":
        indicator = str(number)

    elif state == "locked":
        indicator = "🔒"

    else:
        indicator = str(number)

    description_html = ""

    if description:
        description_html = f"""
        <div class="surm-workflow-description">
            {html.escape(description)}
        </div>
        """

    render_html(
        f"""
        <div class="surm-workflow-item surm-workflow-{state}">

            <div class="surm-workflow-indicator">
                {indicator}
            </div>

            <div class="surm-workflow-content">

                <div class="surm-workflow-label">
                    {html.escape(label)}
                </div>

                {description_html}

            </div>

        </div>
        """,
         
    )


# ============================================================================
# WORKFLOW LIST
# ============================================================================

def render_workflow_list(
    items: list[dict],
    *,
    current_page: str | None = None,
) -> None:
    """
    Render a complete workflow list.

    Example
    -------

    items = [
        {
            "number": 1,
            "label": "Uncertainties",
            "page": "1️⃣ Uncertainties",
            "completed": True,
        }
    ]
    """

    for item in items:

        page = item.get(
            "page",
            item.get("label", ""),
        )

        if current_page == page:

            state = "current"

        elif item.get(
            "completed",
            False,
        ):

            state = "completed"

        elif item.get(
            "locked",
            False,
        ):

            state = "locked"

        else:

            state = "not_started"

        render_workflow_item(
            number=int(
                item.get(
                    "number",
                    0,
                )
            ),
            label=str(
                item.get(
                    "label",
                    "",
                )
            ),
            state=state,
            description=item.get(
                "description",
            ),
        )


# ============================================================================
# WORKFLOW PROGRESS
# ============================================================================

def calculate_workflow_progress(
    items: list[dict],
) -> float:
    """
    Calculate workflow completion percentage.
    """

    if not items:
        return 0.0

    completed = sum(
        1
        for item in items
        if item.get(
            "completed",
            False,
        )
    )

    return (
        completed
        / len(items)
        * 100
    )


# ============================================================================
# WORKFLOW HEADER
# ============================================================================

def render_workflow_header(
    title: str,
    description: str | None = None,
    *,
    step: int | None = None,
    total_steps: int | None = None,
) -> None:
    """
    Render a page-level workflow header.
    """

    step_html = ""

    if (
        step is not None
        and total_steps is not None
    ):

        step_html = f"""
        <div class="surm-workflow-step">
            Step {step} of {total_steps}
        </div>
        """

    description_html = ""

    if description:

        description_html = f"""
        <div class="surm-page-description">
            {html.escape(description)}
        </div>
        """

    render_html(
        f"""
        <div class="surm-page-header">

            <div class="surm-page-header-main">

                <h1 class="surm-page-title">
                    {html.escape(title)}
                </h1>

                {description_html}

            </div>

            {step_html}

        </div>
        """,
         
    )


def render_page_frame(
    title: str,
    description: str,
    *,
    step: int | None = None,
    total_steps: int = 7,
) -> None:
    """Render the consistent heading used by workflow and output pages."""

    render_workflow_header(
        title,
        description,
        step=step,
        total_steps=total_steps,
    )


def render_page_footer(
    *,
    previous_page: str | None = None,
    next_page: str | None = None,
) -> None:
    """Render a lightweight page boundary for visual continuity."""

    previous_html = html.escape(previous_page or "")
    next_html = html.escape(next_page or "")

    render_html(
        f"""
        <div class="surm-page-footer">
            <span class="surm-page-footer-previous">
                {f"Previous: {previous_html}" if previous_page else ""}
            </span>
            <span class="surm-page-footer-next">
                {f"Next: {next_html} &rarr;" if next_page else ""}
            </span>
        </div>
        """
    )
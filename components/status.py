"""
SURM Status Components.

Provides consistent visual status indicators throughout the application.
"""

from __future__ import annotations
import html

from utils.ui import render_html


# ============================================================================
# STATUS DEFINITIONS
# ============================================================================

STATUS_CONFIG = {
    "draft": {
        "label": "Draft",
        "icon": "●",
        "css_class": "status-draft",
    },

    "saved": {
        "label": "Saved",
        "icon": "✓",
        "css_class": "status-saved",
    },

    "complete": {
        "label": "Complete",
        "icon": "✓",
        "css_class": "status-complete",
    },

    "in_progress": {
        "label": "In Progress",
        "icon": "●",
        "css_class": "status-in-progress",
    },

    "not_started": {
        "label": "Not Started",
        "icon": "○",
        "css_class": "status-not-started",
    },

    "warning": {
        "label": "Warning",
        "icon": "!",
        "css_class": "status-warning",
    },

    "error": {
        "label": "Error",
        "icon": "!",
        "css_class": "status-error",
    },
}


# ============================================================================
# STATUS BADGE
# ============================================================================

def render_status(
    status: str,
    label: str | None = None,
    *,
    icon: str | None = None,
) -> None:
    """
    Render a compact status badge.

    Parameters
    ----------
    status:
        Status key such as ``saved``, ``draft`` or ``complete``.

    label:
        Optional custom display label.

    icon:
        Optional custom icon.
    """

    config = STATUS_CONFIG.get(
        status,
        STATUS_CONFIG["draft"],
    )

    display_label = label or config["label"]
    display_icon = icon or config["icon"]

    display_label = html.escape(str(display_label))
    display_icon = html.escape(str(display_icon))

    render_html(
        f"""
        <span class="surm-status-badge {config["css_class"]}">
            <span class="surm-status-icon">{display_icon}</span>
            <span class="surm-status-label">{display_label}</span>
        </span>
        """,
         
    )


# ============================================================================
# STATUS HTML
# ============================================================================

def status_html(
    status: str,
    label: str | None = None,
) -> str:
    """
    Return status HTML instead of rendering it.

    Useful when composing cards or headers.
    """

    config = STATUS_CONFIG.get(
        status,
        STATUS_CONFIG["draft"],
    )

    display_label = html.escape(
        str(label or config["label"])
    )

    display_icon = html.escape(
        str(config["icon"])
    )

    return (
        f'<span class="surm-status-badge '
        f'{config["css_class"]}">'
        f'<span class="surm-status-icon">'
        f'{display_icon}'
        f'</span>'
        f'<span class="surm-status-label">'
        f'{display_label}'
        f'</span>'
        f'</span>'
    )
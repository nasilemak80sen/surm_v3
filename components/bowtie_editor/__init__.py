"""Streamlit bridge for the SURM Bowtie editor.

The frontend is a local custom component. It keeps the diagram in browser-side
SVG state and returns the current Bowtie JSON to Python after a user edit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components


_COMPONENT = components.declare_component(
    "surm_bowtie_editor",
    path=str(Path(__file__).resolve().parent / "frontend"),
)


def render(
    document: dict[str, Any],
    *,
    key: str,
    height: int = 720,
    editable: bool = True,
) -> dict[str, Any] | None:
    """Render an editable Bowtie and return the most recent changed document."""
    return _COMPONENT(
        document=document,
        editable=editable,
        height=height,
        key=key,
        default=None,
    )


def render_readonly(document: dict[str, Any], *, key: str, height: int = 760) -> None:
    """Render a read-only Bowtie view for reporting pages."""
    _COMPONENT(document=document, editable=False, height=height, key=key, default=None)

"""
Tab 4 — Key Uncertainties.

The calculated ranking remains unchanged. This page focuses the user on the
human decision: which ranked uncertainties should actually be carried into the
resolution plan?
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.form_ui import render_form_header, render_save_hint, render_stage_status
from utils.logic import compute_key_uncertainties
from utils.persistence import save_session
from utils.workflow import mark_stage_changed


_RATING_HTML = {
    "HH": "#C00000",
    "HM": "#FF4500",
    "HL": "#FFA500",
    "MH": "#FF8C00",
    "MM": "#FFD700",
    "ML": "#A5D6A7",
    "LH": "#FFC107",
    "LM": "#C8E6C9",
    "LL": "#00B050",
}


def _badge(rating: str) -> str:
    background = _RATING_HTML.get(rating, "#EEE")
    text = "white" if rating in ("HH", "HM", "MH", "LL") else "#3E2000"
    return (
        f'<span style="background:{background};color:{text};'
        f'padding:2px 10px;border-radius:10px;font-size:11px;'
        f'font-weight:700;">{rating}</span>'
    )


def render():
    impact_assessment = st.session_state.get("impact_assessment", [])
    decisions = st.session_state.get("key_decisions", [])

    if not impact_assessment:
        st.info(
            "⬅️ Complete **Tab 3 – Impact Assessment** first."
        )
        return

    render_form_header(
        "STEP 4 OF 7",
        "Key Uncertainties",
        "Review the calculated ranking, then decide which uncertainties deserve "
        "resolution planning. SURM calculates the rank; the study team decides "
        "what to carry forward.",
        next_step="Resolution List",
    )

    st.info(
        "The ranking is calculated from the saved Tab 3 assessment. "
        "Use **Include in Plan** to identify the uncertainties that require action."
    )

    impact_df = pd.DataFrame(impact_assessment)
    key_uncertainties = compute_key_uncertainties(
        impact_df,
        decisions,
    )

    if key_uncertainties.empty:
        st.warning(
            "No rankings could be calculated. Return to Tab 3 and check the assessment."
        )
        return

    existing = {
        row["Uncertainty"]: row
        for row in st.session_state.get("key_uncertainties", [])
        if isinstance(row, dict) and row.get("Uncertainty")
    }

    key_uncertainties["Include in Plan"] = key_uncertainties[
        "Uncertainty"
    ].map(
        lambda name: existing.get(name, {}).get(
            "Include in Plan",
            True,
        )
    )
    key_uncertainties["Resolution Achieved"] = key_uncertainties[
        "Uncertainty"
    ].map(
        lambda name: existing.get(name, {}).get(
            "Resolution Achieved",
            False,
        )
    )

    included_count = int(
        key_uncertainties["Include in Plan"].sum()
    )

    if included_count:
        render_stage_status(
            label="Planning selection",
            value=(
                f"{included_count} of {len(key_uncertainties)} ranked uncertainties "
                "are currently included in the plan."
            ),
            tone="success",
        )
    else:
        render_stage_status(
            label="Planning selection",
            value="Include at least one uncertainty before moving to resolution planning.",
            tone="warning",
        )

    st.markdown(
        '<div class="surm-section-header">📋 Ranked Uncertainties</div>',
        unsafe_allow_html=True,
    )

    with st.form("ku_form"):
        render_save_hint(
            "Review the calculated ranking and select what should carry forward. "
            "Apply the selection before moving to Tab 5."
        )

        button_cols = st.columns([1, 1, 0.5, 3])
        with button_cols[0]:
            include_all = st.form_submit_button(
                "✅ Include All",
                help="Carry every ranked uncertainty into the plan.",
            )
        with button_cols[1]:
            exclude_all = st.form_submit_button(
                "☐ Exclude All",
                help="Remove every ranked uncertainty from the plan.",
            )
        with button_cols[3]:
            apply_selection = st.form_submit_button(
                "🔄 Apply Selection",
                type="primary",
            )

        edited = st.data_editor(
            key_uncertainties[
                [
                    "uncertainty_id",
                    "Uncertainty",
                    "Degree of Uncertainty",
                    "Impact (Weighted)",
                    "Impact Bin",
                    "Combined Rating",
                    "Rank",
                    "Include in Plan",
                    "Resolution Achieved",
                ]
            ],
            column_config={
                "uncertainty_id": st.column_config.TextColumn(
                    "ID",
                    width="small",
                    disabled=True,
                ),
                "Uncertainty": st.column_config.TextColumn(
                    "Uncertainty",
                    width="large",
                    disabled=True,
                ),
                "Degree of Uncertainty": st.column_config.TextColumn(
                    "Degree",
                    width="small",
                    disabled=True,
                ),
                "Impact (Weighted)": st.column_config.NumberColumn(
                    "Score",
                    format="%.3f",
                    disabled=True,
                    width="small",
                ),
                "Impact Bin": st.column_config.TextColumn(
                    "Impact",
                    width="small",
                    disabled=True,
                ),
                "Combined Rating": st.column_config.TextColumn(
                    "Rating",
                    width="small",
                    disabled=True,
                ),
                "Rank": st.column_config.NumberColumn(
                    "Rank",
                    width="small",
                    disabled=True,
                ),
                "Include in Plan": st.column_config.CheckboxColumn(
                    "Include ✓",
                    help="Carry this uncertainty into the resolution plan.",
                ),
                "Resolution Achieved": st.column_config.CheckboxColumn(
                    "Resolved ✓",
                    help="Use this as the team's resolution tracking flag.",
                ),
            },
            hide_index=True,
            width="stretch",
            num_rows="fixed",
            key=f"ku_editor_{st.session_state.get('study_id', 'new')}",
        )

    if include_all or exclude_all or apply_selection:
        full = key_uncertainties.copy()
        full["Include in Plan"] = edited["Include in Plan"].values
        full["Resolution Achieved"] = edited["Resolution Achieved"].values

        if include_all:
            full["Include in Plan"] = True
        elif exclude_all:
            full["Include in Plan"] = False

        st.session_state["key_uncertainties"] = full.to_dict("records")
        mark_stage_changed(
            st.session_state,
            "key_uncertainties",
        )

        ok = save_session(auto=not apply_selection)
        if not ok:
            st.error("Key uncertainty selection could not be saved.")
            return

        st.success(
            f"✅ {int(full['Include in Plan'].sum())} uncertainties selected for planning."
        )
        st.rerun()

    # ------------------------------------------------------------------
    # Charts from saved state
    # ------------------------------------------------------------------
    saved_key_uncertainties = st.session_state.get(
        "key_uncertainties",
        [],
    )

    if not saved_key_uncertainties:
        st.info(
            "Apply the selection above to generate the decision-support charts."
        )
        return

    saved_df = pd.DataFrame(saved_key_uncertainties)
    active = saved_df[
        saved_df["Include in Plan"]
    ]

    metric_cols = st.columns(4)
    metric_cols[0].metric(
        "Total",
        len(saved_df),
    )
    metric_cols[1].metric(
        "Included",
        int(saved_df["Include in Plan"].sum()),
    )
    metric_cols[2].metric(
        "High Priority",
        int(
            saved_df["Combined Rating"].isin(
                ["HH", "HM", "MH", "HL", "LH"]
            ).sum()
        ),
    )
    metric_cols[3].metric(
        "Resolved",
        int(saved_df["Resolution Achieved"].sum()),
    )

    if active.empty:
        st.warning(
            "No uncertainties are currently included. Select at least one above."
        )
        return

    from utils.charts import build_tornado_chart, build_uncertainty_matrix
    from utils.export_png import fig_to_png_bytes

    matrix_col, tornado_col = st.columns(2)

    with matrix_col:
        st.markdown(
            '<div class="surm-section-header">🟩 Uncertainty Matrix</div>',
            unsafe_allow_html=True,
        )
        matrix_figure = build_uncertainty_matrix(active)
        st.plotly_chart(matrix_figure, width="stretch")
        try:
            st.download_button(
                "📥 Matrix (PNG)",
                data=fig_to_png_bytes(matrix_figure),
                file_name="SURM_Uncertainty_Matrix.png",
                mime="image/png",
            )
        except Exception:
            st.caption("Install kaleido for PNG export.")

    with tornado_col:
        st.markdown(
            '<div class="surm-section-header">🌪️ Tornado Chart</div>',
            unsafe_allow_html=True,
        )
        tornado_figure = build_tornado_chart(active)
        st.plotly_chart(tornado_figure, width="stretch")
        try:
            st.download_button(
                "📥 Tornado (PNG)",
                data=fig_to_png_bytes(
                    tornado_figure,
                    height=max(500, len(active) * 55 + 120),
                ),
                file_name="SURM_Tornado_Chart.png",
                mime="image/png",
            )
        except Exception:
            st.caption("Install kaleido for PNG export.")

    st.divider()

    legend = "".join(
        f'<span style="margin:3px;display:inline-block;">{_badge(rating)}</span>'
        for rating in [
            "HH",
            "HM",
            "HL",
            "MH",
            "MM",
            "ML",
            "LH",
            "LM",
            "LL",
        ]
    )
    st.markdown(
        '<div style="padding:10px;background:#FAFAFA;'
        'border:1px solid #E8E8E8;border-radius:6px;">'
        '<span style="font-size:12px;color:#888;margin-right:10px;">'
        'Degree × Impact →</span>'
        f"{legend}</div>",
        unsafe_allow_html=True,
    )

    st.success(
        f"✅ {int(active['Include in Plan'].sum())} uncertainties included. "
        "Proceed to **Tab 5 → Resolution List**."
    )

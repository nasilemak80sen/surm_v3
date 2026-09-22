"""Tab 4 — Key Uncertainties: prioritisation with immediate decision support."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.form_ui import render_form_header, render_save_hint, render_stage_status
from utils.logic import compute_key_uncertainties
from utils.persistence import save_session
from utils.workflow import mark_stage_changed


_RATING_HTML = {
    "HH": "#C00000", "HM": "#FF4500", "HL": "#FFA500",
    "MH": "#FF8C00", "MM": "#FFD700", "ML": "#A5D6A7",
    "LH": "#FFC107", "LM": "#C8E6C9", "LL": "#00B050",
}


def _badge(rating: str) -> str:
    background = _RATING_HTML.get(rating, "#EEE")
    text = "white" if rating in {"HH", "HM", "MH", "LL"} else "#3E2000"
    return f'<span style="background:{background};color:{text};padding:2px 9px;border-radius:10px;font-size:10px;font-weight:700;">{rating}</span>'


def render():
    impact_assessment = st.session_state.get("impact_assessment", [])
    decisions = st.session_state.get("key_decisions", [])

    if not impact_assessment:
        st.info("⬅️ Complete **Tab 3 – Impact Assessment** first.")
        return

    render_form_header(
        "STEP 4 OF 7",
        "Key Uncertainties",
        "The ranking is calculated. Your job here is to decide what carries into resolution planning.",
        next_step="Resolution List",
    )

    impact_df = pd.DataFrame(impact_assessment)
    key_uncertainties = compute_key_uncertainties(impact_df, decisions)

    if key_uncertainties.empty:
        st.warning("No rankings could be calculated. Return to Tab 3 and check the assessment.")
        return

    existing = {
        row["Uncertainty"]: row
        for row in st.session_state.get("key_uncertainties", [])
        if isinstance(row, dict) and row.get("Uncertainty")
    }

    key_uncertainties["Include in Plan"] = key_uncertainties["Uncertainty"].map(
        lambda name: existing.get(name, {}).get("Include in Plan", True)
    )
    key_uncertainties["Resolution Achieved"] = key_uncertainties["Uncertainty"].map(
        lambda name: existing.get(name, {}).get("Resolution Achieved", False)
    )

    saved = st.session_state.get("key_uncertainties", [])
    saved_df = pd.DataFrame(saved) if saved else key_uncertainties.copy()
    if "Include in Plan" not in saved_df.columns:
        saved_df["Include in Plan"] = True
    if "Resolution Achieved" not in saved_df.columns:
        saved_df["Resolution Achieved"] = False

    included = int(saved_df["Include in Plan"].sum()) if not saved_df.empty else 0
    high_priority = (
        int(
            saved_df["Combined Rating"].isin(
                ["HH", "HM", "MH", "HL", "LH"]
            ).sum()
        )
        if not saved_df.empty
        else 0
    )
    resolved = (
        int(saved_df["Resolution Achieved"].sum())
        if not saved_df.empty
        else 0
    )
    ranked_count = len(saved_df)

    # Keep the executive signal together at the top, matching the pattern used
    # in Tabs 5–7. The detailed matrix/reporting stays full-width below.
    metric_cols = st.columns(4)
    metric_cols[0].metric("Ranked", ranked_count)
    metric_cols[1].metric("Included", included)
    metric_cols[2].metric("High priority", high_priority)
    metric_cols[3].metric("Resolved", resolved)

    if included:
        render_stage_status(
            label="Plan selection",
            value=f"{included} of {ranked_count} ranked uncertainties are in the plan.",
            tone="success",
        )
    else:
        render_stage_status(
            label="Plan selection",
            value="Select at least one uncertainty.",
            tone="warning",
        )

    st.markdown(
        '<div class="surm-section-header">Prioritisation Matrix</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Calculated fields are locked. Edit only the two planning checkboxes."
    )
    render_save_hint(
        "Include/Resolved changes are a session draft until you click Save selection. "
        "Bulk Include/Exclude applies a draft change without persisting the saved study."
    )

    with st.form("ku_form", enter_to_submit=False):
        button_cols = st.columns([1, 1, 2.2, 3.6])
        with button_cols[0]:
            include_all = st.form_submit_button("Include all", key="ku_include_all")
        with button_cols[1]:
            exclude_all = st.form_submit_button("Exclude all", key="ku_exclude_all")
        with button_cols[2]:
            apply_selection = st.form_submit_button(
                "Save selection",
                key="save_key_uncertainties",
                type="primary",
            )
        with button_cols[3]:
            st.caption(
                "Use **Plan** to carry an uncertainty into resolution planning; "
                "**Resolved** is tracking metadata."
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
                    "ID", width="small", disabled=True
                ),
                "Uncertainty": st.column_config.TextColumn(
                    "Uncertainty", width="large", disabled=True
                ),
                "Degree of Uncertainty": st.column_config.TextColumn(
                    "Degree", width="small", disabled=True
                ),
                "Impact (Weighted)": st.column_config.NumberColumn(
                    "Score", format="%.3f", disabled=True, width="small"
                ),
                "Impact Bin": st.column_config.TextColumn(
                    "Impact", width="small", disabled=True
                ),
                "Combined Rating": st.column_config.TextColumn(
                    "Rating", width="small", disabled=True
                ),
                "Rank": st.column_config.NumberColumn(
                    "Rank", width="small", disabled=True
                ),
                "Include in Plan": st.column_config.CheckboxColumn(
                    "Plan",
                    help="Carry this uncertainty into resolution planning.",
                ),
                "Resolution Achieved": st.column_config.CheckboxColumn(
                    "Resolved",
                    help="Track whether the uncertainty has been resolved.",
                ),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            height=min(720, max(320, len(key_uncertainties) * 60 + 100)),
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

        previous_rows = st.session_state.get("key_uncertainties", [])
        previous_include = {
            str(row.get("Uncertainty", "")).strip(): bool(row.get("Include in Plan"))
            for row in previous_rows
            if isinstance(row, dict)
        }
        next_rows = full.to_dict("records")
        next_include = {
            str(row.get("Uncertainty", "")).strip(): bool(row.get("Include in Plan"))
            for row in next_rows
        }

        st.session_state["key_uncertainties"] = next_rows

        # Resolution Achieved is tracking metadata. It does not invalidate
        # the resolution matrix or later risk/PRA work.
        if previous_include != next_include:
            mark_stage_changed(st.session_state, "key_uncertainties")

        if apply_selection:
            if not st.session_state.get("project_name", "").strip():
                st.warning(
                    "Enter a Project Name on Overview before saving the key uncertainty selection."
                )
                return
            ok = save_session(auto=False)
            if not ok:
                st.error("Key uncertainty selection could not be saved.")
                return
            st.success("✅ Key uncertainty selection saved.")
        else:
            st.info(
                "Draft updated. Click **Save selection** to persist the key uncertainty selection."
            )
        st.rerun()

    # ------------------------------------------------------------------
    # Reporting area: full width, below the engineering editor.
    # ------------------------------------------------------------------
    saved = st.session_state.get("key_uncertainties", [])
    saved_df = pd.DataFrame(saved) if saved else key_uncertainties.copy()
    if "Include in Plan" not in saved_df.columns:
        saved_df["Include in Plan"] = True
    active = saved_df[saved_df["Include in Plan"]].copy()

    if active.empty:
        st.caption("No uncertainties are currently included in the resolution plan.")

    if not active.empty:
        from utils.charts import build_tornado_chart, build_uncertainty_matrix
        from utils.export_png import fig_to_png_bytes

        st.markdown(
            '<div class="surm-section-header">Uncertainty Matrix</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Degree of uncertainty is plotted against decision impact. Each point represents an uncertainty selected for the plan."
        )

        matrix_display = active.reset_index(drop=True).copy()
        matrix_display.insert(0, "Matrix #", range(1, len(matrix_display) + 1))

        matrix_figure = build_uncertainty_matrix(matrix_display)
        st.plotly_chart(
            matrix_figure,
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )
        st.caption("Numbers in the matrix map directly to the detail table below.")
        st.dataframe(
            matrix_display[
                [
                    "Matrix #",
                    "Uncertainty",
                    "Degree of Uncertainty",
                    "Impact Bin",
                    "Combined Rating",
                    "Impact (Weighted)",
                    "Rank",
                ]
            ].rename(
                columns={
                    "Degree of Uncertainty": "Degree",
                    "Impact Bin": "Impact",
                    "Combined Rating": "Rating",
                    "Impact (Weighted)": "Weighted Score",
                }
            ),
            hide_index=True,
            use_container_width=True,
            height=min(420, max(120, len(matrix_display) * 48 + 48)),
        )
        try:
            st.download_button(
                "Download matrix",
                data=fig_to_png_bytes(matrix_figure, width=1500, height=700),
                file_name="SURM_Uncertainty_Matrix.png",
                mime="image/png",
                use_container_width=True,
                key="ku_matrix_download",
            )
        except Exception:
            pass

        st.markdown(
            '<div class="surm-section-header">Priority Ranking — Weighted Impact</div>',
            unsafe_allow_html=True,
        )
        tornado_figure = build_tornado_chart(active)
        st.plotly_chart(
            tornado_figure,
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )
        try:
            st.download_button(
                "Download tornado",
                data=fig_to_png_bytes(
                    tornado_figure,
                    width=1500,
                    height=max(520, len(active) * 55 + 140),
                ),
                file_name="SURM_Tornado_Chart.png",
                mime="image/png",
                use_container_width=True,
                key="ku_tornado_download",
            )
        except Exception:
            pass

    legend = "".join(
        f'<span style="margin:2px;display:inline-block;">{_badge(r)}</span>'
        for r in ["HH", "HM", "HL", "MH", "MM", "ML", "LH", "LM", "LL"]
    )
    st.markdown(
        '<div style="margin-top:0.6rem;color:#66736B;font-size:10px;">Degree × Impact → '
        + legend
        + "</div>",
        unsafe_allow_html=True,
    )

"""
modules/tab7_risk_register.py

Risk register form with explicit "Not Assessed" state. The existing risk
matrix is preserved exactly; the enhancement prevents an unassessed risk from
being reported as Medium/Medium.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.workflow import render_page_frame
from utils.form_ui import render_form_header, render_save_hint, render_stage_status
from utils.logic import (
    RISK_MATRIX,
    build_pra_output,
    build_risk_register,
    calculate_risk_rating,
    is_risk_assessed,
)
from utils.persistence import save_session

_RATING_OPTIONS = ["", "H", "M", "L"]
_STATUS_OPTIONS = ["Open", "In Progress", "Closed", "On Hold"]


def _risk_distribution(df: pd.DataFrame) -> dict[str, int]:
    distribution = {
        "Extreme": 0,
        "High": 0,
        "Medium": 0,
        "Low": 0,
        "Not Assessed": 0,
    }

    for _, row in df.iterrows():
        rating = calculate_risk_rating(
            row.get("Likelihood (H/M/L)", ""),
            row.get("Impact (H/M/L)", ""),
        )
        distribution[rating] = distribution.get(rating, 0) + 1

    return distribution


def render():
    ku_list = [
        row
        for row in st.session_state.get("key_uncertainties", [])
        if row.get("Include in Plan")
    ]
    res_list = st.session_state.get("resolution_list", {})

    if not ku_list:
        st.info("⬅️ Complete **Tab 4** first.")
        return

    render_form_header(
        "STEP 7 OF 7",
        "Risk Register",
        "Turn the selected uncertainties into an actionable risk register. "
        "Each generated risk starts as **Not Assessed** until the study team explicitly "
        "sets likelihood and impact.",
        next_step="PRA Output",
    )

    st.info(
        "Use the generated register as your starting point. Then complete the "
        "risk owner, consequence, contingency, likelihood, impact and status."
    )

    # ------------------------------------------------------------------
    # Populate generated risks
    # ------------------------------------------------------------------
    col_btn, col_hint = st.columns([1, 3], gap="small")
    with col_btn:
        populate = st.button(
            "🔄 Populate Risk Register",
            type="primary",
            key="populate_risk_register",
            use_container_width=True,
        )
    with col_hint:
        st.caption(
            "Populate again only when upstream uncertainties or resolutions changed. "
            "Existing risk assessments are preserved by risk name."
        )

    if populate:
        ku_df = pd.DataFrame(ku_list)
        options = st.session_state["_mapping"]["resolution_options"]

        resolution_rows = []
        for _, row in ku_df.iterrows():
            output = {
                "Uncertainty": row["Uncertainty"],
                "Rating": row.get("Combined Rating", ""),
            }
            output.update(res_list.get(row["Uncertainty"], {}))
            resolution_rows.append(output)

        resolution_df = pd.DataFrame(resolution_rows)
        risk_df = build_risk_register(ku_df, resolution_df)

        st.session_state["risk_register"] = risk_df.to_dict("records")
        st.session_state["pra_output"] = []
        save_session(auto=True)
        st.rerun()

    risk_data = st.session_state.get("risk_register", [])
    if not risk_data:
        render_stage_status(
            label="Register status",
            value="No risks populated yet. Start with the Populate Risk Register button.",
            tone="info",
        )
        return

    risk_df = pd.DataFrame(risk_data)

    distribution = _risk_distribution(risk_df)
    assessed_count = sum(
        1 for row in risk_data if is_risk_assessed(row)
    )
    total_count = len(risk_data)
    not_assessed = total_count - assessed_count

    if not_assessed:
        render_stage_status(
            label="Assessment status",
            value=(
                f"{assessed_count} of {total_count} risks assessed. "
                f"{not_assessed} still need explicit likelihood and impact."
            ),
            tone="warning",
        )
    else:
        render_stage_status(
            label="Assessment status",
            value=f"All {total_count} risks have explicit likelihood and impact ratings.",
            tone="success",
        )

    metric_cols = st.columns(5)
    metric_cols[0].metric("Extreme", distribution["Extreme"])
    metric_cols[1].metric("High", distribution["High"])
    metric_cols[2].metric("Medium", distribution["Medium"])
    metric_cols[3].metric("Low", distribution["Low"])
    metric_cols[4].metric("Not Assessed", distribution["Not Assessed"])

    # ------------------------------------------------------------------
    # Risk register form
    # ------------------------------------------------------------------
    st.markdown(
        '<div class="surm-section-header">📋 Risk Register</div>',
        unsafe_allow_html=True,
    )

    with st.form("rr_form"):
        render_save_hint(
            "Complete the assessment fields, then click Save Register. "
            "Unassessed risks will remain visible but will not be treated as Medium."
        )

        _, save_col = st.columns([5, 1])
        with save_col:
            save_clicked = st.form_submit_button(
                "💾 Save Register",
                type="primary",
            )

        edited = st.data_editor(
            risk_df,
            column_config={
                "risk_id": st.column_config.TextColumn(
                    "Risk ID",
                    width="small",
                    disabled=True,
                ),
                "#": st.column_config.NumberColumn(
                    "#",
                    width="small",
                    disabled=True,
                ),
                "Risk": st.column_config.TextColumn(
                    "Risk",
                    width="medium",
                    disabled=True,
                ),
                "Uncertainty/Causes": st.column_config.TextColumn(
                    "Causes / Uncertainties",
                    width="large",
                    disabled=True,
                ),
                "Resolution Plan": st.column_config.TextColumn(
                    "Resolution Plan",
                    width="large",
                    disabled=True,
                ),
                "Action Owner": st.column_config.TextColumn(
                    "Action Owner",
                    help="Person accountable for monitoring or managing this risk.",
                ),
                "Contingency Plan": st.column_config.TextColumn(
                    "Contingency Plan",
                    width="large",
                ),
                "Impact/Consequence": st.column_config.TextColumn(
                    "Impact / Consequence",
                    width="large",
                ),
                "Likelihood (H/M/L)": st.column_config.SelectboxColumn(
                    "Likelihood",
                    options=_RATING_OPTIONS,
                    width="small",
                    help="Leave blank until the study team explicitly assesses likelihood.",
                ),
                "Impact (H/M/L)": st.column_config.SelectboxColumn(
                    "Impact",
                    options=_RATING_OPTIONS,
                    width="small",
                    help="Leave blank until the study team explicitly assesses impact.",
                ),
                "Risk Rating": st.column_config.TextColumn(
                    "Risk Rating",
                    width="small",
                    disabled=True,
                ),
                "Risk Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=_STATUS_OPTIONS,
                    width="small",
                ),
                "Remarks": st.column_config.TextColumn(
                    "Remarks",
                    width="large",
                ),
            },
            hide_index=True,
            width="stretch",
            num_rows="fixed",
            key=f"rr_editor_{st.session_state.get('study_id', 'new')}",
        )

    if save_clicked:
        edited = edited.copy()
        edited["Risk Rating"] = edited.apply(
            lambda row: calculate_risk_rating(
                row.get("Likelihood (H/M/L)", ""),
                row.get("Impact (H/M/L)", ""),
            ),
            axis=1,
        )

        saved_rows = edited.to_dict("records")
        st.session_state["risk_register"] = saved_rows
        st.session_state["pra_output"] = (
            build_pra_output(edited).to_dict("records")
            if all(is_risk_assessed(row) for row in saved_rows)
            else []
        )

        ok = save_session(auto=False)
        if not ok:
            st.error("Register could not be saved.")
            return

        st.success("✅ Risk register saved.")
        st.rerun()

    # ------------------------------------------------------------------
    # Bowtie generator
    # ------------------------------------------------------------------
    st.divider()
    st.markdown(
        '<div class="surm-section-header">🦋 Bowtie Diagram Generator</div>',
        unsafe_allow_html=True,
    )
    st.info(
        "Select an assessed risk to generate its Bowtie. "
        "Complete consequence and contingency fields first for a useful diagram."
    )

    risk_names = risk_df["Risk"].tolist()
    col_select, col_generate = st.columns([3, 1], gap="small")

    with col_select:
        selected_risk = st.selectbox(
            "Select risk",
            risk_names,
            key="bowtie_risk_selection",
        )

    with col_generate:
        generate = st.button(
            "🦋 Generate Bowtie",
            type="primary",
            key="generate_bowtie",
            use_container_width=True,
        )

    if generate:
        risk_rows = risk_df[risk_df["Risk"] == selected_risk]
        if risk_rows.empty:
            st.warning("The selected risk is no longer available in the current register.")
        else:
            risk_row = risk_rows.iloc[0].to_dict()
            if not is_risk_assessed(risk_row):
                st.warning(
                    "Assess likelihood and impact before generating the Bowtie "
                    "for this risk."
                )
            else:
                from utils.charts import build_bowtie
                from utils.export_png import fig_to_png_bytes

                figure = build_bowtie(risk_row)
                st.plotly_chart(figure, width="stretch")

                try:
                    png_data = fig_to_png_bytes(
                        figure,
                        width=1600,
                        height=700,
                    )
                    safe = (
                        selected_risk
                        .replace("/", "_")
                        .replace(" ", "_")[:40]
                    )
                    st.download_button(
                        f"📥 Download Bowtie — {selected_risk[:30]} (PNG)",
                        data=png_data,
                        file_name=f"SURM_Bowtie_{safe}.png",
                        mime="image/png",
                    )
                except Exception:
                    st.caption("Install kaleido for PNG export.")

    # ------------------------------------------------------------------
    # Status overview
    # ------------------------------------------------------------------
    st.divider()
    st.markdown(
        '<div class="surm-section-header">📊 Status Overview</div>',
        unsafe_allow_html=True,
    )

    if "Risk Status" in risk_df.columns:
        status_counts = risk_df["Risk Status"].value_counts()
        badge_map = {
            "Open": "badge-open",
            "In Progress": "badge-progress",
            "Closed": "badge-closed",
            "On Hold": "badge-hold",
        }

        cols = st.columns(max(len(status_counts), 1))
        for col, (status, count) in zip(cols, status_counts.items()):
            badge = badge_map.get(status, "")
            col.markdown(
                f"""
                <div style="text-align:center;padding:12px;background:#FAFAFA;
                border:1px solid #E8E8E8;border-radius:6px;">
                    <div style="font-size:22px;font-weight:700;">{count}</div>
                    <span class="badge {badge}">{status}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

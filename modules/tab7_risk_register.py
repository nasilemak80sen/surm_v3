"""Tab 7 — Risk Register: assessment workspace with live risk and Bowtie view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.form_ui import render_form_header, render_stage_status
from utils.logic import (
    build_pra_output,
    build_risk_register,
    calculate_risk_rating,
    is_risk_assessed,
)
from utils.persistence import save_session
from utils.workflow import mark_stage_changed


_RATING_OPTIONS = ["", "H", "M", "L"]
_STATUS_OPTIONS = ["Open", "In Progress", "Closed", "On Hold"]
_RATING_ORDER = ["Extreme", "High", "Medium", "Low", "Not Assessed"]


def _risk_distribution(df: pd.DataFrame) -> dict[str, int]:
    distribution = {key: 0 for key in _RATING_ORDER}
    for _, row in df.iterrows():
        rating = calculate_risk_rating(
            row.get("Likelihood (H/M/L)", ""),
            row.get("Impact (H/M/L)", ""),
        )
        distribution[rating] = distribution.get(rating, 0) + 1
    return distribution


def render():
    ku_list = [
        row for row in st.session_state.get("key_uncertainties", [])
        if row.get("Include in Plan")
    ]
    res_list = st.session_state.get("resolution_list", {})

    if not ku_list:
        st.info("⬅️ Complete **Tab 4** first.")
        return

    render_form_header(
        "STEP 7 OF 7",
        "Risk Register",
        "Assess the generated risks explicitly, then use the right-hand panel to inspect exposure and generate a Bowtie.",
        next_step="PRA Output",
    )

    risk_data = st.session_state.get("risk_register", [])

    left, right = st.columns([1.75, 1], gap="large")

    with left:
        populate = st.button(
            "Populate from current plan",
            type="secondary",
            key="populate_risk_register",
            use_container_width=True,
        )
        st.caption("Populate again only when upstream uncertainties or resolutions change. Existing assessments are preserved by risk name.")

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

            risk_df = build_risk_register(ku_df, pd.DataFrame(resolution_rows))
            st.session_state["risk_register"] = risk_df.to_dict("records")
            mark_stage_changed(st.session_state, "risk_register")
            save_session(auto=True)
            st.rerun()

        risk_data = st.session_state.get("risk_register", [])
        if not risk_data:
            render_stage_status(
                label="Register",
                value="No risks populated yet.",
                tone="info",
            )
        else:
            risk_df = pd.DataFrame(risk_data)
            with st.form("rr_form"):
                save_clicked = st.form_submit_button("Save risk register", type="primary")
                edited = st.data_editor(
                    risk_df,
                    column_config={
                        "risk_id": st.column_config.TextColumn("ID", width="small", disabled=True),
                        "#": st.column_config.NumberColumn("#", width="small", disabled=True),
                        "Risk": st.column_config.TextColumn("Risk", width="medium", disabled=True),
                        "Uncertainty/Causes": st.column_config.TextColumn("Causes / Uncertainties", width="large", disabled=True),
                        "Resolution Plan": st.column_config.TextColumn("Resolution Plan", width="large", disabled=True),
                        "Action Owner": st.column_config.TextColumn("Owner"),
                        "Contingency Plan": st.column_config.TextColumn("Contingency", width="large"),
                        "Impact/Consequence": st.column_config.TextColumn("Consequence", width="large"),
                        "Likelihood (H/M/L)": st.column_config.SelectboxColumn("Likelihood", options=_RATING_OPTIONS, width="small", help="Blank = Not Assessed"),
                        "Impact (H/M/L)": st.column_config.SelectboxColumn("Impact", options=_RATING_OPTIONS, width="small", help="Blank = Not Assessed"),
                        "Risk Rating": st.column_config.TextColumn("Rating", width="small", disabled=True),
                        "Risk Status": st.column_config.SelectboxColumn("Status", options=_STATUS_OPTIONS, width="small"),
                        "Remarks": st.column_config.TextColumn("Remarks", width="large"),
                    },
                    hide_index=True,
                use_container_width=True,
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
                mark_stage_changed(st.session_state, "risk_register")
                st.session_state["pra_output"] = (
                    build_pra_output(edited).to_dict("records")
                    if all(is_risk_assessed(row) for row in saved_rows)
                    else []
                )
                ok = save_session(auto=False)
                if not ok:
                    st.error("Register could not be saved.")
                    return
                st.rerun()

    risk_data = st.session_state.get("risk_register", [])

    with right:
        st.markdown("**Risk pulse**")
        if risk_data:
            risk_df = pd.DataFrame(risk_data)
            distribution = _risk_distribution(risk_df)
            assessed_count = sum(is_risk_assessed(row) for row in risk_data)
            not_assessed = len(risk_data) - assessed_count

            metric_cols = st.columns(2)
            metric_cols[0].metric("Risks", len(risk_data))
            metric_cols[1].metric("Assessed", assessed_count)
            st.metric("Not assessed", not_assessed)

            st.bar_chart(pd.DataFrame({
                "Count": [distribution[k] for k in ["Extreme", "High", "Medium", "Low"]]
            }, index=["Extreme", "High", "Medium", "Low"]))

            if not_assessed:
                render_stage_status(
                    label="PRA",
                    value=f"{not_assessed} risk(s) still need likelihood and impact.",
                    tone="warning",
                )
            else:
                render_stage_status(
                    label="PRA",
                    value="All risks are explicitly assessed.",
                    tone="success",
                )

            st.markdown("**Bowtie**")
            risk_names = risk_df["Risk"].tolist()
            selected_risk = st.selectbox("Risk", risk_names, key="bowtie_risk_selection")
            generate = st.button("Generate Bowtie", type="primary", key="generate_bowtie", use_container_width=True)

            if generate:
                risk_row = risk_df[risk_df["Risk"] == selected_risk]
                if risk_row.empty:
                    st.warning("The selected risk is no longer available.")
                else:
                    record = risk_row.iloc[0].to_dict()
                    if not is_risk_assessed(record):
                        st.warning("Assess likelihood and impact before generating the Bowtie.")
                    else:
                        from utils.charts import build_bowtie
                        from utils.export_png import fig_to_png_bytes
                        figure = build_bowtie(record)
                        st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
                        try:
                            safe = selected_risk.replace("/", "_").replace(" ", "_")[:40]
                            st.download_button(
                                "Download Bowtie (PNG)",
                                data=fig_to_png_bytes(figure, width=1600, height=700),
                                file_name=f"SURM_Bowtie_{safe}.png",
                                mime="image/png",
                                use_container_width=True,
                                key="bowtie_download",
                            )
                        except Exception:
                            st.caption("Install kaleido for PNG export.")

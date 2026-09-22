"""Tab 7 — Risk Register: assessment workspace with live risk and Bowtie view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.form_ui import render_form_header, render_save_hint, render_stage_status
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
        "Assess the generated risks explicitly, then review the portfolio distribution and Bowtie below the register.",
        next_step="PRA Output",
    )

    risk_data = st.session_state.get("risk_register", [])
    risk_df = pd.DataFrame(risk_data) if risk_data else pd.DataFrame()
    distribution = _risk_distribution(risk_df) if risk_data else {key: 0 for key in _RATING_ORDER}
    assessed_count = sum(is_risk_assessed(row) for row in risk_data)
    not_assessed = len(risk_data) - assessed_count
    assessed_pct = round((assessed_count / max(len(risk_data), 1)) * 100)

    # Executive signal first. Detailed register and visual diagnostics get
    # their own full-width sections below.
    metric_cols = st.columns(4)
    metric_cols[0].metric("Risks", len(risk_data))
    metric_cols[1].metric("Assessed", assessed_count)
    metric_cols[2].metric("Not assessed", not_assessed)
    metric_cols[3].metric("Assessment", f"{assessed_pct}%")

    if not risk_data:
        render_stage_status(
            label="Register",
            value="No risks populated yet.",
            tone="info",
        )
    elif not_assessed:
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

    populate = st.button(
        "Populate from current plan",
        type="secondary",
        key="populate_risk_register",
        use_container_width=True,
    )
    st.caption(
        "Populate again only when upstream uncertainties or resolutions change. "
        "Existing assessments are preserved by risk identity."
    )

    if populate:
        ku_df = pd.DataFrame(ku_list)
        resolution_rows = []
        for _, row in ku_df.iterrows():
            output = {
                "Uncertainty": row["Uncertainty"],
                "Rating": row.get("Combined Rating", ""),
            }
            output.update(res_list.get(row["Uncertainty"], {}))
            resolution_rows.append(output)

        risk_df = build_risk_register(ku_df, pd.DataFrame(resolution_rows))
        previous = st.session_state.get("risk_register", [])
        updated = risk_df.to_dict("records")
        st.session_state["risk_register"] = updated
        if previous != updated:
            mark_stage_changed(st.session_state, "risk_register")
        st.info("Risk register draft populated. Review it, then click **Save risk register** to persist.")
        st.rerun()

    risk_data = st.session_state.get("risk_register", [])

    if not risk_data:
        return

    risk_df = pd.DataFrame(risk_data)
    with st.container():
        st.markdown('<div class="surm-section-header">Risk Register</div>', unsafe_allow_html=True)
        render_save_hint(
            "Risk edits are a session draft until you click Save risk register. "
            "PRA output is regenerated only when the saved risk register is explicitly committed."
        )
        with st.form("rr_form", enter_to_submit=False):
            save_clicked = st.form_submit_button(
                "Save risk register",
                key="save_risk_register",
                type="primary",
            )
            edited = st.data_editor(
                risk_df,
                column_config={
                    "risk_id": st.column_config.TextColumn("ID", width="small", disabled=True),
                    "#": st.column_config.NumberColumn("#", width="small", disabled=True),
                    "Risk": st.column_config.TextColumn("Risk", width="large", disabled=True),
                    "Uncertainty/Causes": st.column_config.TextColumn("Causes / Uncertainties", width="large", disabled=True),
                    "Resolution Plan": st.column_config.TextColumn("Resolution Plan", width="large", disabled=True),
                    "Action Owner": st.column_config.TextColumn("Owner"),
                    "Contingency Plan": st.column_config.TextColumn("Contingency", width="large"),
                    "Impact/Consequence": st.column_config.TextColumn("Consequence", width="large"),
                    "Likelihood (H/M/L)": st.column_config.SelectboxColumn(
                        "Likelihood",
                        options=_RATING_OPTIONS,
                        width="small",
                        help="Blank = Not Assessed",
                    ),
                    "Impact (H/M/L)": st.column_config.SelectboxColumn(
                        "Impact",
                        options=_RATING_OPTIONS,
                        width="small",
                        help="Blank = Not Assessed",
                    ),
                    "Risk Rating": st.column_config.TextColumn("Rating", width="small", disabled=True),
                    "Risk Status": st.column_config.SelectboxColumn("Status", options=_STATUS_OPTIONS, width="small"),
                    "Remarks": st.column_config.TextColumn("Remarks", width="large"),
                },
                hide_index=True,
                use_container_width=True,
                num_rows="fixed",
                height=min(760, max(340, len(risk_data) * 78 + 100)),
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
        if not st.session_state.get("project_name", "").strip():
            st.warning("Enter a Project Name on Overview before saving the risk register.")
            return
        ok = save_session(auto=False)
        if not ok:
            st.error("Register could not be saved.")
            return
        st.success("✅ Risk register saved.")
        st.rerun()

    # ------------------------------------------------------------------
    # Portfolio reporting: deliberately separated from the editing table.
    # ------------------------------------------------------------------
    risk_data = st.session_state.get("risk_register", [])
    risk_df = pd.DataFrame(risk_data)
    distribution = _risk_distribution(risk_df)

    st.markdown('<div class="surm-section-header">Risk Distribution</div>', unsafe_allow_html=True)
    distribution_df = pd.DataFrame(
        {"Risks": [distribution[level] for level in ["Extreme", "High", "Medium", "Low", "Not Assessed"]]},
        index=["Extreme", "High", "Medium", "Low", "Not Assessed"],
    )
    st.bar_chart(
        distribution_df,
        use_container_width=True,
        height=320,
    )

    # ------------------------------------------------------------------
    # Bowtie: full-width reporting section with a deliberately larger figure.
    # ------------------------------------------------------------------
    st.markdown('<div class="surm-section-header">Bowtie Analysis</div>', unsafe_allow_html=True)
    risk_names = [str(name) for name in risk_df["Risk"].tolist()]
    selected_risk = st.selectbox(
        "Risk event",
        risk_names,
        key="bowtie_risk_selection",
        help="Choose an assessed risk to generate its threat → event → consequence view.",
    )
    generate = st.button(
        "Generate Bowtie",
        type="primary",
        key="generate_bowtie",
        use_container_width=True,
    )

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
                st.plotly_chart(
                    figure,
                    use_container_width=True,
                    config={"displayModeBar": False, "responsive": True},
                )
                try:
                    safe = selected_risk.replace("/", "_").replace(" ", "_")[:40]
                    st.download_button(
                        "Download Bowtie (PNG)",
                        data=fig_to_png_bytes(figure, width=1800, height=900),
                        file_name=f"SURM_Bowtie_{safe}.png",
                        mime="image/png",
                        use_container_width=True,
                        key="bowtie_download",
                    )
                except Exception:
                    st.caption("Install kaleido for PNG export.")

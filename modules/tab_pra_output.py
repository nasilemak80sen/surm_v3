"""Final PRA output — read-only reporting view generated from the Risk Register."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.bowtie_editor import render_readonly as render_bowtie_readonly

from utils.analytics import build_executive_summary
from utils.export_excel import build_excel_export
from utils.form_ui import render_form_header, render_stage_status
from utils.logic import build_pra_output, is_risk_assessed
from utils.workflow import stage_results


_RISK_BG = {
    "Extreme": "#FFEBEE",
    "High": "#FFF3E0",
    "Medium": "#FFFDE7",
    "Low": "#E8F5E9",
}
_RISK_CLR = {
    "Extreme": "#C00000",
    "High": "#E64A19",
    "Medium": "#F57F17",
    "Low": "#2E7D32",
}


def render():
    risk_data = st.session_state.get("risk_register", [])

    if not risk_data:
        st.info(
            "⬅️ Complete **Tab 7 – Risk Register** first."
        )
        return

    stages = stage_results(dict(st.session_state))
    risk_stage = next(
        stage for stage in stages
        if stage.key == "risk_register"
    )

    if not risk_stage.complete:
        render_form_header(
            "PRA OUTPUT",
            "PRA Not Ready",
            "The PRA is a read-only report generated from the Risk Register. "
            "Complete the remaining risk assessment and governance fields before "
            "using this output as a study deliverable.",
        )
        render_stage_status(
            label="PRA readiness",
            value=risk_stage.guidance,
            tone="warning",
        )
        st.info(
            "Return to **Tab 7 → Risk Register** to complete the outstanding fields."
        )
        return

    render_form_header(
        "PRA OUTPUT",
        "PRA Output",
        "Read-only summary generated from the saved Risk Register. "
        "Edit source data in Tab 7; this page never creates a second editable copy.",
    )

    render_stage_status(
        label="PRA readiness",
        value="All mandatory Risk Register assessment and governance fields are complete.",
        tone="success",
    )

    st.caption(
        f"Methodology: {st.session_state.get('methodology_version', 'SURM-2026.01')} · "
        f"Study revision: {st.session_state.get('study_revision', 0)}"
    )

    pra_df = build_pra_output(pd.DataFrame(risk_data))

    if pra_df.empty:
        st.warning("No PRA data to display.")
        return

    st.markdown(
        '<div class="surm-section-header">Executive Summary</div>',
        unsafe_allow_html=True,
    )
    st.info(
        build_executive_summary(dict(st.session_state))
    )

    st.markdown(
        '<div class="surm-section-header">📊 Risk Portfolio Summary</div>',
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(4)
    for column, level in zip(
        metric_cols,
        ["Extreme", "High", "Medium", "Low"],
    ):
        count = int(
            (
                pra_df.get(
                    "Risk Rating",
                    pd.Series(dtype=str),
                ) == level
            ).sum()
        )
        column.metric(level, count)

    st.markdown(
        '<div class="surm-section-header">📄 PRA Output Table</div>',
        unsafe_allow_html=True,
    )

    def style_risk_rating(value):
        background = _RISK_BG.get(value, "")
        color = _RISK_CLR.get(value, "")
        if background:
            return (
                f"background-color:{background};"
                f"color:{color};font-weight:700;"
            )
        return ""

    styled = (
        pra_df.style.map(
            style_risk_rating,
            subset=["Risk Rating"],
        )
        if "Risk Rating" in pra_df.columns
        else pra_df.style
    )

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        height=480,
    )

    bowtie_register = st.session_state.get("bowtie_register", {})
    if bowtie_register:
        st.markdown(
            '<div class="surm-section-header">📐 Bowtie Risk Reporting</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Read-only Bowtie diagrams registered against each Risk ID. "
            "The diagram is sourced from Tab 7 and does not recalculate risk."
        )
        for risk_row in risk_data:
            risk_id = str(risk_row.get("risk_id", "")).strip()
            document = bowtie_register.get(risk_id)
            if not document:
                continue
            with st.expander(
                f'{risk_id} — {risk_row.get("Risk", "Risk")}',
                expanded=False,
            ):
                render_bowtie_readonly(
                    document,
                    key=f"pra_bowtie_{risk_id}_{st.session_state.get('study_id', 'new')}",
                    height=720,
                )

    st.divider()
    st.markdown(
        '<div class="surm-section-header">📥 Export</div>',
        unsafe_allow_html=True,
    )

    export_col, info_col = st.columns([1, 3])

    with export_col:
        workbook = build_excel_export()
        field = st.session_state.get("field_name", "") or "Output"
        st.download_button(
            "📥 Download Full SURM Workbook (.xlsx)",
            data=workbook,
            file_name=f"SURM_{field.replace(' ', '_')}_Complete.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

    with info_col:
        st.markdown(
            """
            <div style="background:#E8F5E9;border-left:4px solid #1F6B3A;
            padding:10px 14px;border-radius:0 4px 4px 0;font-size:12px;
            color:#2E7D32;margin-top:4px;">
                📄 The workbook exports the current canonical study outputs,
                including governance metadata and the Risk Register.
            </div>
            """,
            unsafe_allow_html=True,
        )

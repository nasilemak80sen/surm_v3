"""
Tab 3 — Impact Assessment.

This form preserves the existing weighted scoring methodology while requiring
the user to explicitly choose a degree of uncertainty before the assessment
can progress.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.form_ui import render_form_header, render_save_hint, render_stage_status
from utils.logic import (
    compute_combined_rating,
    compute_weighted_score,
    score_to_bin,
)
from utils.persistence import save_session
from utils.workflow import mark_stage_changed


DEG_OPTIONS = ["", "H", "M", "L"]
RATING_OPTIONS = ["H", "M", "L", "NA"]


def render():
    selected = [
        uncertainty
        for uncertainty in st.session_state["uncertainties"]
        if uncertainty.get("selected")
    ]
    decisions = [
        decision
        for decision in st.session_state.get("key_decisions", [])
        if str(decision.get("Key Decision", "")).strip()
    ]

    if not selected:
        st.info(
            "⬅️ Go to **Tab 1** and select at least one uncertainty first."
        )
        return

    if not decisions:
        st.info(
            "⬅️ Go to **Tab 2** and define at least one key decision first."
        )
        return

    render_form_header(
        "STEP 3 OF 7",
        "Impact Assessment",
        "Rate how uncertain each topic is and how strongly it can affect the "
        "decisions that matter to the project. The weighted impact calculation "
        "and combined rating are calculated for you after saving.",
        next_step="Key Uncertainties",
    )

    saved_assessment = st.session_state.get("impact_assessment", [])
    saved_by_name = {
        row["Uncertainty"]: row
        for row in saved_assessment
        if isinstance(row, dict) and row.get("Uncertainty")
    }

    unresolved_degree = [
        uncertainty["name"]
        for uncertainty in selected
        if str(
            saved_by_name.get(
                uncertainty["name"],
                {},
            ).get("Degree of Uncertainty", "")
        ).strip().upper()
        not in {"H", "M", "L"}
    ]

    if unresolved_degree:
        render_stage_status(
            label="Assessment status",
            value=(
                f"{len(unresolved_degree)} uncertainties still need an explicit "
                "Degree of Uncertainty. New rows are intentionally blank so the "
                "form does not make an assessment on your behalf."
            ),
            tone="warning",
        )
    else:
        render_stage_status(
            label="Assessment status",
            value=f"{len(selected)} uncertainties have an explicit degree rating.",
            tone="success",
        )

    st.info(
        "Use **NA** when a decision genuinely does not apply. NA is excluded "
        "from the weighted denominator, preserving the existing SURM scoring rule."
    )

    decision_names = [
        decision["Key Decision"]
        for decision in decisions
    ]

    rows = []
    for uncertainty in selected:
        name = uncertainty["name"]
        existing = saved_by_name.get(name, {})
        row = {
            "uncertainty_id": uncertainty.get("uncertainty_id", ""),
            "Uncertainty": name,
            "Degree of Uncertainty": existing.get(
                "Degree of Uncertainty",
                "",
            ),
        }

        for decision_name in decision_names:
            row[decision_name] = existing.get(
                decision_name,
                "NA",
            )

        rows.append(row)

    df_in = pd.DataFrame(rows)

    st.markdown(
        '<div class="surm-section-header">📊 Impact Assessment Matrix</div>',
        unsafe_allow_html=True,
    )

    with st.form("impact_form"):
        render_save_hint(
            "Fill the assessment matrix, then click Save Assessment. "
            "Bulk buttons are useful for repeated values, but review each row "
            "before committing the study results."
        )

        button_cols = st.columns([1, 1, 1, 1, 0.5, 2])
        with button_cols[0]:
            degree_h = st.form_submit_button(
                "Degree → All H",
                help="Set every degree to High.",
            )
        with button_cols[1]:
            degree_m = st.form_submit_button(
                "Degree → All M",
                help="Set every degree to Medium.",
            )
        with button_cols[2]:
            degree_l = st.form_submit_button(
                "Degree → All L",
                help="Set every degree to Low.",
            )
        with button_cols[3]:
            impacts_na = st.form_submit_button(
                "Impacts → All NA",
                help="Reset all decision impacts to Not Applicable.",
            )
        with button_cols[5]:
            save_clicked = st.form_submit_button(
                "✅ Save Assessment",
                type="primary",
            )

        column_config = {
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
            "Degree of Uncertainty": st.column_config.SelectboxColumn(
                "Degree",
                options=DEG_OPTIONS,
                width="small",
                help="Choose H, M, or L explicitly.",
            ),
        }

        for decision_name in decision_names:
            column_config[decision_name] = st.column_config.SelectboxColumn(
                decision_name,
                options=RATING_OPTIONS,
                width="small",
                help=f"Rate the impact on '{decision_name}'.",
            )

        edited = st.data_editor(
            df_in,
            column_config=column_config,
            hide_index=True,
                use_container_width=True,
            num_rows="fixed",
            key=f"impact_editor_{st.session_state.get('study_id', 'new')}",
        )

    submitted = (
        degree_h
        or degree_m
        or degree_l
        or impacts_na
        or save_clicked
    )

    if submitted:
        data = edited.to_dict("records")

        if degree_h:
            for row in data:
                row["Degree of Uncertainty"] = "H"
        elif degree_m:
            for row in data:
                row["Degree of Uncertainty"] = "M"
        elif degree_l:
            for row in data:
                row["Degree of Uncertainty"] = "L"

        if impacts_na:
            for row in data:
                for decision_name in decision_names:
                    row[decision_name] = "NA"

        if save_clicked:
            missing_degree = [
                row["Uncertainty"]
                for row in data
                if str(
                    row.get("Degree of Uncertainty", "")
                ).strip().upper()
                not in {"H", "M", "L"}
            ]
            if missing_degree:
                st.warning(
                    "Before saving, choose a Degree of Uncertainty for: "
                    + ", ".join(missing_degree[:5])
                    + ("…" if len(missing_degree) > 5 else "")
                )
                return

        scored = []
        for row in data:
            degree = row.get("Degree of Uncertainty", "")
            score = compute_weighted_score(row, decisions)
            impact_bin = score_to_bin(score)
            combined = compute_combined_rating(
                degree,
                impact_bin,
            )

            scored.append({
                **row,
                "Impact (Weighted)": round(score, 3),
                "Impact Bin": impact_bin,
                "Combined Rating": combined,
            })

        st.session_state["impact_assessment"] = scored
        mark_stage_changed(
            st.session_state,
            "impact_assessment",
        )

        if save_clicked:
            ok = save_session(auto=False)
            if not ok:
                st.error("Assessment could not be saved.")
                return
            st.success("✅ Impact assessment saved.")
        else:
            save_session(auto=True)

        st.rerun()

    # ------------------------------------------------------------------
    # Saved score preview
    # ------------------------------------------------------------------
    saved_impact = st.session_state.get("impact_assessment", [])

    if saved_impact:
        st.markdown(
            '<div class="surm-section-header">🏆 Current Rankings</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "These scores reflect the last saved assessment. Changing upstream "
            "inputs will invalidate downstream ranking and resolution stages."
        )

        preview_rows = [
            {
                "Uncertainty": row["Uncertainty"],
                "Degree": row.get("Degree of Uncertainty", "—"),
                "Score": row.get("Impact (Weighted)", "—"),
                "Impact": row.get("Impact Bin", "—"),
                "Rating": row.get("Combined Rating", "—"),
            }
            for row in saved_impact
        ]

        preview_df = pd.DataFrame(preview_rows).sort_values(
            "Score",
            ascending=False,
        )

        def style_rating(value):
            colors = {
                "HH": "background:#C00000;color:white",
                "HM": "background:#FF4500;color:white",
                "HL": "background:#FFA500",
                "MH": "background:#FF8C00;color:white",
                "MM": "background:#FFD700",
                "ML": "background:#A5D6A7",
                "LH": "background:#FFC107",
                "LM": "background:#C8E6C9",
                "LL": "background:#00B050;color:white",
            }
            return colors.get(value, "")

        st.dataframe(
            preview_df.style.map(
                style_rating,
                subset=["Rating"],
            ),
                use_container_width=True,
            hide_index=True,
        )

        st.success(
            f"✅ {len(saved_impact)} rows saved. "
            "Proceed to **Tab 4 → Key Uncertainties**."
        )
    else:
        st.info(
            "Complete the matrix and click **Save Assessment** to calculate rankings."
        )

"""Tab 2 — Define the decisions this study needs to support."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.coercion import safe_int
from utils.form_ui import render_form_header, render_stage_status
from utils.workflow import mark_stage_changed


def _weight_value(value) -> int:
    return safe_int(value, default=0)


def _normalize_decisions(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()

    if "Weight (1-3)" not in normalized.columns:
        normalized["Weight (1-3)"] = 1

    normalized["Weight (1-3)"] = (
        pd.to_numeric(
            normalized["Weight (1-3)"],
            errors="coerce",
        )
        .fillna(1)
        .clip(1, 3)
        .astype(int)
    )

    return normalized


def render():
    render_form_header(
        "STEP 2 OF 7",
        "Key Decisions",
        "List the decisions the study needs to support. The weight you assign to "
        "each decision determines how strongly it influences the uncertainty ranking.",
        next_step="Impact Assessment",
    )

    existing_decisions = st.session_state.get("key_decisions", [])
    valid_decisions = [
        row
        for row in existing_decisions
        if isinstance(row, dict)
        and str(row.get("Key Decision", "")).strip()
    ]

    if valid_decisions:
        render_stage_status(
            label="Decision set",
            value=(
                f"{len(valid_decisions)} decisions defined. "
                "Use higher weights for decisions that matter more to the project."
            ),
            tone="success",
        )
    else:
        render_stage_status(
            label="Decision set",
            value="Define at least one key decision to unlock Impact Assessment.",
            tone="warning",
        )

    st.info(
        "Think about the decisions the study must help the team make — for example, "
        "well count, injector strategy, or WAG pattern. Keep one decision per row."
    )

    st.markdown(
        '<div class="surm-section-header">🎯 Key Project Decisions</div>',
        unsafe_allow_html=True,
    )

    before_signature = tuple(
        (
            str(row.get("decision_id", "")),
            str(row.get("Key Decision", "")).strip(),
            _weight_value(row.get("Weight (1-3)", 0)),
            str(row.get("Description", "") or "").strip(),
        )
        for row in existing_decisions
        if isinstance(row, dict)
    )

    df = pd.DataFrame(existing_decisions)
    if df.empty:
        df = pd.DataFrame(
            [{
                "decision_id": "DEC-001",
                "Key Decision": "",
                "Weight (1-3)": 1,
                "Description": "",
            }]
        )

    # Backfill the durable decision ID into older studies.
    if "decision_id" not in df.columns:
        df.insert(
            0,
            "decision_id",
            [
                f"DEC-{index:03d}"
                for index in range(1, len(df) + 1)
            ],
        )
    else:
        for index in range(len(df)):
            if not str(df.at[index, "decision_id"] or "").strip():
                df.at[index, "decision_id"] = f"DEC-{index + 1:03d}"

    df = _normalize_decisions(df)

    editor_key = f"kd_editor_{st.session_state.get('study_id', 'new')}"

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "decision_id": st.column_config.TextColumn(
                "Decision ID",
                width="small",
                disabled=True,
            ),
            "Key Decision": st.column_config.TextColumn(
                "Key Decision",
                width="large",
                help="What decision will this study help the team make?",
            ),
            "Weight (1-3)": st.column_config.NumberColumn(
                "Weight (1–3)",
                min_value=1,
                max_value=3,
                step=1,
                format="%d",
                help="1 = Low importance, 2 = Medium, 3 = High importance.",
            ),
            "Description": st.column_config.TextColumn(
                "Description",
                width="large",
                help="Brief context so other reviewers understand the decision.",
            ),
        },
        hide_index=True,
        key=editor_key,
    )

    normalized = _normalize_decisions(edited)

    # Preserve current responsive behaviour: edits are immediately reflected
    # in the workspace. The workflow validator decides when the stage is ready.
    updated_records = normalized.to_dict("records")
    st.session_state["key_decisions"] = updated_records
    after_signature = tuple(
        (
            str(row.get("decision_id", "")),
            str(row.get("Key Decision", "")).strip(),
            _weight_value(row.get("Weight (1-3)", 0)),
            str(row.get("Description", "") or "").strip(),
        )
        for row in updated_records
    )
    if before_signature != after_signature:
        mark_stage_changed(st.session_state, "key_decisions")

    if st.button(
        "Remove Empty Decision Rows",
        key="remove_empty_decision_rows",
        help="Remove blank rows created by the dynamic editor.",
    ):
        cleaned = [
            row
            for row in st.session_state["key_decisions"]
            if str(row.get("Key Decision") or "").strip()
        ]
        st.session_state["key_decisions"] = cleaned or [{
            "decision_id": "DEC-001",
            "Key Decision": "",
            "Weight (1-3)": 1,
            "Description": "",
        }]
        st.rerun()

    st.divider()

    if not normalized.empty:
        metric_cols = st.columns(3)
        metric_cols[0].metric(
            "Decisions Defined",
            sum(
                bool(str(row.get("Key Decision", "")).strip())
                for row in normalized.to_dict("records")
            ),
        )
        metric_cols[1].metric(
            "Highest Weight",
            int(normalized["Weight (1-3)"].max()),
        )
        metric_cols[2].metric(
            "Total Weight",
            int(normalized["Weight (1-3)"].sum()),
        )

        st.markdown(
            '<div class="surm-section-header">⚖️ Weight Distribution</div>',
            unsafe_allow_html=True,
        )

        for _, row in normalized.iterrows():
            decision_name = str(row.get("Key Decision", "")).strip()
            if not decision_name:
                continue

            weight = _weight_value(row.get("Weight (1-3)", 0))
            bar_color = (
                "#1F6B3A"
                if weight == 3
                else "#FFD700"
                if weight == 2
                else "#CCC"
            )

            st.markdown(
                f"""
                <div style="display:flex;align-items:center;margin:5px 0;">
                    <div style="width:260px;font-size:12px;color:#333;
                                overflow:hidden;white-space:nowrap;
                                text-overflow:ellipsis;">
                        {decision_name}
                    </div>
                    <div style="width:{weight * 60}px;height:14px;
                                background:{bar_color};border-radius:3px;
                                margin-left:8px;"></div>
                    <div style="margin-left:8px;font-size:11px;color:#666;">
                        {"●" * weight}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

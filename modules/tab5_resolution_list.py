"""
modules/tab5_resolution_list.py

Resolution selection as a guided coverage form. Saving is always allowed so
users can work progressively, but downstream progression is blocked until
every included key uncertainty has at least one resolution or the study has
explicitly documented why it remains unresolved in a future extension.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.form_ui import render_form_header, render_save_hint, render_stage_status
from utils.persistence import save_session
from utils.workflow import mark_stage_changed


def _coverage(rows: list[dict], options: list[str]) -> tuple[int, int, list[str]]:
    covered = 0
    uncovered: list[str] = []

    for row in rows:
        name = str(row.get("Uncertainty", "")).strip()
        has_resolution = any(
            row.get(option, "") == "Y"
            for option in options
        )
        if has_resolution:
            covered += 1
        elif name:
            uncovered.append(name)

    return covered, len(rows), uncovered


def render():
    key_uncertainties = [
        row
        for row in st.session_state.get("key_uncertainties", [])
        if row.get("Include in Plan")
    ]

    if not key_uncertainties:
        st.info(
            "⬅️ Go to **Tab 4** and select at least one uncertainty "
            "to carry forward into resolution planning."
        )
        return

    options = st.session_state["_mapping"]["resolution_options"]

    render_form_header(
        "STEP 5 OF 7",
        "Resolution List",
        "For each selected key uncertainty, choose the engineering studies or "
        "actions that can reduce or resolve it. Think of this page as the "
        "bridge between prioritisation and the actual workplan.",
        next_step="Resolution Planner",
    )

    saved_state = st.session_state.get("resolution_list", {})
    rows = []

    for uncertainty in key_uncertainties:
        name = uncertainty["Uncertainty"]
        existing = saved_state.get(name, {})
        row = {
            "uncertainty_id": uncertainty.get("uncertainty_id", ""),
            "Uncertainty": name,
            "Rating": uncertainty["Combined Rating"],
        }
        for option in options:
            row[option] = existing.get(option, "")
        rows.append(row)

    df_in = pd.DataFrame(rows)

    covered, total, uncovered = _coverage(rows, options)

    if uncovered:
        render_stage_status(
            label="Resolution coverage",
            value=(
                f"{covered} of {total} key uncertainties covered. "
                f"{len(uncovered)} still need a resolution selection."
            ),
            tone="warning",
        )
    else:
        render_stage_status(
            label="Resolution coverage",
            value=f"All {total} key uncertainties have at least one resolution action.",
            tone="success",
        )

    st.info(
        "A resolution action can address more than one uncertainty. "
        "Use the matrix to make those relationships explicit."
    )

    st.markdown(
        '<div class="surm-section-header">🛠️ Resolution Alternatives Matrix</div>',
        unsafe_allow_html=True,
    )

    with st.form("res_list_form"):
        render_save_hint(
            "Use the bulk controls for a quick starting point, refine the matrix, "
            "then save your selections."
        )

        button_cols = st.columns([1, 1, 0.5, 3])
        with button_cols[0]:
            select_all = st.form_submit_button(
                "✅ Y for All",
                help="Mark every resolution option for every listed uncertainty.",
            )
        with button_cols[1]:
            clear_all = st.form_submit_button(
                "☐ Clear All",
                help="Clear every resolution selection.",
            )
        with button_cols[3]:
            save_clicked = st.form_submit_button(
                "💾 Save Selections",
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
            "Rating": st.column_config.TextColumn(
                "Rating",
                width="small",
                disabled=True,
            ),
        }

        for option in options:
            column_config[option] = st.column_config.SelectboxColumn(
                option,
                options=["", "Y"],
                width="small",
                help=f"Select Y when '{option}' will address this uncertainty.",
            )

        edited = st.data_editor(
            df_in,
            column_config=column_config,
            hide_index=True,
            width="stretch",
            num_rows="fixed",
            key=f"res_list_editor_{st.session_state.get('study_id', 'new')}",
        )

    if select_all or clear_all or save_clicked:
        data = edited.to_dict("records")

        if select_all:
            for row in data:
                for option in options:
                    row[option] = "Y"
        elif clear_all:
            for row in data:
                for option in options:
                    row[option] = ""

        resolution_dict = {}
        for row in data:
            name = row["Uncertainty"]
            resolution_dict[name] = {
                option: row.get(option, "")
                for option in options
            }

        st.session_state["resolution_list"] = resolution_dict
        mark_stage_changed(st.session_state, "resolution_list")
        save_session(auto=not save_clicked)

        covered, total, uncovered = _coverage(data, options)
        if uncovered:
            st.warning(
                f"{len(uncovered)} key uncertainties still have no selected "
                "resolution. You can continue editing here, but Tab 6 will "
                "remain unavailable until coverage is complete."
            )
        else:
            st.success(
                f"✅ Resolution coverage complete for all {total} key uncertainties."
            )

        st.rerun()

    # ------------------------------------------------------------------
    # Coverage summary from persisted state
    # ------------------------------------------------------------------
    persisted_rows = []
    for uncertainty in key_uncertainties:
        name = uncertainty["Uncertainty"]
        existing = saved_state.get(name, {})
        persisted_rows.append({
            "Uncertainty": name,
            "Rating": uncertainty["Combined Rating"],
            **existing,
        })

    persisted_covered, persisted_total, persisted_uncovered = _coverage(
        persisted_rows,
        options,
    )

    st.divider()
    st.markdown(
        '<div class="surm-section-header">📈 Coverage Summary</div>',
        unsafe_allow_html=True,
    )

    summary_cols = st.columns(3)
    summary_cols[0].metric("Key Uncertainties", persisted_total)
    summary_cols[1].metric("Covered", persisted_covered)
    summary_cols[2].metric("Uncovered", len(persisted_uncovered))

    coverage_rows = []
    for option in options:
        count = sum(
            1
            for row in persisted_rows
            if row.get(option) == "Y"
        )
        if count:
            coverage_rows.append({
                "Resolution Action": option,
                "Uncertainties Addressed": count,
            })

    if coverage_rows:
        coverage_df = pd.DataFrame(coverage_rows).sort_values(
            "Uncertainties Addressed",
            ascending=False,
        )

        for _, row in coverage_df.iterrows():
            percentage = int(
                row["Uncertainties Addressed"]
                / max(persisted_total, 1)
                * 100
            )
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;margin:5px 0;">
                    <div style="width:280px;font-size:12px;overflow:hidden;
                                white-space:nowrap;text-overflow:ellipsis;">
                        {row["Resolution Action"]}
                    </div>
                    <div style="width:{max(2, percentage * 2)}px;max-width:220px;
                                height:10px;background:#1F6B3A;border-radius:3px;
                                margin:0 8px;"></div>
                    <div style="font-size:11px;color:#555;">
                        {int(row["Uncertainties Addressed"])} ({percentage}%)
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if persisted_uncovered:
        st.warning(
            "Still uncovered: "
            + ", ".join(persisted_uncovered[:4])
            + ("…" if len(persisted_uncovered) > 4 else "")
        )
    else:
        st.success(
            "✅ Every selected key uncertainty has at least one resolution action. "
            "You are ready for **Tab 6 → Resolution Planner**."
        )

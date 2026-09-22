"""Tab 5 — Resolution List: action selection with live coverage."""

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
        has_resolution = any(row.get(option, "") == "Y" for option in options)
        if has_resolution:
            covered += 1
        elif name:
            uncovered.append(name)
    return covered, len(rows), uncovered


def render():
    key_uncertainties = [
        row for row in st.session_state.get("key_uncertainties", [])
        if row.get("Include in Plan")
    ]

    if not key_uncertainties:
        st.info("⬅️ Go to **Tab 4** and select at least one uncertainty to carry into resolution planning.")
        return

    options = st.session_state["_mapping"]["resolution_options"]
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

    render_form_header(
        "STEP 5 OF 7",
        "Resolution List",
        "Map each selected uncertainty to one or more engineering actions. Coverage is shown beside the matrix.",
        next_step="Resolution Planner",
    )

    left, right = st.columns([1.8, 1], gap="large")

    with left:
        st.markdown("**Resolution alternatives**")
        st.caption("Select Y where an action genuinely addresses the uncertainty.")
        render_save_hint(
            "Resolution mappings are a session draft until you click Save selections. "
            "Bulk actions apply the draft but do not persist it."
        )
        with st.form("res_list_form", enter_to_submit=False):
            button_cols = st.columns([1, 1, 2.2])
            with button_cols[0]:
                select_all = st.form_submit_button("Y for all", key="res_select_all")
            with button_cols[1]:
                clear_all = st.form_submit_button("Clear all", key="res_clear_all")
            with button_cols[2]:
                save_clicked = st.form_submit_button("Save selections", key="save_resolution_list", type="primary")

            column_config = {
                "uncertainty_id": st.column_config.TextColumn("ID", width="small", disabled=True),
                "Uncertainty": st.column_config.TextColumn("Uncertainty", width="large", disabled=True),
                "Rating": st.column_config.TextColumn("Rating", width="small", disabled=True),
            }
            for option in options:
                column_config[option] = st.column_config.SelectboxColumn(
                    option,
                    options=["", "Y"],
                    width="small",
                    help=f"Select Y when '{option}' will address this uncertainty.",
                )

            edited = st.data_editor(
                pd.DataFrame(rows),
                column_config=column_config,
                hide_index=True,
                use_container_width=True,
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

            resolution_dict = {
                row["Uncertainty"]: {option: row.get(option, "") for option in options}
                for row in data
            }
            previous = st.session_state.get("resolution_list", {})
            st.session_state["resolution_list"] = resolution_dict

            if previous != resolution_dict:
                mark_stage_changed(st.session_state, "resolution_list")

            if save_clicked:
                if not st.session_state.get("project_name", "").strip():
                    st.warning("Enter a Project Name on Overview before saving the resolution mapping.")
                    return
                ok = save_session(auto=False)
                if not ok:
                    st.error("Resolution mapping could not be saved.")
                    return
                st.success("✅ Resolution selections saved.")
            else:
                st.info("Draft updated. Click **Save selections** to persist the resolution mapping.")
            st.rerun()

    with right:
        persisted_rows = []
        for row in key_uncertainties:
            name = row["Uncertainty"]
            persisted_rows.append({
                "Uncertainty": name,
                "Rating": row["Combined Rating"],
                **saved_state.get(name, {}),
            })

        covered, total, uncovered = _coverage(persisted_rows, options)
        st.markdown("**Coverage**")
        st.metric("Covered", f"{covered}/{total}")
        st.progress(covered / max(total, 1))

        if uncovered:
            render_stage_status(
                label="Next step",
                value=f"{len(uncovered)} uncertainty{'ies' if len(uncovered) != 1 else ''} still need an action.",
                tone="warning",
            )
        else:
            render_stage_status(
                label="Ready",
                value="Every selected uncertainty has at least one resolution action.",
                tone="success",
            )

        action_counts = []
        for option in options:
            count = sum(1 for row in persisted_rows if row.get(option) == "Y")
            if count:
                action_counts.append((option, count))

        action_counts.sort(key=lambda item: item[1], reverse=True)
        if action_counts:
            st.markdown("**Actions addressing the study**")
            for option, count in action_counts[:8]:
                st.markdown(
                    f'<div class="surm-guide-row"><strong>{option}</strong><span>{count} of {total} uncertainties</span></div>',
                    unsafe_allow_html=True,
                )

        if uncovered:
            st.caption("Still uncovered: " + ", ".join(uncovered[:4]) + ("…" if len(uncovered) > 4 else ""))

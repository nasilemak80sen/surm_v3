"""
modules/tab6_resolution_planner.py

Resolution workplan form. This page deliberately separates:
1) generated resolution actions,
2) the user's scheduling/ownership decisions, and
3) the progress view.

Existing planner fields and statuses are preserved.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.form_ui import render_form_header, render_save_hint, render_stage_status
from utils.logic import build_resolution_planner
from utils.persistence import save_session


_STATUS_OPTIONS = [
    "Open",
    "Under Assessment",
    "Resolution Planned",
    "In Progress",
    "Resolved",
    "Closed",
]


def _build_resolution_dataframe(
    ku_list: list[dict],
    resolution_list: dict,
) -> pd.DataFrame:
    rows = []

    for uncertainty in ku_list:
        row = {
            "Uncertainty": uncertainty["Uncertainty"],
            "Rating": uncertainty["Combined Rating"],
        }
        row.update(
            resolution_list.get(
                uncertainty["Uncertainty"],
                {},
            )
        )
        rows.append(row)

    return pd.DataFrame(rows)


def _planner_quality(rows: list[dict]) -> tuple[int, int]:
    """Return count of assigned workplan rows and rows missing owner."""
    workplan = [
        row for row in rows
        if row.get("Part of Workplan")
    ]
    missing_owner = sum(
        1
        for row in workplan
        if not str(row.get("Action Owner", "") or "").strip()
    )
    return len(workplan), missing_owner


def render():
    resolution_list = st.session_state.get("resolution_list", {})
    key_uncertainties = [
        row
        for row in st.session_state.get("key_uncertainties", [])
        if row.get("Include in Plan")
    ]

    if not resolution_list:
        st.info(
            "⬅️ Go to **Tab 5** and select resolution actions first."
        )
        return

    render_form_header(
        "STEP 6 OF 7",
        "Resolution Planner",
        "Turn the selected resolution actions into a practical workplan. "
        "Assign what will be done, who owns it, when it is needed, and how progress "
        "will be tracked.",
        next_step="Risk Register",
    )

    st.info(
        "Start with the actions generated from Tab 5. Use **In Workplan?** to "
        "identify the actions the team intends to execute."
    )

    # ------------------------------------------------------------------
    # Refresh generated actions
    # ------------------------------------------------------------------
    col_button, col_hint = st.columns([1, 3])
    with col_button:
        refresh_planner = st.button(
            "🔄 Update Planner from Tab 5",
            type="primary",
            key="update_resolution_planner",
            use_container_width=True,
        )
    with col_hint:
        st.caption(
            "Updating refreshes the action list from Tab 5 while preserving "
            "existing planner fields for matching resolution actions."
        )

    if refresh_planner:
        if not key_uncertainties:
            st.warning(
                "No key uncertainties are currently included in the plan. "
                "Return to Tab 4 and review the selection."
            )
            return

        resolution_df = _build_resolution_dataframe(
            key_uncertainties,
            resolution_list,
        )
        planner_df = build_resolution_planner(resolution_df)

        if planner_df.empty:
            st.warning(
                "No resolution actions were selected in Tab 5. "
                "Return there and mark at least one action."
            )
            return

        st.session_state["resolution_planner"] = planner_df.to_dict("records")
        st.session_state["risk_register"] = []
        st.session_state["pra_output"] = []
        save_session(auto=True)
        st.success(
            f"✅ {len(planner_df)} resolution actions loaded into the planner."
        )
        st.rerun()

    planner_data = st.session_state.get("resolution_planner", [])
    if not planner_data:
        render_stage_status(
            label="Planner status",
            value="No actions loaded yet. Update the planner from Tab 5 to begin.",
            tone="info",
        )
        return

    workplan_count, missing_owner = _planner_quality(planner_data)

    if not workplan_count:
        render_stage_status(
            label="Workplan status",
            value="No actions are currently marked as part of the workplan.",
            tone="warning",
        )
    elif missing_owner:
        render_stage_status(
            label="Workplan status",
            value=(
                f"{workplan_count} actions are in the workplan; "
                f"{missing_owner} still need an Action Owner."
            ),
            tone="warning",
        )
    else:
        render_stage_status(
            label="Workplan status",
            value=f"{workplan_count} workplan actions have owners assigned.",
            tone="success",
        )

    st.markdown(
        '<div class="surm-section-header">📅 Resolution Action Plan</div>',
        unsafe_allow_html=True,
    )

    df_in = pd.DataFrame(planner_data)

    with st.form("planner_form"):
        render_save_hint(
            "Bulk buttons and table edits are applied together. Save before leaving this page."
        )

        button_cols = st.columns([1, 1, 0.5, 3])
        with button_cols[0]:
            add_all = st.form_submit_button(
                "✅ Add All to Workplan",
                help="Mark every generated action as part of the workplan.",
            )
        with button_cols[1]:
            remove_all = st.form_submit_button(
                "☐ Remove All from Workplan",
                help="Remove every generated action from the workplan.",
            )
        with button_cols[3]:
            save_clicked = st.form_submit_button(
                "💾 Save Planner",
                type="primary",
            )

        edited = st.data_editor(
            df_in,
            column_config={
                "resolution_id": st.column_config.TextColumn(
                    "ID",
                    width="small",
                    disabled=True,
                ),
                "#": st.column_config.NumberColumn(
                    "#",
                    width="small",
                    disabled=True,
                ),
                "Resolution Action": st.column_config.TextColumn(
                    "Resolution Action",
                    width="medium",
                    disabled=True,
                ),
                "Associated Uncertainties": st.column_config.TextColumn(
                    "Addresses",
                    width="large",
                    disabled=True,
                ),
                "Ratings": st.column_config.TextColumn(
                    "Ratings",
                    width="small",
                    disabled=True,
                ),
                "Description": st.column_config.TextColumn(
                    "Description of Work",
                    width="large",
                ),
                "Duration (months)": st.column_config.NumberColumn(
                    "Duration (mths)",
                    min_value=0,
                    max_value=60,
                    step=1,
                ),
                "Resources": st.column_config.TextColumn(
                    "Resources",
                ),
                "Constraints": st.column_config.TextColumn(
                    "Constraints",
                ),
                "Start Date": st.column_config.TextColumn(
                    "Start Date",
                    help="DD/MM/YYYY",
                    width="small",
                ),
                "Required Completion": st.column_config.TextColumn(
                    "Completion Date",
                    help="DD/MM/YYYY",
                    width="small",
                ),
                "Progress (0-1)": st.column_config.NumberColumn(
                    "Progress",
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                ),
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=_STATUS_OPTIONS,
                ),
                "Action Owner": st.column_config.TextColumn(
                    "Owner",
                ),
                "Part of Workplan": st.column_config.CheckboxColumn(
                    "In Workplan?",
                ),
                "Remarks": st.column_config.TextColumn(
                    "Remarks",
                    width="large",
                ),
            },
            hide_index=True,
            width="stretch",
            num_rows="fixed",
            key=f"planner_editor_{st.session_state.get('study_id', 'new')}",
        )

    if add_all or remove_all or save_clicked:
        data = edited.to_dict("records")

        if add_all:
            for row in data:
                row["Part of Workplan"] = True
        elif remove_all:
            for row in data:
                row["Part of Workplan"] = False

        # IMPORTANT: persist the local edited dataframe for every submit path.
        # The old Add All branch changed only the local dataframe and then
        # reran, which discarded the bulk selection.
        st.session_state["resolution_planner"] = data
        st.session_state["risk_register"] = []
        st.session_state["pra_output"] = []

        ok = save_session(auto=not save_clicked)
        if not ok:
            st.error("Planner could not be saved.")
            return

        if add_all:
            st.success("✅ All resolution actions were added to the workplan.")
        elif remove_all:
            st.success("✅ All resolution actions were removed from the workplan.")
        else:
            st.success("✅ Planner saved.")

        st.rerun()

    # ------------------------------------------------------------------
    # Progress dashboard
    # ------------------------------------------------------------------
    planner_data = st.session_state.get("resolution_planner", [])
    workplan_rows = [
        row for row in planner_data
        if row.get("Part of Workplan")
    ]

    overall = (
        sum(
            float(row.get("Progress (0-1)", 0) or 0)
            for row in workplan_rows
        )
        / max(len(workplan_rows), 1)
    )

    st.markdown(
        '<div class="surm-section-header">📊 Progress Dashboard</div>',
        unsafe_allow_html=True,
    )

    if not workplan_rows:
        st.info(
            "Mark at least one action as **In Workplan?** to see workplan progress."
        )
        return

    progress_pct = int(overall * 100)
    progress_tone = (
        "#1F6B3A"
        if progress_pct >= 80
        else "#C89B00"
        if progress_pct >= 40
        else "#D97706"
    )

    st.markdown(
        f"""
        <div style="background:#FFFFFF;border:1px solid #E0E0E0;
                    border-radius:8px;padding:14px 18px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;
                        align-items:center;margin-bottom:8px;">
                <span style="font-size:13px;font-weight:700;color:#1F6B3A;">
                    Overall Workplan Progress
                </span>
                <span style="font-size:18px;font-weight:700;">
                    {progress_pct}%
                </span>
            </div>
            <div style="background:#E8E8E8;border-radius:6px;height:12px;">
                <div style="width:{progress_pct}%;background:{progress_tone};
                            height:12px;border-radius:6px;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for row in workplan_rows:
        progress = float(row.get("Progress (0-1)", 0) or 0)
        percentage = int(progress * 100)
        label = str(row.get("Resolution Action", ""))[:55]
        owner = str(row.get("Action Owner", "") or "Unassigned")
        duration = str(row.get("Duration (months)", "") or "—")

        if percentage >= 100:
            status_class = "badge-closed"
            status_label = "Complete"
        elif percentage > 0:
            status_class = "badge-progress"
            status_label = "In Progress"
        else:
            status_class = "badge-hold"
            status_label = "Not Started"

        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #EEEEEE;
                        border-radius:6px;padding:10px 14px;margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;
                            align-items:center;margin-bottom:5px;">
                    <span style="font-size:12px;font-weight:600;">
                        {label}
                    </span>
                    <div style="display:flex;gap:8px;align-items:center;">
                        <span class="badge {status_class}" style="font-size:10px;">
                            {status_label}
                        </span>
                        <span style="font-size:11px;color:#888;">
                            {owner}
                        </span>
                        <span style="font-size:11px;color:#888;">
                            {duration} mths
                        </span>
                        <span style="font-size:12px;font-weight:700;
                                     min-width:36px;text-align:right;">
                            {percentage}%
                        </span>
                    </div>
                </div>
                <div style="background:#EFEFEF;border-radius:4px;height:8px;">
                    <div style="width:{percentage}%;background:#1F6B3A;
                                height:8px;border-radius:4px;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

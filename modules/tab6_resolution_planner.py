"""Tab 6 — Resolution Planner: workplan editing with live execution summary."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.coercion import safe_float
from utils.form_ui import render_form_header, render_save_hint, render_stage_status
from utils.logic import build_resolution_planner
from utils.persistence import save_session
from utils.workflow import mark_stage_changed


_STATUS_OPTIONS = ["Open", "Under Assessment", "Resolution Planned", "In Progress", "Resolved", "Closed"]
_OTHER_OWNER_OPTION = "Others"


def build_owner_options(session: dict | None = None) -> list[str]:
    """Build planner owner dropdown options from Team names plus controlled custom owners."""
    source = session if session is not None else st.session_state
    names: list[str] = []
    for member in source.get("team_members", []) or []:
        if not isinstance(member, dict):
            continue
        name = str(member.get("Name", "") or "").strip()
        if name and name not in names:
            names.append(name)

    for row in source.get("resolution_planner", []) or []:
        if not isinstance(row, dict):
            continue
        for key in ("Action Owner", "Other Owner Name"):
            name = str(row.get(key, "") or "").strip()
            if name and name != _OTHER_OWNER_OPTION and name not in names:
                names.append(name)

    return [""] + names + [_OTHER_OWNER_OPTION]


def _display_owner(row: dict) -> str:
    owner = str(row.get("Action Owner", "") or "").strip()
    if owner == _OTHER_OWNER_OPTION:
        return str(row.get("Other Owner Name", "") or "").strip()
    return owner


def _normalize_owner_rows(rows: list[dict]) -> list[dict]:
    """Resolve the controlled Others option into the actual custom owner name."""
    normalized = []
    for row in rows:
        next_row = dict(row)
        if str(next_row.get("Action Owner", "") or "").strip() == _OTHER_OWNER_OPTION:
            custom_owner = str(next_row.get("Other Owner Name", "") or "").strip()
            next_row["Action Owner"] = custom_owner
        next_row.pop("Other Owner Name", None)
        normalized.append(next_row)
    return normalized


def _build_resolution_dataframe(ku_list: list[dict], resolution_list: dict) -> pd.DataFrame:
    rows = []
    for uncertainty in ku_list:
        row = {
            "Uncertainty": uncertainty["Uncertainty"],
            "Rating": uncertainty["Combined Rating"],
        }
        row.update(resolution_list.get(uncertainty["Uncertainty"], {}))
        rows.append(row)
    return pd.DataFrame(rows)


def _planner_structure_signature(rows: list[dict]) -> tuple:
    """Return the part of planner state that can change downstream risk structure."""
    return tuple(
        (
            str(row.get("resolution_id", "")),
            str(row.get("Resolution Action", "")),
            str(row.get("Associated Uncertainties", "")),
            str(row.get("Ratings", "")),
        )
        for row in rows
        if isinstance(row, dict)
    )


def _planner_quality(rows: list[dict]) -> tuple[int, int]:
    workplan = [row for row in rows if row.get("Part of Workplan")]
    missing_owner = sum(
        1 for row in workplan
        if not _display_owner(row)
    )
    return len(workplan), missing_owner


def _planner_status_counts(rows: list[dict]) -> pd.DataFrame:
    counts = {status: 0 for status in _STATUS_OPTIONS}
    for row in rows:
        if not row.get("Part of Workplan"):
            continue
        status = str(row.get("Status", "Open") or "Open")
        counts[status] = counts.get(status, 0) + 1
    return pd.DataFrame({"Workplan actions": list(counts.values())}, index=list(counts.keys()))


def render():
    resolution_list = st.session_state.get("resolution_list", {})
    key_uncertainties = [
        row for row in st.session_state.get("key_uncertainties", [])
        if row.get("Include in Plan")
    ]

    if not resolution_list:
        st.info("⬅️ Go to **Tab 5** and select resolution actions first.")
        return

    render_form_header(
        "STEP 6 OF 7",
        "Resolution Planner",
        "Turn selected resolution actions into an owned, dated and trackable workplan.",
        next_step="Risk Register",
    )

    planner_data = st.session_state.get("resolution_planner", [])
    workplan_rows = [row for row in planner_data if row.get("Part of Workplan")]
    workplan_count, missing_owner = _planner_quality(planner_data)
    overall = (
        sum(safe_float(row.get("Progress (0-1)", 0), default=0.0) for row in workplan_rows)
        / max(len(workplan_rows), 1)
    )
    progress_pct = int(overall * 100) if workplan_rows else 0
    resolved_count = sum(
        1
        for row in workplan_rows
        if str(row.get("Status", "")).strip() in {"Resolved", "Closed"}
    )

    # Keep the KPI cards in a single row. They are the executive signal; the
    # detailed workplan and status chart get the full page width below them.
    metric_cols = st.columns(4)
    metric_cols[0].metric("Workplan", workplan_count)
    metric_cols[1].metric("Missing owners", missing_owner)
    metric_cols[2].metric("Average progress", f"{progress_pct}%")
    metric_cols[3].metric("Resolved / closed", resolved_count)

    if workplan_count and not missing_owner:
        render_stage_status(
            label="Ready",
            value=f"{workplan_count} owned workplan actions are ready for risk management.",
            tone="success",
        )
    elif workplan_count:
        render_stage_status(
            label="Action needed",
            value=f"{missing_owner} workplan action(s) still need an owner.",
            tone="warning",
        )
    else:
        render_stage_status(
            label="Action needed",
            value="Mark at least one action as part of the workplan.",
            tone="warning",
        )

    refresh_col, hint_col = st.columns([1, 4])
    with refresh_col:
        refresh_planner = st.button(
            "Update from Tab 5",
            type="secondary",
            key="update_resolution_planner",
            use_container_width=True,
        )
    with hint_col:
        st.caption("Refresh only when Tab 5 changed. Existing planner fields are preserved for matching actions.")

    if refresh_planner:
        if not key_uncertainties:
            st.warning("No key uncertainties are currently included in the plan. Return to Tab 4.")
            return

        resolution_df = _build_resolution_dataframe(key_uncertainties, resolution_list)
        planner_df = build_resolution_planner(resolution_df)
        if planner_df.empty:
            st.warning("No resolution actions were selected in Tab 5.")
            return

        previous = st.session_state.get("resolution_planner", [])
        updated = planner_df.to_dict("records")
        st.session_state["resolution_planner"] = updated

        # Only a structural refresh should invalidate the generated risk
        # register. Owner/progress/remarks edits are execution metadata.
        if _planner_structure_signature(previous) != _planner_structure_signature(updated):
            mark_stage_changed(st.session_state, "resolution_planner")

        st.info("Planner draft updated from Tab 5. Review it, then click **Save planner** to persist.")
        st.rerun()

    planner_data = st.session_state.get("resolution_planner", [])

    if not planner_data:
        render_stage_status(
            label="Planner",
            value="No actions loaded yet. Update from Tab 5 to begin.",
            tone="info",
        )
    else:
        df_in = pd.DataFrame(planner_data)
        if "Other Owner Name" not in df_in.columns:
            df_in["Other Owner Name"] = ""
        owner_options = build_owner_options(st.session_state)
        render_save_hint(
            "Planner edits are a session draft until you click Save planner. "
            "Execution fields such as owner, dates, progress and remarks do not invalidate the risk register."
        )

        with st.form("planner_form", enter_to_submit=False):
            button_cols = st.columns([1, 1, 2.2, 3.6])
            with button_cols[0]:
                add_all = st.form_submit_button("Add all", key="planner_add_all")
            with button_cols[1]:
                remove_all = st.form_submit_button("Remove all", key="planner_remove_all")
            with button_cols[2]:
                save_clicked = st.form_submit_button(
                    "Save planner",
                    key="save_resolution_planner",
                    type="primary",
                )
            with button_cols[3]:
                st.caption("Choose an Owner from the Team roster. Select **Others** and fill **Other owner name** for an external contributor.")

            edited = st.data_editor(
                df_in,
                column_config={
                    "resolution_id": st.column_config.TextColumn("ID", width="small", disabled=True),
                    "#": st.column_config.NumberColumn("#", width="small", disabled=True),
                    "Resolution Action": st.column_config.TextColumn("Resolution Action", width="medium", disabled=True),
                    "Associated Uncertainties": st.column_config.TextColumn("Addresses", width="large", disabled=True),
                    "Ratings": st.column_config.TextColumn("Ratings", width="small", disabled=True),
                    "Description": st.column_config.TextColumn("Description of Work", width="large"),
                    "Duration (months)": st.column_config.NumberColumn("Months", min_value=0, max_value=60, step=1),
                    "Resources": st.column_config.TextColumn("Resources"),
                    "Constraints": st.column_config.TextColumn("Constraints"),
                    "Start Date": st.column_config.TextColumn("Start Date", help="DD/MM/YYYY", width="small"),
                    "Required Completion": st.column_config.TextColumn("Completion", help="DD/MM/YYYY", width="small"),
                    "Progress (0-1)": st.column_config.NumberColumn(
                        "Progress",
                        min_value=0.0,
                        max_value=1.0,
                        step=0.05,
                    ),
                    "Status": st.column_config.SelectboxColumn("Status", options=_STATUS_OPTIONS),
                    "Action Owner": st.column_config.SelectboxColumn(
                        "Owner",
                        options=owner_options,
                        help="Choose a Team member. Select Others and enter a name in Other owner name for someone outside the Team roster.",
                    ),
                    "Other Owner Name": st.column_config.TextColumn(
                        "Other owner name",
                        help="Used only when Owner is Others.",
                        width="medium",
                    ),
                    "Part of Workplan": st.column_config.CheckboxColumn("In Workplan?"),
                    "Remarks": st.column_config.TextColumn("Remarks", width="large"),
                },
                hide_index=True,
                use_container_width=True,
                num_rows="fixed",
                height=min(760, max(330, len(planner_data) * 72 + 90)),
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

            if save_clicked:
                data = _normalize_owner_rows(data)

            st.session_state["resolution_planner"] = data

            # Planner execution metadata does not alter the generated risk
            # structure, so do not clear Risk Register/PRA for owner,
            # progress, description, status or workplan-flag edits.
            if save_clicked:
                if not st.session_state.get("project_name", "").strip():
                    st.warning("Enter a Project Name on Overview before saving the planner.")
                    return
                ok = save_session(auto=False)
                if not ok:
                    st.error("Planner could not be saved.")
                    return
                st.success("✅ Resolution planner saved.")
            else:
                st.info("Draft updated. Click **Save planner** to persist the planner.")
            st.rerun()

    # Detailed reporting is intentionally below the editor.
    planner_data = st.session_state.get("resolution_planner", [])
    workplan_rows = [row for row in planner_data if row.get("Part of Workplan")]

    if workplan_rows:
        st.markdown('<div class="surm-section-header">Execution Status Mix</div>', unsafe_allow_html=True)
        st.bar_chart(
            _planner_status_counts(planner_data),
            use_container_width=True,
            height=300,
        )

        st.markdown('<div class="surm-section-header">Execution Pulse</div>', unsafe_allow_html=True)
        pulse_cols = st.columns(2)
        for index, row in enumerate(workplan_rows[:8]):
            progress = int(safe_float(row.get("Progress (0-1)", 0), default=0.0) * 100)
            owner = _display_owner(row) or "Unassigned"
            action = str(row.get("Resolution Action", "Unnamed"))[:42]
            with pulse_cols[index % 2]:
                st.markdown(
                    f'<div class="surm-guide-row"><strong>{action}</strong><span>{progress}% · {owner}</span></div>',
                    unsafe_allow_html=True,
                )

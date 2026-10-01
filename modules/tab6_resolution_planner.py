"""Tab 6 — Resolution Planner: workplan editing with live execution summary."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.coercion import safe_float
from utils.form_ui import render_form_header, render_save_hint, render_stage_status
from utils.logic import build_resolution_planner
from utils.persistence import save_session
from utils.workflow import mark_stage_changed


_STATUS_OPTIONS = ["Open", "Under Assessment", "Resolution Planned", "In Progress", "Resolved", "Closed"]
_MONTH_OPTIONS = list(range(13))
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


def _parse_planner_date(value: object):
    """Parse planner dates while accepting the UI's DD/MM/YYYY format."""
    text = str(value or "").strip()
    if not text:
        return pd.NaT
    return pd.to_datetime(text, dayfirst=True, errors="coerce")


def _prepare_planner_draft(rows: list[dict]) -> pd.DataFrame:
    """Build the user-facing draft table without changing canonical storage."""
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    if "Other Owner Name" not in df.columns:
        df["Other Owner Name"] = ""

    df["Duration (months)"] = (
        pd.to_numeric(df.get("Duration (months)", 0), errors="coerce")
        .fillna(0)
        .round()
        .clip(0, 12)
        .astype(int)
    )
    df["Progress (%)"] = (
        pd.to_numeric(df.get("Progress (0-1)", 0), errors="coerce")
        .fillna(0)
        .clip(0, 1)
        .mul(100)
        .round()
        .astype(int)
    )
    return df


def _normalize_planner_draft(rows: list[dict]) -> list[dict]:
    """Convert UI-friendly Months/Progress back to canonical study storage."""
    normalized = []
    for row in rows:
        next_row = dict(row)
        months = safe_float(next_row.get("Duration (months)", 0), default=0)
        progress_pct = safe_float(next_row.get("Progress (%)", 0), default=0)

        next_row["Duration (months)"] = max(0, min(12, int(round(months))))
        next_row["Progress (0-1)"] = max(0.0, min(1.0, progress_pct / 100.0))
        next_row.pop("Progress (%)", None)
        normalized.append(next_row)

    return normalized


def _build_live_gantt(rows: list[dict]):
    """Build a reactive Gantt figure from the current unsaved planner draft."""
    workplan = [
        row for row in rows
        if isinstance(row, dict) and row.get("Part of Workplan")
    ]
    if not workplan:
        return None, 0, []

    today = pd.Timestamp.today().normalize()
    figure = go.Figure()
    timeline_rows = []
    missing_dates = []

    for index, row in enumerate(workplan):
        action = str(row.get("Resolution Action", "") or "Unnamed action").strip()
        start = _parse_planner_date(row.get("Start Date"))
        months = max(0, min(12, int(safe_float(row.get("Duration (months)", 0), default=0))))
        progress = max(0.0, min(1.0, safe_float(row.get("Progress (0-1)", 0), default=0.0)))
        owner = str(row.get("Action Owner", "") or "").strip() or "Unassigned"
        status = str(row.get("Status", "") or "Open").strip() or "Open"
        deadline = _parse_planner_date(row.get("Required Completion"))

        if pd.isna(start):
            missing_dates.append(action)
            continue

        end = start + pd.DateOffset(months=months)
        if end <= start:
            # A 0-month action is represented as a milestone instead of a
            # zero-width rectangle that would be invisible on the chart.
            figure.add_trace(
                go.Scatter(
                    x=[start],
                    y=[action],
                    mode="markers",
                    marker={"symbol": "diamond", "size": 12},
                    customdata=[[
                        owner,
                        status,
                        "0 months",
                        f"{progress * 100:.0f}%",
                    ]],
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Milestone: %{x|%d %b %Y}<br>"
                        "Owner: %{customdata[0]}<br>"
                        "Status: %{customdata[1]}<br>"
                        "Progress: %{customdata[3]}<extra></extra>"
                    ),
                    showlegend=False,
                )
            )
        else:
            completed_end = start + (end - start) * progress

            # Planned duration.
            figure.add_shape(
                type="rect",
                x0=start,
                x1=end,
                y0=index - 0.30,
                y1=index + 0.30,
                line={"width": 0},
                fillcolor="rgba(127, 127, 127, 0.18)",
            )
            # Completed portion driven directly by the user's current draft
            # progress value.
            if progress > 0:
                figure.add_shape(
                    type="rect",
                    x0=start,
                    x1=completed_end,
                    y0=index - 0.30,
                    y1=index + 0.30,
                    line={"width": 0},
                    fillcolor="rgba(31, 107, 58, 0.80)",
                )

            figure.add_trace(
                go.Scatter(
                    x=[start + (end - start) / 2],
                    y=[action],
                    mode="markers",
                    marker={"size": 18, "opacity": 0.01},
                    customdata=[[
                        owner,
                        status,
                        f"{months} month" + ("" if months == 1 else "s"),
                        f"{progress * 100:.0f}%",
                        deadline.strftime("%d %b %Y") if not pd.isna(deadline) else "Not set",
                    ]],
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Planned: %{customdata[2]}<br>"
                        "Progress: %{customdata[3]}<br>"
                        "Owner: %{customdata[0]}<br>"
                        "Status: %{customdata[1]}<br>"
                        "Deadline: %{customdata[4]}<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

        if not pd.isna(deadline):
            figure.add_trace(
                go.Scatter(
                    x=[deadline],
                    y=[action],
                    mode="markers",
                    marker={"symbol": "line-ns", "size": 15},
                    hovertemplate="Deadline: %{x|%d %b %Y}<extra></extra>",
                    showlegend=False,
                )
            )

        timeline_rows.append((action, start, end, progress, deadline))

    if not timeline_rows and missing_dates:
        return None, 0, missing_dates

    figure.add_shape(
        type="line",
        x0=today,
        x1=today,
        y0=-0.6,
        y1=max(len(timeline_rows) - 0.4, 0.6),
        line={"dash": "dash", "width": 2},
    )
    figure.add_annotation(
        x=today,
        y=1.03,
        xref="x",
        yref="paper",
        text="Today",
        showarrow=False,
    )

    figure.update_yaxes(
        categoryorder="array",
        categoryarray=[item[0] for item in reversed(timeline_rows)],
        autorange="reversed",
        title=None,
    )
    figure.update_xaxes(
        title=None,
        showgrid=True,
        tickformat="%b\n%Y",
    )
    figure.update_layout(
        height=max(300, len(timeline_rows) * 58 + 110),
        margin={"l": 15, "r": 20, "t": 35, "b": 20},
        hovermode="closest",
        showlegend=False,
        dragmode=False,
    )
    return figure, len(timeline_rows), missing_dates


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

    workplan_tab, execution_tab = st.tabs(["1 · Workplan", "2 · Execution pulse"])

    with workplan_tab:
        if not planner_data:
            render_stage_status(
                label="Planner",
                value="No actions loaded yet. Update from Tab 5 to begin.",
                tone="info",
            )
        else:
            # Unlike the old form-based editor, this table is intentionally
            # outside st.form so every edit reruns the app and refreshes the
            # Gantt immediately. The draft remains session-only until Save.
            draft_seed = st.session_state.get("_planner_draft_rows")
            if not isinstance(draft_seed, list):
                draft_seed = planner_data

            df_in = _prepare_planner_draft(draft_seed)
            owner_options = build_owner_options(st.session_state)

            render_save_hint(
                "Edits are a live session draft, so the Gantt updates immediately. "
                "Nothing is persisted until you click Save planner."
            )

            edited = st.data_editor(
                df_in,
                column_config={
                    "resolution_id": st.column_config.TextColumn("ID", width="small", disabled=True),
                    "#": st.column_config.NumberColumn("#", width="small", disabled=True),
                    "Resolution Action": st.column_config.TextColumn("Resolution Action", width="medium", disabled=True),
                    "Associated Uncertainties": st.column_config.TextColumn("Addresses", width="large", disabled=True),
                    "Ratings": st.column_config.TextColumn("Ratings", width="small", disabled=True),
                    "Description": st.column_config.TextColumn("Description of Work", width="large"),
                    "Duration (months)": st.column_config.SelectboxColumn(
                        "Months",
                        options=_MONTH_OPTIONS,
                        width="small",
                        help="Select the planned duration from 0 to 12 months. 0 months is treated as a milestone.",
                    ),
                    "Resources": st.column_config.TextColumn("Resources"),
                    "Constraints": st.column_config.TextColumn("Constraints"),
                    "Start Date": st.column_config.TextColumn(
                        "Start Date",
                        help="DD/MM/YYYY",
                        width="small",
                    ),
                    "Required Completion": st.column_config.TextColumn(
                        "Completion",
                        help="DD/MM/YYYY",
                        width="small",
                    ),
                    "Progress (%)": st.column_config.NumberColumn(
                        "Progress",
                        min_value=0,
                        max_value=100,
                        step=1,
                        format="%d%%",
                        width="medium",
                        help="Set execution progress from 0% to 100%. The live Gantt updates after each edit.",
                    ),
                    "Progress (0-1)": None,
                    "Status": st.column_config.SelectboxColumn(
                        "Status",
                        options=_STATUS_OPTIONS,
                    ),
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

            draft_rows = edited.to_dict("records")
            st.session_state["_planner_draft_rows"] = draft_rows

            action_cols = st.columns([1, 1, 1.6, 3.4])
            with action_cols[0]:
                add_all = st.button(
                    "Add all",
                    key="planner_add_all",
                    use_container_width=True,
                )
            with action_cols[1]:
                remove_all = st.button(
                    "Remove all",
                    key="planner_remove_all",
                    use_container_width=True,
                )
            with action_cols[2]:
                save_clicked = st.button(
                    "Save planner",
                    key="save_resolution_planner",
                    type="primary",
                    use_container_width=True,
                )
            with action_cols[3]:
                st.caption(
                    "Live draft — the Gantt below responds to Start Date, Months, "
                    "Progress, Status and Workplan changes. Save persists the current draft."
                )

            if add_all or remove_all:
                updated_draft = [dict(row) for row in draft_rows]
                target = add_all
                for row in updated_draft:
                    row["Part of Workplan"] = target
                st.session_state["_planner_draft_rows"] = updated_draft
                st.rerun()

            if save_clicked:
                data = _normalize_planner_draft(draft_rows)
                data = _normalize_owner_rows(data)

                # Planner execution metadata does not alter the generated risk
                # structure, so do not clear Risk Register/PRA for owner,
                # progress, description, status or workplan-flag edits.
                st.session_state["resolution_planner"] = data

                if not st.session_state.get("project_name", "").strip():
                    st.warning("Enter a Project Name on Overview before saving the planner.")
                    return

                ok = save_session(auto=False)
                if not ok:
                    st.error("Planner could not be saved.")
                    return

                st.session_state.pop("_planner_draft_rows", None)
                st.success("✅ Resolution planner saved.")
                st.rerun()

            gantt_title = '<div class="surm-section-header">Live Workplan Gantt</div>'
            st.markdown(gantt_title, unsafe_allow_html=True)
            gantt_figure, gantt_count, missing_dates = _build_live_gantt(draft_rows)

            if gantt_figure is None:
                if missing_dates:
                    st.warning(
                        "Add a valid Start Date (DD/MM/YYYY) to at least one workplan action "
                        "to render its timeline."
                    )
                else:
                    st.info("Mark an action as **In Workplan?** to populate the live Gantt.")
            else:
                st.caption(
                    "Live preview of the current unsaved draft. "
                    "Completed portions are calculated directly from Progress (%)."
                )
                st.plotly_chart(
                    gantt_figure,
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
                if missing_dates:
                    st.caption(
                        f"{len(missing_dates)} workplan action(s) are missing a valid Start Date "
                        "and are excluded from the timeline until a date is entered."
                    )

    with execution_tab:
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


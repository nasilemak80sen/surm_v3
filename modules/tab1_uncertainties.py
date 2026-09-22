"""Tab 1 — Select and define the uncertainties relevant to this study."""

from __future__ import annotations

from uuid import uuid4

import streamlit as st

from utils.form_ui import render_form_header, render_stage_status
from utils.workflow import mark_stage_changed


_DISC_ICONS = {
    "Geology": "🪨",
    "Geophysics": "📡",
    "Geomechanics": "⚙️",
    "PP": "🧪",
    "RE": "💧",
    "PT": "🔩",
    "PT/PP": "🔩",
    "PT/RE": "💧",
}


def render():
    mapping = st.session_state["_mapping"]
    disciplines = mapping["disciplines"]
    all_risks = mapping["risks"]

    before_selection = tuple(
        (str(item.get("uncertainty_id") or item.get("id") or ""), bool(item.get("selected")))
        for item in st.session_state["uncertainties"]
    )

    selected_items = [
        item
        for item in st.session_state["uncertainties"]
        if item.get("selected")
    ]
    selected_count = len(selected_items)

    flagged_risks = sorted({
        risk
        for item in selected_items
        for risk in item.get("risks", [])
    })

    render_form_header(
        "STEP 1 OF 7",
        "Uncertainties",
        "Select the subsurface uncertainties that are relevant to this field and project. "
        "These choices become the source population for impact assessment, resolution "
        "planning, and the downstream risk register.",
        next_step="Key Decisions",
    )

    if selected_count:
        render_stage_status(
            label="Selection status",
            value=(
                f"{selected_count} uncertainties selected and "
                f"{len(flagged_risks)} risks currently linked."
            ),
            tone="success",
        )
    else:
        render_stage_status(
            label="Selection status",
            value="Select at least one uncertainty to unlock the next stage.",
            tone="warning",
        )

    st.markdown(
        '<div class="surm-section-header">📌 Selection Summary</div>',
        unsafe_allow_html=True,
    )

    summary_columns = st.columns(3)
    summary_columns[0].metric("Selected", selected_count)
    summary_columns[1].metric("Risks Flagged", len(flagged_risks))
    summary_columns[2].metric(
        "Custom Added",
        sum(
            1
            for item in st.session_state["uncertainties"]
            if item.get("custom")
        ),
    )

    if selected_items:
        selected_html = "".join(
            (
                f'<li><strong>{item["name"]}</strong>'
                f'<span>{item["discipline"]}</span></li>'
            )
            for item in selected_items
        )
        st.markdown(
            '<div class="uncertainty-selection-list">'
            '<div class="uncertainty-selection-title">Currently selected uncertainties</div>'
            f"<ul>{selected_html}</ul></div>",
            unsafe_allow_html=True,
        )
    else:
        st.info(
            "Nothing is selected yet. Start with the discipline sections below; "
            "the summary updates as you make selections."
        )

    # ------------------------------------------------------------------
    # Global controls
    # ------------------------------------------------------------------
    st.markdown(
        '<div class="surm-section-header">🎛️ Global Controls</div>',
        unsafe_allow_html=True,
    )

    button_cols = st.columns([1, 1, 1, 5])
    with button_cols[0]:
        if st.button(
            "✅ Select All",
            key="g_sel_all",
            help="Select every predefined uncertainty.",
        ):
            for uncertainty in st.session_state["uncertainties"]:
                uncertainty["selected"] = True
            mark_stage_changed(st.session_state, "uncertainties")
            st.rerun()

    with button_cols[1]:
        if st.button(
            "☐ Deselect All",
            key="g_desel_all",
            help="Clear every current uncertainty selection.",
        ):
            for uncertainty in st.session_state["uncertainties"]:
                uncertainty["selected"] = False
            mark_stage_changed(st.session_state, "uncertainties")
            st.rerun()

    with button_cols[2]:
        st.caption(
            f"{selected_count} / {len(st.session_state['uncertainties'])} selected"
        )

    st.divider()

    # ------------------------------------------------------------------
    # Per-discipline selection
    # ------------------------------------------------------------------
    for discipline in disciplines:
        items = [
            uncertainty
            for uncertainty in st.session_state["uncertainties"]
            if uncertainty["discipline"] == discipline
        ]
        if not items:
            continue

        icon = _DISC_ICONS.get(discipline, "🔬")
        ticked = sum(
            1
            for uncertainty in items
            if uncertainty.get("selected")
        )
        total = len(items)

        header_col, select_col, deselect_col = st.columns([7, 1, 1])

        with header_col:
            st.markdown(
                f"""
                <div class="surm-section-header" style="margin-bottom:4px;">
                    {icon} {discipline}
                    <span style="margin-left:auto;background:rgba(255,255,255,0.25);
                    padding:1px 8px;border-radius:10px;font-size:11px;font-weight:400;">
                        {ticked}/{total}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with select_col:
            if st.button(
                "✅ All",
                key=f"sel_{discipline}",
                help=f"Select all {discipline} uncertainties.",
            ):
                for uncertainty in items:
                    uncertainty["selected"] = True
                mark_stage_changed(st.session_state, "uncertainties")
                st.rerun()

        with deselect_col:
            if st.button(
                "☐ None",
                key=f"desel_{discipline}",
                help=f"Deselect all {discipline} uncertainties.",
            ):
                for uncertainty in items:
                    uncertainty["selected"] = False
                mark_stage_changed(st.session_state, "uncertainties")
                st.rerun()

        for uncertainty in items:
            checkbox_col, name_col, risks_col = st.columns([0.4, 4, 5])

            with checkbox_col:
                uncertainty["selected"] = st.checkbox(
                    uncertainty["name"],
                    value=uncertainty.get("selected", False),
                    key=f"unc_{uncertainty['id']}",
                    label_visibility="collapsed",
                )

            with name_col:
                weight = (
                    "font-weight:700;color:#1F6B3A;"
                    if uncertainty.get("selected")
                    else "color:#333;"
                )
                st.markdown(
                    f'<div style="{weight}font-size:13px;padding:2px 0;">'
                    f'{uncertainty["name"]}'
                    "</div>",
                    unsafe_allow_html=True,
                )

            with risks_col:
                if uncertainty.get("selected"):
                    badges = "".join(
                        (
                            '<span style="display:inline-block;background:#E8F5E9;'
                            'color:#1B5E20;padding:1px 7px;border-radius:10px;'
                            'font-size:10px;margin:1px 2px;border:1px solid #C8E6C9;">'
                            f"{risk}</span>"
                        )
                        for risk in uncertainty.get("risks", [])[:3]
                    )
                    more = (
                        f'<span style="font-size:10px;color:#888;">'
                        f'+{len(uncertainty.get("risks", [])) - 3} more</span>'
                        if len(uncertainty.get("risks", [])) > 3
                        else ""
                    )
                    st.markdown(
                        badges + more,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<span style="font-size:11px;color:#CCC;font-style:italic;">'
                        "—</span>",
                        unsafe_allow_html=True,
                    )

    after_selection = tuple(
        (str(item.get("uncertainty_id") or item.get("id") or ""), bool(item.get("selected")))
        for item in st.session_state["uncertainties"]
    )
    if before_selection != after_selection:
        mark_stage_changed(st.session_state, "uncertainties")

    # ------------------------------------------------------------------
    # Custom uncertainty
    # ------------------------------------------------------------------
    st.divider()
    st.markdown(
        '<div class="surm-section-header">➕ Add Custom Uncertainty</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Custom uncertainties are supported end-to-end, but they must have at least "
        "one associated risk so the risk register can trace them later."
    )

    with st.form("custom_unc_form", clear_on_submit=True):
        discipline_col, name_col, risk_col = st.columns([2, 4, 2])

        with discipline_col:
            custom_discipline = st.selectbox(
                "Discipline",
                disciplines,
                key="custom_uncertainty_discipline",
            )

        with name_col:
            custom_name = st.text_input(
                "Description",
                placeholder=(
                    "Be specific — e.g. 'Fault seal integrity in eastern block'"
                ),
                key="custom_uncertainty_description",
            )

        with risk_col:
            custom_risks = st.multiselect(
                "Associated Risks",
                all_risks,
                key="custom_uncertainty_risks",
                help="At least one risk is required for downstream tracing.",
            )

        add_custom = st.form_submit_button(
            "➕ Add Uncertainty",
            type="primary",
        )

    if add_custom:
        if not custom_name.strip():
            st.warning("Give the custom uncertainty a clear description.")
        elif not custom_risks:
            st.warning(
                "Select at least one associated risk so this custom uncertainty "
                "can flow into the Risk Register."
            )
        else:
            new_numeric_id = max(
                (
                    int(item.get("id", 0))
                    for item in st.session_state["uncertainties"]
                    if str(item.get("id", "")).isdigit()
                ),
                default=0,
            ) + 1

            st.session_state["uncertainties"].append({
                "id": new_numeric_id,
                "uncertainty_id": f"UNC-CUSTOM-{uuid4().hex[:8].upper()}",
                "discipline": custom_discipline,
                "name": custom_name.strip(),
                "selected": True,
                "custom": True,
                "risks": custom_risks,
            })

            mark_stage_changed(st.session_state, "uncertainties")
            st.success(
                f"✅ Added: **{custom_name.strip()}**"
            )
            st.rerun()

    if selected_count >= 1:
        st.success(
            f"✅ {selected_count} uncertainty"
            f"{'ies' if selected_count != 1 else 'y'} selected. "
            "Proceed to **Tab 2 → Key Decisions**."
        )

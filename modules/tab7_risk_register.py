"""Tab 7 — Risk Register: assessment workspace with live risk and Bowtie view."""

from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from utils.form_ui import render_form_header, render_save_hint, render_stage_status
from components.bowtie_editor import render as render_bowtie_editor
from utils.bowtie_adapter import (
    ensure_bowtie_register,
    refresh_bowtie_document,
)
from utils.intelligence import sync_barrier_register
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

_OTHER_OPTION = "Others"
_CONTINGENCY_OPTIONS = [
    "",
    "Reassess subsurface uncertainty and update the model",
    "Run additional simulation / sensitivity cases",
    "Acquire additional data / surveillance",
    "Revise development or injection strategy",
    "Activate monitoring and surveillance trigger",
    "Escalate to technical review / decision gate",
    _OTHER_OPTION,
]
_CONSEQUENCE_OPTIONS = [
    "",
    "Production / recovery shortfall",
    "Injection performance / VRR deviation",
    "Reservoir pressure / performance deviation",
    "Well / facility integrity exposure",
    "Schedule / decision delay",
    "CAPEX / OPEX impact",
    "Reserves / value uncertainty",
    _OTHER_OPTION,
]


def _risk_owner_options(session: dict | None = None) -> list[str]:
    """Return Team + Resolution Planner owners, preserving existing custom values."""
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
        name = str(row.get("Action Owner", "") or "").strip()
        if name and name not in names:
            names.append(name)
    for row in source.get("risk_register", []) or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("Action Owner", "") or "").strip()
        if name and name not in names:
            names.append(name)
    return [""] + names


def _editor_choice(value: object, options: list[str]) -> str:
    current = str(value or "").strip()
    return current if current in options else (_OTHER_OPTION if current else "")


def _custom_value(value: object, options: list[str]) -> str:
    current = str(value or "").strip()
    return "" if current in options or current == _OTHER_OPTION else current


def _normalize_risk_rows(rows: list[dict], owner_options: list[str]) -> list[dict]:
    """Resolve controlled inputs and preserve planner-vs-manual owner lineage."""
    normalized: list[dict] = []
    previous_rows = st.session_state.get("risk_register", []) or []
    previous_by_id = {
        str(row.get("risk_id", "") or "").strip(): row
        for row in previous_rows
        if isinstance(row, dict) and str(row.get("risk_id", "") or "").strip()
    }

    for row in rows:
        next_row = dict(row)
        owner = str(next_row.get("Action Owner", "") or "").strip()
        risk_id = str(next_row.get("risk_id", "") or "").strip()
        previous = previous_by_id.get(risk_id, {})
        previous_owner = str(previous.get("Action Owner", "") or "").strip()
        previous_source = str(
            previous.get("Action Owner Source", "") or ""
        ).strip()
        incoming_source = str(
            next_row.get("Action Owner Source", "") or ""
        ).strip()

        next_row["Action Owner"] = owner
        if previous:
            # Existing rows become manual only when the user actually changes
            # the inherited value.
            if owner != previous_owner:
                next_row["Action Owner Source"] = "manual"
            else:
                next_row["Action Owner Source"] = (
                    previous_source or incoming_source or "manual"
                )
        else:
            # A newly populated risk may arrive already tagged as the planner
            # default. Preserve that lineage so future planner refreshes can
            # continue updating it until the user overrides the owner.
            next_row["Action Owner Source"] = incoming_source or "manual"

        contingency = str(next_row.get("Contingency Plan", "") or "").strip()
        if contingency == _OTHER_OPTION:
            contingency = str(next_row.get("Custom Contingency", "") or "").strip()
        next_row["Contingency Plan"] = contingency

        consequence = str(next_row.get("Impact/Consequence", "") or "").strip()
        if consequence == _OTHER_OPTION:
            consequence = str(next_row.get("Custom Consequence", "") or "").strip()
        next_row["Impact/Consequence"] = consequence

        next_row.pop("Custom Contingency", None)
        next_row.pop("Custom Consequence", None)
        normalized.append(next_row)
    return normalized



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
            label="Risk assessment",
            value=f"{not_assessed} risk(s) still need likelihood and impact.",
            tone="warning",
        )
    else:
        missing_governance = sum(
            1
            for row in risk_data
            if not str(row.get("Action Owner", "") or "").strip()
            or not str(row.get("Contingency Plan", "") or "").strip()
            or not str(row.get("Impact/Consequence", "") or "").strip()
        )
        if missing_governance:
            render_stage_status(
                label="PRA readiness",
                value=(
                    f"Assessment complete. {missing_governance} risk(s) still need "
                    "Owner, Consequence and/or Contingency details."
                ),
                tone="warning",
            )
        else:
            render_stage_status(
                label="PRA readiness",
                value="✓ Risk assessment and governance details are complete. Ready for PRA Output.",
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
        st.session_state["bowtie_register"] = ensure_bowtie_register(
            updated,
            current=st.session_state.get("bowtie_register", {}),
            uncertainties=st.session_state.get("uncertainties", []),
            resolution_list=st.session_state.get("resolution_list", {}),
            resolution_planner=st.session_state.get("resolution_planner", []),
        )
        sync_barrier_register(st.session_state)
        if previous != updated:
            mark_stage_changed(st.session_state, "risk_register")
        st.info("Risk register draft populated. Review it, then click **Save risk register** to persist.")
        st.rerun()

    risk_data = st.session_state.get("risk_register", [])

    if not risk_data:
        return

    risk_tab, pulse_tab, bowtie_tab = st.tabs(["1 · Risk assessment", "2 · Risk pulse", "3 · Bowtie analysis"])

    with risk_tab:
        risk_df = pd.DataFrame(risk_data)
        owner_options = _risk_owner_options(st.session_state)

        # "Others" is a controlled escape hatch: select it, then enter the
        # study-specific wording in the adjacent Custom column.
        for index, row in risk_df.iterrows():
            risk_df.at[index, "Action Owner"] = _editor_choice(
                row.get("Action Owner", ""), owner_options
            )
            risk_df.at[index, "Contingency Plan"] = _editor_choice(
                row.get("Contingency Plan", ""), _CONTINGENCY_OPTIONS
            )
            risk_df.at[index, "Custom Contingency"] = _custom_value(
                row.get("Contingency Plan", ""), _CONTINGENCY_OPTIONS
            )
            risk_df.at[index, "Impact/Consequence"] = _editor_choice(
                row.get("Impact/Consequence", ""), _CONSEQUENCE_OPTIONS
            )
            risk_df.at[index, "Custom Consequence"] = _custom_value(
                row.get("Impact/Consequence", ""), _CONSEQUENCE_OPTIONS
            )

        st.caption(
            "Owner is sourced from Team + Resolution Planner. For Contingency and "
            "Consequence, choose a study-relevant template or **Others**. "
            "**Others** is the muted/custom path: enter the specific wording in "
            "the adjacent Custom column before saving."
        )

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
                        "Action Owner": st.column_config.SelectboxColumn(
                            "Owner",
                            options=owner_options,
                            width="medium",
                            help="Pre-filled from the linked Resolution Planner owner. You can change the owner here to override it.",
                        ),
                        "Action Owner Source": None,
                        "Contingency Plan": st.column_config.SelectboxColumn(
                            "Contingency",
                            options=_CONTINGENCY_OPTIONS,
                            width="large",
                            help="Choose a common subsurface contingency or Others for study-specific wording.",
                        ),
                        "Custom Contingency": st.column_config.TextColumn(
                            "Custom Contingency",
                            width="large",
                            help="Required when Contingency is Others.",
                        ),
                        "Impact/Consequence": st.column_config.SelectboxColumn(
                            "Consequence",
                            options=_CONSEQUENCE_OPTIONS,
                            width="large",
                            help="Choose a common study consequence or Others for study-specific wording.",
                        ),
                        "Custom Consequence": st.column_config.TextColumn(
                            "Custom Consequence",
                            width="large",
                            help="Required when Consequence is Others.",
                        ),
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
            saved_rows = _normalize_risk_rows(
                edited.to_dict("records"),
                owner_options,
            )
            st.session_state["risk_register"] = saved_rows
            st.session_state["bowtie_register"] = ensure_bowtie_register(
                saved_rows,
                current=st.session_state.get("bowtie_register", {}),
                uncertainties=st.session_state.get("uncertainties", []),
                resolution_list=st.session_state.get("resolution_list", {}),
                resolution_planner=st.session_state.get("resolution_planner", []),
            )
            sync_barrier_register(st.session_state)
            mark_stage_changed(st.session_state, "risk_register")
            risk_ready = all(
                is_risk_assessed(row)
                and str(row.get("Action Owner", "") or "").strip()
                and str(row.get("Contingency Plan", "") or "").strip()
                and str(row.get("Impact/Consequence", "") or "").strip()
                for row in saved_rows
            )
            st.session_state["pra_output"] = (
                build_pra_output(pd.DataFrame(saved_rows)).to_dict("records")
                if risk_ready
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

    with pulse_tab:
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

    with bowtie_tab:
        # Bowtie authoring: one persistent document per risk_id.
        # ------------------------------------------------------------------
        st.markdown(
            '<div class="surm-section-header">Bowtie Analysis</div>',
            unsafe_allow_html=True,
        )
        risk_options = [
            f'{row.get("risk_id", "")} — {row.get("Risk", "Risk")}'
            for row in risk_data
        ]
        selected_label = st.selectbox(
            "Risk",
            risk_options,
            key="bowtie_risk_selection",
        )
        selected_index = risk_options.index(selected_label)
        selected_record = risk_data[selected_index]
        selected_risk_id = str(selected_record.get("risk_id", "")).strip()

        registry = st.session_state.get("bowtie_register", {})

        # The Risk Register is the Bowtie source-of-truth. Reconcile any
        # upstream form changes before rendering the editor, while preserving
        # manual Bowtie objects, relationships and positions.
        synced_registry = ensure_bowtie_register(
            [selected_record],
            current=registry,
            uncertainties=st.session_state.get("uncertainties", []),
            resolution_list=st.session_state.get("resolution_list", {}),
            resolution_planner=st.session_state.get("resolution_planner", []),
        )
        if synced_registry != registry:
            registry = {
                **registry,
                selected_risk_id: synced_registry.get(selected_risk_id),
            }
            st.session_state["bowtie_register"] = registry

        document = registry.get(selected_risk_id)
        if document is None:
            document = refresh_bowtie_document(
                selected_record,
                uncertainties=st.session_state.get("uncertainties", []),
                resolution_list=st.session_state.get("resolution_list", {}),
                resolution_planner=st.session_state.get("resolution_planner", []),
            )
            registry[selected_risk_id] = document
            st.session_state["bowtie_register"] = registry

        action_cols = st.columns([1.4, 1.4, 1.4, 2.8])
        with action_cols[0]:
            refresh_clicked = st.button(
                "Sync from Risk Register",
                key="refresh_selected_bowtie",
                use_container_width=True,
            )
        with action_cols[1]:
            save_bowtie = st.button(
                "Save Bowtie",
                type="primary",
                key="save_selected_bowtie",
                use_container_width=True,
            )
        with action_cols[2]:
            json_download_placeholder = st.empty()
        with action_cols[3]:
            st.caption(
                "Bowtie edits are session drafts. Saving the study persists the diagram "
                "with this risk without changing SURM risk scoring."
            )

        if refresh_clicked:
            registry[selected_risk_id] = refresh_bowtie_document(
                selected_record,
                uncertainties=st.session_state.get("uncertainties", []),
                resolution_list=st.session_state.get("resolution_list", {}),
                resolution_planner=st.session_state.get("resolution_planner", []),
                current=registry.get(selected_risk_id),
            )
            st.session_state["bowtie_register"] = registry
            st.rerun()

        changed_document = render_bowtie_editor(
            registry[selected_risk_id],
            key=f"surm_bowtie_{selected_risk_id}_{st.session_state.get('study_id', 'new')}",
            height=760,
        )
        if isinstance(changed_document, dict) and isinstance(changed_document.get("document"), dict):
            incoming = changed_document["document"]
            if int(incoming.get("editor_revision", 0)) >= int(
                registry[selected_risk_id].get("editor_revision", 0)
            ):
                registry[selected_risk_id] = incoming
                st.session_state["bowtie_register"] = registry

        with json_download_placeholder:
            st.download_button(
                "Download JSON",
                data=json.dumps(
                    registry[selected_risk_id],
                    indent=2,
                    ensure_ascii=False,
                ),
                file_name=f"SURM_{selected_risk_id}_Bowtie.json",
                mime="application/json",
                use_container_width=True,
                key="download_selected_bowtie_json",
            )

        if save_bowtie:
            if not st.session_state.get("project_name", "").strip():
                st.warning("Enter a Project Name on Overview before saving the Bowtie.")
            else:
                ok = save_session(auto=False)
                if ok:
                    st.success(f"Bowtie for {selected_risk_id} saved with the study.")
                else:
                    st.error("Bowtie could not be saved.")

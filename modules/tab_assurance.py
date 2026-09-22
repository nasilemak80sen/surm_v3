"""SURM assurance, review and lifecycle controls."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from utils.analytics import validation_warnings
from utils.form_ui import render_save_hint
from utils.intelligence import build_bowtie_qa
from utils.assurance import LIFECYCLE_ORDER, validate_transition, signoff_complete
from utils.persistence import save_session
from utils.workflow import completion_percent, stage_results


def render():
    session = st.session_state
    stages = stage_results(dict(session))
    warnings = validation_warnings(dict(session))
    qa = build_bowtie_qa(dict(session))

    st.markdown("## ✅ Assurance & Review")
    st.caption(
        "Lifecycle, review decisions, governance readiness and reproducible revision controls."
    )

    metrics = st.columns(5)
    metrics[0].metric("Core completion", f"{completion_percent(dict(session))}%")
    metrics[1].metric("Workflow gates", f"{sum(s.complete for s in stages)}/{len(stages)}")
    metrics[2].metric("QA findings", len(qa))
    metrics[3].metric("Validation warnings", len(warnings))
    metrics[4].metric("Revision", session.get("study_revision", 0))

    left, right = st.columns([1, 1.2], gap="large")
    with left:
        st.markdown("### Lifecycle")
        st.selectbox(
            "Study role",
            ["Author", "Reviewer", "Approver", "Viewer"],
            key="study_role",
        )
        current = session.get("study_lifecycle", "Draft")
        desired = st.selectbox(
            "Target lifecycle",
            LIFECYCLE_ORDER,
            index=LIFECYCLE_ORDER.index(current) if current in LIFECYCLE_ORDER else 0,
            key="assurance_target_lifecycle",
        )
        comment = st.text_area("Review / decision comment", key="assurance_comment")
        render_save_hint(
            "Lifecycle changes are drafts until the review action is recorded and the study is saved."
        )

        if st.button("Record lifecycle decision", type="primary", key="record_lifecycle"):
            allowed, reasons = validate_transition(dict(session), desired)

            if allowed:
                session["study_lifecycle"] = desired
                session["study_reviews"] = list(session.get("study_reviews", [])) + [{
                    "at": datetime.now().isoformat(timespec="seconds"),
                    "actor": session.get("study_owner", "local-user"),
                    "role": session.get("study_role", "Author"),
                    "from": current,
                    "to": desired,
                    "comment": comment.strip(),
                    "revision": session.get("study_revision", 0),
                }]
                if save_session(auto=False):
                    st.success(f"Lifecycle moved to {desired}.")
                else:
                    st.error("Lifecycle decision could not be saved.")
                st.rerun()
            else:
                for reason in reasons:
                    st.error(reason)
                if not reasons:
                    st.error("Lifecycle transition is not valid.")

    with right:
        st.markdown("### Gate status")
        stage_frame = pd.DataFrame([
            {
                "Stage": stage.label,
                "State": stage.state,
                "Guidance": stage.guidance,
            }
            for stage in stages
        ])
        st.dataframe(stage_frame, hide_index=True, use_container_width=True)

        st.markdown("### Validation")
        if warnings:
            st.dataframe(pd.DataFrame(warnings), hide_index=True, use_container_width=True)
        else:
            st.success("No current validation warnings.")

        st.markdown("### Bowtie QA")
        if qa:
            st.dataframe(pd.DataFrame(qa), hide_index=True, use_container_width=True)
        else:
            st.success("No Bowtie QA findings.")

    st.markdown("### Review history")
    history = session.get("study_reviews", []) or []
    if history:
        st.dataframe(pd.DataFrame(history), hide_index=True, use_container_width=True)
    else:
        st.info("No lifecycle decisions recorded yet.")

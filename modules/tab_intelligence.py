"""SURM Intelligence Command Center.

Read-only decision support derived from the canonical study state. It does not
change the underlying scoring methodology.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.analytics import build_study_analytics
from utils.db import get_db
from utils.form_ui import render_stage_status
from utils.intelligence import (
    build_historical_patterns,
    build_portfolio_intelligence,
    build_risk_intelligence,
    build_traceability,
    sync_barrier_register,
)


def render():
    session = dict(st.session_state)
    intelligence = build_risk_intelligence(session)
    st.markdown("## 📊 Study Intelligence")
    st.caption(
        "Management view of recorded risks, actions, barriers and traceability. "
        "No risk score is recalculated here."
    )

    metric_cols = st.columns(6)
    metric_cols[0].metric("Risks", intelligence["risk_count"])
    metric_cols[1].metric("Assessed", f'{intelligence["assessment_pct"]}%')
    metric_cols[2].metric("Actions", intelligence["action_count"])
    metric_cols[3].metric("Overdue", intelligence["overdue_actions"])
    metric_cols[4].metric("Barriers", intelligence["barrier_count"])
    metric_cols[5].metric("QA warnings", intelligence["bowtie_qa_warnings"])

    stage = build_study_analytics(session)
    st.caption(
        f'Core study completion: {stage["completion"]}% · '
        f'{len(intelligence["traceability_rows"])} traceability links recorded.'
    )

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("### Risk portfolio")
        risk_df = pd.DataFrame(
            {
                "Rating": list(intelligence["ratings"].keys()),
                "Risks": list(intelligence["ratings"].values()),
            }
        )
        st.bar_chart(risk_df.set_index("Rating"), height=300)

    with right:
        st.markdown("### Action pulse")
        action_df = pd.DataFrame(
            {
                "Status": list(intelligence["action_status"].keys()),
                "Actions": list(intelligence["action_status"].values()),
            }
        )
        if action_df.empty:
            st.info("No resolution planner actions recorded yet.")
        else:
            st.bar_chart(action_df.set_index("Status"), height=300)

    st.markdown("### Barrier health")
    barrier_health = intelligence["barrier_health"]
    if barrier_health:
        cols = st.columns(len(barrier_health))
        for col, (label, count) in zip(cols, barrier_health.items()):
            col.metric(label, count)
    else:
        st.info("No managed Bowtie barriers recorded yet.")

    st.markdown("### Bowtie assurance")
    qa = intelligence["bowtie_qa"]
    if qa:
        st.dataframe(
            pd.DataFrame(qa)[["risk_id", "risk", "severity", "message"]],
            hide_index=True,
            use_container_width=True,
        )
    else:
        render_stage_status(
            label="Bowtie QA",
            value="No Bowtie completeness findings recorded.",
            tone="success",
        )

    st.markdown("### Risk traceability")
    trace = build_traceability({**session, "barrier_register": sync_barrier_register(dict(session))})
    if trace:
        st.dataframe(pd.DataFrame(trace), hide_index=True, use_container_width=True, height=420)
    else:
        st.info("Traceability will appear after risks and resolutions are populated.")

    st.markdown("### Saved-study portfolio")
    records = get_db().list_all()
    portfolio = build_portfolio_intelligence(records)
    pcols = st.columns(5)
    pcols[0].metric("Saved studies", portfolio["study_count"])
    pcols[1].metric("Avg. completion", f'{portfolio["completion_avg"]}%')
    pcols[2].metric("Highest", f'{portfolio["completion_max"]}%')
    pcols[3].metric("Lowest", f'{portfolio["completion_min"]}%')
    pcols[4].metric("Lifecycle states", len(portfolio["lifecycle"]))
    if records:
        st.dataframe(pd.DataFrame(records), hide_index=True, use_container_width=True)

    st.markdown("### Historical patterns")
    historical = build_historical_patterns([record.get("session", {}) for record in get_db().list_all_records()])
    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown("**Recurring uncertainties**")
        st.dataframe(pd.DataFrame(historical["recurring_uncertainties"], columns=["Uncertainty", "Studies"]), hide_index=True, use_container_width=True)
    with h2:
        st.markdown("**Recurring resolutions**")
        st.dataframe(pd.DataFrame(historical["recurring_resolutions"], columns=["Resolution", "Uses"]), hide_index=True, use_container_width=True)
    with h3:
        st.markdown("**Recurring risks**")
        st.dataframe(pd.DataFrame(historical["recurring_risks"], columns=["Risk", "Studies"]), hide_index=True, use_container_width=True)

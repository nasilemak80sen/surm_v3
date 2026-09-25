"""modules/tab_how_to_use.py — visual onboarding and workflow guide."""

import streamlit as st

from utils.form_ui import render_form_header


def render():
    render_form_header(
        "START HERE",
        "How to Use SURM",
        "A visual walkthrough of the study journey. Use this page to understand the flow before entering assessment data.",
        next_step="Overview",
    )

    st.markdown(
        """
        <div class="surm-guide-hero">
            <div>
                <div class="surm-guide-kicker">THE SURM METHOD</div>
                <div class="surm-guide-title">From uncertainty → decision → action → risk</div>
                <div class="surm-guide-subtitle">Each stage narrows the problem and produces something the next stage can use.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="surm-flow-label">Study flow</div>', unsafe_allow_html=True)
    flow = [
        ("1", "Select", "Uncertainties"),
        ("2", "Frame", "Key Decisions"),
        ("3", "Assess", "Impact"),
        ("4", "Prioritise", "Key Uncertainties"),
        ("5", "Resolve", "Resolution List"),
        ("6", "Plan", "Workplan"),
        ("7", "Manage", "Risk Register"),
        ("→", "Output", "PRA"),
    ]
    nodes = []
    for index, (num, verb, label) in enumerate(flow):
        arrow = '<div class="surm-flow-arrow">→</div>' if index < len(flow) - 1 else ''
        nodes.append(
            f"""
            <div class="surm-flow-node">
                <div class="surm-flow-num">{num}</div>
                <div class="surm-flow-verb">{verb}</div>
                <div class="surm-flow-label">{label}</div>
            </div>{arrow}
            """
        )
    st.markdown(f'<div class="surm-flow-figure">{"".join(nodes)}</div>', unsafe_allow_html=True)

    st.markdown('<div class="surm-guide-grid">', unsafe_allow_html=True)
    guide_cards = [
        ("Before you start", "Set the study context on Overview, confirm contributors on Team, then work left-to-right through the numbered stages."),
        ("What the app calculates", "Ranking, weighted impact, combined ratings, resolution coverage and risk ratings are system-derived. Keep those outputs intact."),
        ("What the team decides", "Selection, decision weights, resolution actions, ownership, timing and risk assessment remain human inputs."),
        ("When something changes", "Changing an upstream stage intentionally refreshes downstream derived information so the study does not silently carry stale outputs."),
    ]
    for title, body in guide_cards:
        st.markdown(
            f'<div class="surm-guide-card"><div class="surm-guide-card-title">{title}</div><div class="surm-guide-card-body">{body}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown('<div class="surm-guide-section-title">Page-by-page</div>', unsafe_allow_html=True)
        rows = [
            ("Overview", "Report front page, study identity, progress and export."),
            ("Team", "Contributors, roles and sign-off governance."),
            ("1 — Uncertainties", "Select the subsurface uncertainties relevant to the study."),
            ("2 — Key Decisions", "Define the decisions the uncertainty assessment must support."),
            ("3 — Impact Assessment", "Rate uncertainty and decision impact; scores are calculated."),
            ("4 — Key Uncertainties", "Review ranking and choose what carries into the plan."),
            ("5 — Resolution List", "Map each selected uncertainty to viable resolution actions."),
            ("6 — Resolution Planner", "Assign ownership, timing, resources and progress."),
            ("7 — Risk Register", "Assess likelihood/impact, ownership, consequence and contingency."),
            ("PRA Output", "Read-only final output generated from the completed risk register."),
        ]
        for title, body in rows:
            st.markdown(f'<div class="surm-guide-row"><strong>{title}</strong><span>{body}</span></div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="surm-guide-section-title">A good working rhythm</div>', unsafe_allow_html=True)
        rhythm = [
            ("1", "Think first", "Capture the uncertainties and the decisions they could affect."),
            ("2", "Assess once", "Use the agreed rating scale consistently; do not bypass the calculated ranking."),
            ("3", "Carry only what matters", "Keep the plan focused on uncertainties the team is willing to resolve."),
            ("4", "Make ownership explicit", "An action without an owner is not yet a workplan action; a risk without governance detail is not complete."),
        ]
        for num, title, body in rhythm:
            st.markdown(
                f'<div class="surm-guide-rhythm"><span class="surm-guide-rhythm-num">{num}</span><div><strong>{title}</strong><div>{body}</div></div></div>',
                unsafe_allow_html=True,
            )

    st.caption("Tip: use the navigation bar at the top to jump directly to a page. The workflow itself remains dependency-aware, so a page can be visible while still being locked until its prerequisites are complete.")

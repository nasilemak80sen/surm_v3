"""modules/tab_how_to_use.py — User guide"""
import streamlit as st

def render():
    st.markdown('<div class="surm-section-header">📖 How to Use the SURM Toolkit</div>', unsafe_allow_html=True)

    steps = [
        ("1️⃣", "Front Page",          "Fill in project name, field, phase and sign-off details."),
        ("2️⃣", "Documentation",        "Add all team members who contributed to this SURM study."),
        ("3️⃣", "Tab 1 – Uncertainties","Tick all uncertainties relevant to your field. Associated risks auto-flag."),
        ("4️⃣", "Tab 2 – Key Decisions","List the key project decisions. Assign weight factors (1–3)."),
        ("5️⃣", "Tab 3 – Impact Assessment","Rate each uncertainty's degree (H/M/L) and its impact on each decision. Scores auto-calculate."),
        ("6️⃣", "Tab 4 – Key Uncertainties","Review ranked uncertainties. Select which to carry forward. View the Uncertainty Matrix and Tornado Chart."),
        ("7️⃣", "Tab 5 – Resolution List","For each key uncertainty, select which resolution actions will address it."),
        ("8️⃣", "Tab 6 – Resolution Planner","Click Update Planner. Fill in description, duration, owners, dates and progress for each action."),
        ("9️⃣", "Tab 7 – Risk Register","Click Populate Risk Register. Fill in contingency, consequence and L/I ratings. Generate Bowtie diagrams."),
        ("🔟", "PRA Output",            "Review the final PRA-formatted table. Download the full SURM workbook as Excel."),
    ]

    for icon, title, desc in steps:
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;margin:10px 0;padding:10px;'
            f'background:#FAFAFA;border:1px solid #E0E0E0;border-radius:4px;border-left:4px solid #1F6B3A;">'
            f'<div style="font-size:22px;margin-right:14px;line-height:1.2;">{icon}</div>'
            f'<div><div style="font-weight:700;font-size:13px;color:#1F6B3A;">{title}</div>'
            f'<div style="font-size:12px;color:#555;margin-top:2px;">{desc}</div></div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.divider()
    st.markdown('<div class="surm-section-header">💡 Key Principles</div>', unsafe_allow_html=True)
    principles = [
        ("Be Specific", "When defining uncertainties and risks, avoid generic statements. Name the exact parameter and its specific uncertainty range."),
        ("Decision-Driven", "Always ask: does this activity impact a key decision? If not, deprioritise it."),
        ("Living Document", "SURM should be updated as new data comes in or when moving to the next project phase."),
        ("Cascade Flow", "Each tab feeds the next. Changes in Tab 1–2 will need you to refresh downstream tabs."),
    ]
    for title, desc in principles:
        st.markdown(
            f'<div style="margin:8px 0;padding:8px 12px;background:#E8F5E9;border-radius:3px;">'
            f'<span style="font-weight:700;color:#1F6B3A;">🌿 {title}:</span> '
            f'<span style="font-size:12px;color:#333;">{desc}</span></div>',
            unsafe_allow_html=True
        )

    st.divider()
    st.markdown('<div class="surm-section-header">⚠️ Important Notes</div>', unsafe_allow_html=True)
    st.markdown("""
- **Session is not saved** — always export to Excel before closing the browser.
- When you update Tab 1 or Tab 2, click the **Update / Populate** buttons in Tabs 6 and 7 to refresh downstream data.
- PNG downloads require `kaleido` to be installed (`pip install kaleido`).
- Custom uncertainties added in Tab 1 will persist for the current session only.
    """)

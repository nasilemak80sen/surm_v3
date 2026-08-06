"""
modules/tab3_impact_assessment.py
H/M/L scoring — wrapped in st.form() to prevent mid-edit reruns.
Bulk H/M/L buttons are form submit buttons — no data loss on click.
"""
import streamlit as st
import pandas as pd
from utils.logic import compute_weighted_score, score_to_bin, compute_combined_rating
from utils.persistence import save_session

DEG_OPTIONS    = ["H", "M", "L"]
RATING_OPTIONS = ["H", "M", "L", "NA"]

def render():
    selected  = [u for u in st.session_state["uncertainties"] if u["selected"]]
    decisions = st.session_state.get("key_decisions", [])

    if not selected:
        st.info("⬅️ Go to **Tab 1** and select at least one uncertainty first.")
        return
    if not decisions:
        st.info("⬅️ Go to **Tab 2** and define at least one key decision first.")
        return

    st.markdown('<div class="surm-instruction">ℹ️ Rate each uncertainty\'s <b>Degree</b> (H/M/L) and its impact on each decision. Use the quick-fill buttons to bulk-set a column, then fine-tune rows individually. Click <b>Save Assessment</b> when done — weighted scores update instantly.</div>', unsafe_allow_html=True)

    decision_names = [d["Key Decision"] for d in decisions]

    # Build df_in from current session state
    existing = {row["Uncertainty"]: row for row in st.session_state.get("impact_assessment", [])}
    rows = []
    for u in selected:
        ex  = existing.get(u["name"], {})
        row = {"Uncertainty": u["name"],
               "Degree of Uncertainty": ex.get("Degree of Uncertainty", "L")}
        for dn in decision_names:
            row[dn] = ex.get(dn, "NA")
        rows.append(row)
    df_in = pd.DataFrame(rows)

    st.markdown('<div class="surm-section-header">📊 Impact Assessment Matrix</div>', unsafe_allow_html=True)

    # ── Form: bulk buttons + data editor ─────────────────────────────
    with st.form("impact_form"):
        st.markdown(
            '<div style="font-size:11px;color:#888;margin-bottom:8px;">'
            '⚠️ Click <b>Save Assessment</b> before switching tabs — edits are only captured on save.'
            '</div>', unsafe_allow_html=True)

        # Bulk-fill buttons (all form_submit_buttons so they batch with edits)
        bc = st.columns([1, 1, 1, 1, 0.5, 2])
        with bc[0]: btn_h   = st.form_submit_button("Degree → All H", help="Set all Degree of Uncertainty to H")
        with bc[1]: btn_m   = st.form_submit_button("Degree → All M")
        with bc[2]: btn_l   = st.form_submit_button("Degree → All L")
        with bc[3]: btn_na  = st.form_submit_button("Impacts → All NA", help="Reset all decision impacts to NA")
        with bc[5]: btn_save= st.form_submit_button("✅ Save Assessment", type="primary")

        col_cfg = {
            "Uncertainty":           st.column_config.TextColumn("Uncertainty", width="large", disabled=True),
            "Degree of Uncertainty": st.column_config.SelectboxColumn("Degree", options=DEG_OPTIONS, width="small"),
        }
        for dn in decision_names:
            col_cfg[dn] = st.column_config.SelectboxColumn(dn, options=RATING_OPTIONS, width="small")

        edited = st.data_editor(
            df_in, column_config=col_cfg,
            hide_index=True, width="stretch",
            num_rows="fixed", key="impact_editor",
        )

    # ── Handle form submission ────────────────────────────────────────
    any_submit = btn_h or btn_m or btn_l or btn_na or btn_save
    if any_submit:
        data = edited.to_dict("records")
        if btn_h:
            for row in data: row["Degree of Uncertainty"] = "H"
        elif btn_m:
            for row in data: row["Degree of Uncertainty"] = "M"
        elif btn_l:
            for row in data: row["Degree of Uncertainty"] = "L"
        elif btn_na:
            for row in data:
                for dn in decision_names:
                    row[dn] = "NA"

        # Compute scores and save
        scored = []
        for row in data:
            deg   = row.get("Degree of Uncertainty", "L")
            score = compute_weighted_score(row, decisions)
            imp   = score_to_bin(score)
            rated = compute_combined_rating(deg, imp)
            scored.append({**row, "Impact (Weighted)": round(score,3),
                           "Impact Bin": imp, "Combined Rating": rated})

        st.session_state["impact_assessment"] = scored
        st.session_state["key_uncertainties"] = []
        st.session_state["resolution_list"] = {}
        st.session_state["resolution_planner"] = []
        st.session_state["risk_register"] = []
        st.session_state["pra_output"] = []
        save_session(auto=True)
        st.rerun()

    # ── Live score preview (read-only, from last saved state) ─────────
    saved_ia = st.session_state.get("impact_assessment", [])
    if saved_ia:
        st.markdown('<div class="surm-section-header">🏆 Current Rankings (from last save)</div>', unsafe_allow_html=True)
        preview_rows = []
        for row in saved_ia:
            preview_rows.append({
                "Uncertainty":       row["Uncertainty"],
                "Degree":            row.get("Degree of Uncertainty","—"),
                "Score":             row.get("Impact (Weighted)", "—"),
                "Impact":            row.get("Impact Bin","—"),
                "Rating":            row.get("Combined Rating","—"),
            })
        preview_df = pd.DataFrame(preview_rows).sort_values("Score", ascending=False)

        def _style_rating(val):
            colors = {"HH":"background:#C00000;color:white","HM":"background:#FF4500;color:white",
                      "HL":"background:#FFA500","MH":"background:#FF8C00;color:white",
                      "MM":"background:#FFD700","ML":"background:#A5D6A7",
                      "LH":"background:#FFC107","LM":"background:#C8E6C9","LL":"background:#00B050;color:white"}
            return colors.get(val,"")

        st.dataframe(
            preview_df.style.map(_style_rating, subset=["Rating"]),
            width="stretch", hide_index=True,
        )
        st.success(f"✅ {len(saved_ia)} rows saved — proceed to **Tab 4 → Key Uncertainties**.")
    else:
        st.info("Fill in the table above and click **Save Assessment** to see rankings.")

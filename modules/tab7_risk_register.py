"""
modules/tab7_risk_register.py
Risk register + bowtie. Auto-saves after populate and after register edits.
"""
import streamlit as st
import pandas as pd
from utils.logic import build_risk_register
from utils.charts import build_bowtie
from utils.export_png import fig_to_png_bytes
from utils.persistence import save_session

_RATING_OPTIONS = ["H", "M", "L"]
_STATUS_OPTIONS = ["Open", "In Progress", "Closed", "On Hold"]

_RISK_MATRIX = {
    ("H","H"):"Extreme",("H","M"):"High",  ("H","L"):"Medium",
    ("M","H"):"High",   ("M","M"):"Medium",("M","L"):"Low",
    ("L","H"):"Medium", ("L","M"):"Low",   ("L","L"):"Low",
}


def render():
    ku_list  = [r for r in st.session_state.get("key_uncertainties",[]) if r.get("Include in Plan")]
    res_list = st.session_state.get("resolution_list", {})

    if not ku_list:
        st.info("⬅️ Complete **Tab 4** first.")
        return

    st.info("Build the register from the prioritised uncertainties, then complete owner, contingency, consequence, likelihood, and impact.")

    # ── Populate button ───────────────────────────────────────────────
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("🔄 Populate Risk Register", type="primary", key="populate_risk_register"):
            ku_df   = pd.DataFrame(ku_list)
            options = st.session_state["_mapping"]["resolution_options"]
            res_rows = []
            for _, r in ku_df.iterrows():
                row = {"Uncertainty": r["Uncertainty"], "Rating": r.get("Combined Rating","")}
                row.update(res_list.get(r["Uncertainty"], {}))
                res_rows.append(row)
            res_df = pd.DataFrame(res_rows)
            rr_df  = build_risk_register(ku_df, res_df)
            st.session_state["risk_register"] = rr_df.to_dict("records")
            save_session(auto=True)
            st.success(f"✅ {len(rr_df)} risks identified.")
            st.rerun()

    rr_data = st.session_state.get("risk_register", [])
    if not rr_data:
        st.info("Click the button above to populate the risk register.")
        return

    # ── Risk summary cards ────────────────────────────────────────────
    rr_df_cur = pd.DataFrame(rr_data)
    rr_df_cur["Risk Rating"] = rr_df_cur.apply(
        lambda r: _RISK_MATRIX.get(
            (r.get("Likelihood (H/M/L)","M"), r.get("Impact (H/M/L)","M")), "Medium"), axis=1)

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("🔴 Extreme", int((rr_df_cur["Risk Rating"]=="Extreme").sum()))
    m2.metric("🟠 High",    int((rr_df_cur["Risk Rating"]=="High").sum()))
    m3.metric("🟡 Medium",  int((rr_df_cur["Risk Rating"]=="Medium").sum()))
    m4.metric("🟢 Low",     int((rr_df_cur["Risk Rating"]=="Low").sum()))

    # ── Risk register form ────────────────────────────────────────────
    st.markdown('<div class="surm-section-header">📋 Risk Register</div>', unsafe_allow_html=True)

    with st.form("rr_form"):
        st.markdown(
            '<div style="font-size:11px;color:#888;margin-bottom:8px;">'
            '⚠️ Click <b>Save Register</b> before switching tabs.'
            '</div>', unsafe_allow_html=True)

        _, btn_save_col = st.columns([5, 1])
        with btn_save_col:
            btn_save = st.form_submit_button("💾 Save Register", type="primary")

        edited = st.data_editor(
            rr_df_cur,
            column_config={
                "#":                   st.column_config.NumberColumn("#", width="small", disabled=True),
                "Risk":                st.column_config.TextColumn("Risk", width="medium", disabled=True),
                "Uncertainty/Causes":  st.column_config.TextColumn("Causes / Uncertainties", width="large", disabled=True),
                "Resolution Plan":     st.column_config.TextColumn("Resolution Plan", width="large", disabled=True),
                "Action Owner":        st.column_config.TextColumn("Action Owner"),
                "Contingency Plan":    st.column_config.TextColumn("Contingency Plan", width="large"),
                "Impact/Consequence":  st.column_config.TextColumn("Impact / Consequence", width="large"),
                "Likelihood (H/M/L)":  st.column_config.SelectboxColumn("Likelihood", options=_RATING_OPTIONS, width="small"),
                "Impact (H/M/L)":      st.column_config.SelectboxColumn("Impact",     options=_RATING_OPTIONS, width="small"),
                "Risk Rating":         st.column_config.TextColumn("Risk Rating", width="small", disabled=True),
                "Risk Status":         st.column_config.SelectboxColumn("Status", options=_STATUS_OPTIONS, width="small"),
                "Remarks":             st.column_config.TextColumn("Remarks", width="large"),
            },
            hide_index=True, width="stretch", num_rows="fixed",
            key=f"rr_editor_{st.session_state.get('study_id', 'new')}",
        )

    if btn_save:
        edited["Risk Rating"] = edited.apply(
            lambda r: _RISK_MATRIX.get(
                (r.get("Likelihood (H/M/L)","M"), r.get("Impact (H/M/L)","M")), "Medium"), axis=1)
        st.session_state["risk_register"] = edited.to_dict("records")
        st.session_state["pra_output"]    = edited.to_dict("records")
        # Manual save from UI
        try:
            ok = save_session(auto=False)
            if ok:
                st.success("✅ Register saved.")
            else:
                st.error("Save failed.")
        except Exception:
            st.error("Save failed.")
        st.rerun()

    # ── Bowtie generator ──────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="surm-section-header">🦋 Bowtie Diagram Generator</div>', unsafe_allow_html=True)
    st.info("Select a risk to generate its Bowtie. Complete the consequence and contingency fields above for a useful diagram.")

    risk_names = rr_df_cur["Risk"].tolist()
    col_sel, col_gen = st.columns([3, 1])
    with col_sel:
        selected_risk = st.selectbox("Select risk:", risk_names, label_visibility="collapsed", key="bowtie_risk_selection")
    with col_gen:
        gen_btn = st.button("🦋 Generate Bowtie", type="primary", key="generate_bowtie")

    if gen_btn:
        risk_row = rr_df_cur[rr_df_cur["Risk"] == selected_risk].iloc[0].to_dict()
        fig_bt   = build_bowtie(risk_row)
        st.plotly_chart(fig_bt, use_container_width=True)
        try:
            png_bt = fig_to_png_bytes(fig_bt, width=1600, height=700)
            safe   = selected_risk.replace("/","_").replace(" ","_")[:40]
            st.download_button(
                f"📥 Download Bowtie — {selected_risk[:30]} (PNG)",
                data=png_bt,
                file_name=f"SURM_Bowtie_{safe}.png",
                mime="image/png",
            )
        except Exception:
            st.caption("Install kaleido for PNG export.")

    # ── Status overview ───────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="surm-section-header">📊 Status Overview</div>', unsafe_allow_html=True)
    if "Risk Status" in rr_df_cur.columns:
        status_counts = rr_df_cur["Risk Status"].value_counts()
        badge_map = {"Open":"badge-open","In Progress":"badge-progress",
                     "Closed":"badge-closed","On Hold":"badge-hold"}
        cols = st.columns(max(len(status_counts), 1))
        for col, (status, count) in zip(cols, status_counts.items()):
            badge = badge_map.get(status,"")
            col.markdown(f"""
                <div style="text-align:center;padding:12px;background:#FAFAFA;
                border:1px solid #E8E8E8;border-radius:6px;">
                    <div style="font-size:22px;font-weight:700;">{count}</div>
                    <span class="badge {badge}">{status}</span>
                </div>
            """, unsafe_allow_html=True)

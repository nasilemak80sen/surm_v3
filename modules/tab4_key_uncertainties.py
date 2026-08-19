"""
modules/tab4_key_uncertainties.py
Matrix + tornado. Wrapped in form to prevent mid-edit reruns.
Include All / Exclude All as form submit buttons.
"""
import streamlit as st
import pandas as pd
from utils.logic import compute_key_uncertainties
from utils.charts import build_uncertainty_matrix, build_tornado_chart
from utils.export_png import fig_to_png_bytes
from utils.persistence import save_session

_RATING_HTML = {
    "HH":"#C00000","HM":"#FF4500","HL":"#FFA500",
    "MH":"#FF8C00","MM":"#FFD700","ML":"#A5D6A7",
    "LH":"#FFC107","LM":"#C8E6C9","LL":"#00B050",
}

def _badge(rating):
    bg  = _RATING_HTML.get(rating,"#EEE")
    txt = "white" if rating in ("HH","HM","MH","LL") else "#3E2000"
    return (f'<span style="background:{bg};color:{txt};padding:2px 10px;'
            f'border-radius:10px;font-size:11px;font-weight:700;">{rating}</span>')

def render():
    ia       = st.session_state.get("impact_assessment", [])
    decisions= st.session_state.get("key_decisions", [])

    if not ia:
        st.info("⬅️ Complete **Tab 3 – Impact Assessment** first.")
        return

    st.markdown('<div class="surm-instruction">ℹ️ Uncertainties are auto-ranked by weighted impact. Use <b>Include All</b> / <b>Exclude All</b> or tick individually, then click <b>Apply & Refresh Charts</b>.</div>', unsafe_allow_html=True)

    ia_df = pd.DataFrame(ia)
    ku_df = compute_key_uncertainties(ia_df, decisions)

    if ku_df.empty:
        st.warning("Could not compute rankings — check Tab 3 inputs.")
        return

    # Re-apply saved user choices
    existing = {r["Uncertainty"]: r for r in st.session_state.get("key_uncertainties", [])}
    ku_df["Include in Plan"]     = ku_df["Uncertainty"].map(lambda x: existing.get(x,{}).get("Include in Plan",  True))
    ku_df["Resolution Achieved"] = ku_df["Uncertainty"].map(lambda x: existing.get(x,{}).get("Resolution Achieved", False))

    st.markdown('<div class="surm-section-header">📋 Ranked Uncertainties</div>', unsafe_allow_html=True)

    # ── Form ─────────────────────────────────────────────────────────
    with st.form("ku_form"):
        st.markdown(
            '<div style="font-size:11px;color:#888;margin-bottom:8px;">'
            '⚠️ Click <b>Apply & Refresh Charts</b> before switching tabs.'
            '</div>', unsafe_allow_html=True)

        bc = st.columns([1, 1, 0.5, 3])
        with bc[0]: btn_incl_all = st.form_submit_button("✅ Include All")
        with bc[1]: btn_excl_all = st.form_submit_button("☐ Exclude All")
        with bc[3]: btn_apply    = st.form_submit_button("🔄 Apply & Refresh Charts", type="primary")

        edited = st.data_editor(
            ku_df[["Uncertainty","Degree of Uncertainty","Impact (Weighted)","Impact Bin",
                   "Combined Rating","Rank","Include in Plan","Resolution Achieved"]],
            column_config={
                "Uncertainty":           st.column_config.TextColumn("Uncertainty", width="large",  disabled=True),
                "Degree of Uncertainty": st.column_config.TextColumn("Deg",         width="small",  disabled=True),
                "Impact (Weighted)":     st.column_config.NumberColumn("Score",     format="%.3f",  disabled=True, width="small"),
                "Impact Bin":            st.column_config.TextColumn("Impact",      width="small",  disabled=True),
                "Combined Rating":       st.column_config.TextColumn("Rating",      width="small",  disabled=True),
                "Rank":                  st.column_config.NumberColumn("Rank",      width="small",  disabled=True),
                "Include in Plan":       st.column_config.CheckboxColumn("Include ✓"),
                "Resolution Achieved":   st.column_config.CheckboxColumn("Resolved ✓"),
            },
            hide_index=True, width="stretch", num_rows="fixed",
            key=f"ku_editor_{st.session_state.get('study_id', 'new')}",
        )

    # ── Handle submission ─────────────────────────────────────────────
    any_submit = btn_incl_all or btn_excl_all or btn_apply
    if any_submit:
        full_ku = ku_df.copy()
        full_ku["Include in Plan"]     = edited["Include in Plan"].values
        full_ku["Resolution Achieved"] = edited["Resolution Achieved"].values
        if btn_incl_all:
            full_ku["Include in Plan"] = True
        elif btn_excl_all:
            full_ku["Include in Plan"] = False
        st.session_state["key_uncertainties"] = full_ku.to_dict("records")
        st.session_state["resolution_list"] = {}
        st.session_state["resolution_planner"] = []
        st.session_state["risk_register"] = []
        st.session_state["pra_output"] = []
        save_session(auto=True)
        st.rerun()

    # ── Charts (from saved state, no form dependency) ─────────────────
    saved_ku_list = st.session_state.get("key_uncertainties", [])
    if not saved_ku_list:
        st.info("Click **Apply & Refresh Charts** above to generate the matrix and tornado chart.")
        return

    saved_ku = pd.DataFrame(saved_ku_list)
    active   = saved_ku[saved_ku["Include in Plan"]]

    # Metrics
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Total",              len(saved_ku))
    m2.metric("Included in Plan",   int(saved_ku["Include in Plan"].sum()))
    m3.metric("High Priority",      int(saved_ku["Combined Rating"].isin(["HH","HM","MH","HL","LH"]).sum()))
    m4.metric("Resolved",           int(saved_ku["Resolution Achieved"].sum()))

    if active.empty:
        st.warning("No uncertainties included. Tick 'Include in Plan' and click Apply.")
        return

    col_m, col_t = st.columns(2)
    with col_m:
        st.markdown('<div class="surm-section-header">🟩 Uncertainty Matrix</div>', unsafe_allow_html=True)
        fig_m = build_uncertainty_matrix(active)
        st.plotly_chart(fig_m, width="stretch")
        try:
            st.download_button("📥 Matrix (PNG)", data=fig_to_png_bytes(fig_m),
                               file_name="SURM_Uncertainty_Matrix.png", mime="image/png")
        except Exception:
            st.caption("Install kaleido for PNG export.")

    with col_t:
        st.markdown('<div class="surm-section-header">🌪️ Tornado Chart</div>', unsafe_allow_html=True)
        fig_t = build_tornado_chart(active)
        st.plotly_chart(fig_t, width="stretch")
        try:
            st.download_button("📥 Tornado (PNG)", data=fig_to_png_bytes(fig_t, height=max(500,len(active)*55+120)),
                               file_name="SURM_Tornado_Chart.png", mime="image/png")
        except Exception:
            pass

    # Rating legend
    st.divider()
    legend_html = "".join([f'<span style="margin:3px;display:inline-block;">{_badge(r)}</span>'
                           for r in ["HH","HM","HL","MH","MM","ML","LH","LM","LL"]])
    st.markdown(f'<div style="padding:10px;background:#FAFAFA;border:1px solid #E8E8E8;border-radius:4px;">'
                f'<span style="font-size:12px;color:#888;margin-right:10px;">Deg × Impact →</span>'
                f'{legend_html}</div>', unsafe_allow_html=True)
    st.success(f"✅ {int(active['Include in Plan'].sum())} uncertainties included — proceed to **Tab 5 → Resolution List**.")

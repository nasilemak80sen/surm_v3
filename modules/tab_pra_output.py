"""modules/tab_pra_output.py — Final PRA-formatted output with colour coding"""
import streamlit as st
import pandas as pd
from utils.logic import build_pra_output
from utils.export_excel import build_excel_export

_RISK_BG  = {"Extreme":"#FFEBEE","High":"#FFF3E0","Medium":"#FFFDE7","Low":"#E8F5E9"}
_RISK_CLR = {"Extreme":"#C00000","High":"#E64A19","Medium":"#F57F17","Low":"#2E7D32"}

def render():
    rr_data = st.session_state.get("risk_register", [])

    if not rr_data:
        st.info("⬅️ Complete **Tab 7 – Risk Register** first.")
        return

    st.markdown('<div class="surm-instruction">ℹ️ Read-only PRA output — auto-generated from Tab 7. Edit data there. Download the full SURM workbook using the button below.</div>', unsafe_allow_html=True)

    pra_df = build_pra_output(pd.DataFrame(rr_data))

    if pra_df.empty:
        st.warning("No PRA data to display.")
        return

    # ── Summary metrics ───────────────────────────────────────────────
    st.markdown('<div class="surm-section-header">📊 Risk Portfolio Summary</div>', unsafe_allow_html=True)

    for lvl in ["Extreme", "High", "Medium", "Low"]:
        count = int((pra_df.get("Risk Rating", pd.Series()) == lvl).sum()) if "Risk Rating" in pra_df.columns else 0
        if count == 0:
            continue
        bg  = _RISK_BG.get(lvl,"#FFF")
        clr = _RISK_CLR.get(lvl,"#333")
        risks_at_level = pra_df[pra_df["Risk Rating"]==lvl]["Risk"].tolist() if "Risk Rating" in pra_df.columns else []
        labels = " · ".join(risks_at_level)

        st.markdown(f"""
            <div style="background:{bg};border-left:5px solid {clr};border-radius:0 4px 4px 0;
            padding:10px 16px;margin-bottom:8px;display:flex;align-items:center;gap:16px;">
                <div style="min-width:80px;">
                    <span style="font-size:22px;font-weight:700;color:{clr};">{count}</span>
                    <span style="font-size:12px;font-weight:700;color:{clr};margin-left:4px;">{lvl}</span>
                </div>
                <div style="font-size:11px;color:{clr};opacity:0.8;overflow:hidden;
                white-space:nowrap;text-overflow:ellipsis;">{labels}</div>
            </div>
        """, unsafe_allow_html=True)

    # ── PRA table ─────────────────────────────────────────────────────
    st.markdown('<div class="surm-section-header">📄 PRA Output Table</div>', unsafe_allow_html=True)

    # Colour-code Risk Rating column using pandas Styler
    def _style_rr(val):
        bg  = _RISK_BG.get(val,"")
        clr = _RISK_CLR.get(val,"")
        if bg:
            return f"background-color:{bg};color:{clr};font-weight:700;"
        return ""

    styled = pra_df.style.map(_style_rr, subset=["Risk Rating"]) if "Risk Rating" in pra_df.columns else pra_df.style
    st.dataframe(styled, width="stretch", hide_index=True, height=480)

    # ── Export ────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="surm-section-header">📥 Export</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 3])
    with col_a:
        xlsx  = build_excel_export()
        field = st.session_state.get("field_name","") or "Output"
        st.download_button(
            "📥 Download Full SURM Workbook (.xlsx)",
            data=xlsx,
            file_name=f"SURM_{field.replace(' ','_')}_Complete.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col_b:
        st.markdown("""
            <div style="background:#E8F5E9;border-left:4px solid #1F6B3A;padding:10px 14px;
            border-radius:0 4px 4px 0;font-size:12px;color:#2E7D32;margin-top:4px;">
                📄 Exports all 9 sheets: Front Page · Team · Uncertainties · Decisions · 
                Impact Assessment · Key Uncertainties · Resolution List · Resolution Planner · 
                Risk Register · PRA Output — all in styled SURM Excel format.
            </div>
        """, unsafe_allow_html=True)

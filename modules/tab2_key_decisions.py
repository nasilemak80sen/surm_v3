"""modules/tab2_key_decisions.py — Key project decisions & weight factors"""
import streamlit as st
import pandas as pd

def render():
    st.markdown('<div class="surm-instruction">ℹ️ <b>Instructions:</b> List the key decisions this study will drive. Assign a weight factor (1 = low importance, 3 = high importance) to each. These weights determine which uncertainties matter most in the scoring.</div>', unsafe_allow_html=True)

    st.markdown('<div class="surm-section-header">🎯 Key Project Decisions</div>', unsafe_allow_html=True)

    df = pd.DataFrame(st.session_state["key_decisions"])
    if "Weight (1-3)" not in df.columns:
        df["Weight (1-3)"] = 1
    df["Weight (1-3)"] = (
        pd.to_numeric(df["Weight (1-3)"], errors="coerce")
        .fillna(1)
        .clip(1, 3)
        .astype(int)
    )

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "Key Decision": st.column_config.TextColumn("Key Decision", width="large", help="What decision will this uncertainty impact?"),
            "Weight (1-3)": st.column_config.NumberColumn("Weight (1–3)", min_value=1, max_value=3, step=1, format="%d", help="1=Low, 2=Medium, 3=High importance"),
            "Description":  st.column_config.TextColumn("Description", width="large", help="Brief context for this decision"),
        },
        hide_index=True,
        key="kd_editor",
    )

    # Persist the editor result as-is. Cleaning or rebuilding rows during the
    # same render makes Streamlit restore the previous widget snapshot.
    normalized = edited.copy()
    normalized["Weight (1-3)"] = (
        pd.to_numeric(normalized["Weight (1-3)"], errors="coerce")
        .fillna(1)
        .clip(1, 3)
        .astype(int)
    )
    st.session_state["key_decisions"] = normalized.to_dict("records")

    if st.button("Remove Empty Decision Rows", key="remove_empty_decision_rows"):
        st.session_state["key_decisions"] = [
            row for row in st.session_state["key_decisions"]
            if str(row.get("Key Decision") or "").strip()
        ] or [{"Key Decision": "", "Weight (1-3)": 1, "Description": ""}]
        st.rerun()

    # Summary
    st.divider()
    if not normalized.empty:
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Decisions Defined", len(normalized))
        mc2.metric("Max Weight",        int(normalized["Weight (1-3)"].max()))
        mc3.metric("Total Weight Sum",  int(normalized["Weight (1-3)"].sum()))

        st.markdown('<div class="surm-section-header">⚖️ Weight Distribution</div>', unsafe_allow_html=True)
        for _, row in normalized.iterrows():
            w = int(row["Weight (1-3)"])
            bar_color = "#1F6B3A" if w == 3 else "#FFD700" if w == 2 else "#CCC"
            st.markdown(
                f'<div style="display:flex;align-items:center;margin:4px 0;">'
                f'<div style="width:220px;font-size:12px;color:#333;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">{row["Key Decision"]}</div>'
                f'<div style="width:{w*60}px;height:14px;background:{bar_color};border-radius:3px;margin-left:8px;"></div>'
                f'<div style="margin-left:8px;font-size:11px;color:#666;">{"●" * w}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.info("No decisions defined yet. Add rows using the table above.")

"""
modules/tab5_resolution_list.py
Resolution alternatives matrix.
Wrapped in st.form() — no reruns during editing.
Y for All / Clear All as form submit buttons.
"""
import streamlit as st
import pandas as pd
from utils.persistence import save_session

def render():
    ku_list = [r for r in st.session_state.get("key_uncertainties",[]) if r.get("Include in Plan")]
    if not ku_list:
        st.info("⬅️ Go to **Tab 4** and select uncertainties to include in the plan.")
        return

    st.markdown('<div class="surm-instruction">ℹ️ For each uncertainty, mark <b>Y</b> against the resolution actions that will address it. Use bulk controls to fill or clear all, then fine-tune individually. Click <b>Save Selections</b> when done.</div>', unsafe_allow_html=True)

    options = st.session_state["_mapping"]["resolution_options"]
    ku_df   = pd.DataFrame(ku_list)

    # Build df_in from current session state
    existing = st.session_state.get("resolution_list", {})
    rows = []
    for _, r in ku_df.iterrows():
        row = {"Uncertainty": r["Uncertainty"], "Rating": r["Combined Rating"]}
        ex  = existing.get(r["Uncertainty"], {})
        for opt in options:
            row[opt] = ex.get(opt, "")
        rows.append(row)
    df_in = pd.DataFrame(rows)

    st.markdown('<div class="surm-section-header">🛠️ Resolution Alternatives Matrix</div>', unsafe_allow_html=True)

    # ── Form ─────────────────────────────────────────────────────────
    with st.form("res_list_form"):
        st.markdown(
            '<div style="font-size:11px;color:#888;margin-bottom:8px;">'
            '⚠️ Click <b>Save Selections</b> before switching tabs.'
            '</div>', unsafe_allow_html=True)

        bc = st.columns([1, 1, 0.5, 3])
        with bc[0]: btn_y_all   = st.form_submit_button("✅ Y for All",   help="Mark Y for every cell")
        with bc[1]: btn_clr_all = st.form_submit_button("☐ Clear All",   help="Clear all selections")
        with bc[3]: btn_save    = st.form_submit_button("💾 Save Selections", type="primary")

        col_cfg = {
            "Uncertainty": st.column_config.TextColumn("Uncertainty", width="large", disabled=True),
            "Rating":      st.column_config.TextColumn("Rating",      width="small", disabled=True),
        }
        for opt in options:
            col_cfg[opt] = st.column_config.SelectboxColumn(
                opt, options=["", "Y"], width="small",
                help=f"Select Y if '{opt}' will address this uncertainty")

        edited = st.data_editor(
            df_in, column_config=col_cfg, hide_index=True,
            width="stretch", num_rows="fixed",
            key=f"res_list_editor_{st.session_state.get('study_id', 'new')}",
        )

    # ── Handle submission ─────────────────────────────────────────────
    any_submit = btn_y_all or btn_clr_all or btn_save
    if any_submit:
        data = edited.to_dict("records")
        if btn_y_all:
            for row in data:
                for opt in options:
                    row[opt] = "Y"
        elif btn_clr_all:
            for row in data:
                for opt in options:
                    row[opt] = ""

        res_dict = {}
        for row in data:
            name = row["Uncertainty"]
            res_dict[name] = {opt: row.get(opt,"") for opt in options}
        st.session_state["resolution_list"] = res_dict
        st.session_state["resolution_planner"] = []
        st.session_state["risk_register"] = []
        st.session_state["pra_output"] = []
        save_session(auto=True)
        st.rerun()

    # ── Coverage summary (from saved state) ───────────────────────────
    saved_rl = st.session_state.get("resolution_list", {})
    if saved_rl:
        st.divider()
        st.markdown('<div class="surm-section-header">📈 Coverage Summary</div>', unsafe_allow_html=True)
        cov_rows = []
        for opt in options:
            count = sum(1 for v in saved_rl.values() if v.get(opt) == "Y")
            if count > 0:
                cov_rows.append({"Resolution Action": opt, "Uncertainties Addressed": count})

        if cov_rows:
            cov_df = pd.DataFrame(cov_rows).sort_values("Uncertainties Addressed", ascending=False)
            for _, cr in cov_df.iterrows():
                pct = int(cr["Uncertainties Addressed"] / max(len(ku_list),1) * 100)
                st.markdown(
                    f'<div style="display:flex;align-items:center;margin:4px 0;">'
                    f'<div style="width:280px;font-size:12px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">{cr["Resolution Action"]}</div>'
                    f'<div style="width:{pct*2}px;max-width:200px;height:10px;background:#1F6B3A;border-radius:3px;margin:0 8px;"></div>'
                    f'<div style="font-size:11px;color:#555;">{int(cr["Uncertainties Addressed"])} ({pct}%)</div>'
                    f'</div>', unsafe_allow_html=True)

        # Warn on uncovered uncertainties
        uncov = [n for n,v in saved_rl.items() if all(v.get(opt,"") != "Y" for opt in options)]
        if uncov:
            st.warning(f"⚠️ {len(uncov)} uncertainties have no resolution selected: " +
                       ", ".join(uncov[:3]) + ("..." if len(uncov)>3 else ""))
        else:
            st.success("✅ All uncertainties have at least one resolution action — proceed to **Tab 6 → Resolution Planner**.")
    else:
        st.info("Fill in the table above and click **Save Selections** to see the coverage summary.")

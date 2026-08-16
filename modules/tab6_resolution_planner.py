"""
modules/tab6_resolution_planner.py
Action plan with progress dashboard.
Add All / Remove All workplan toggle as form submit buttons.
Auto-saves after planner update.
"""
import streamlit as st
import pandas as pd
from utils.logic import build_resolution_planner
from utils.persistence import save_session

def render():
    res_list = st.session_state.get("resolution_list", {})
    ku_list  = [r for r in st.session_state.get("key_uncertainties",[]) if r.get("Include in Plan")]

    if not res_list:
        st.info("⬅️ Go to **Tab 5** and select resolution actions first.")
        return

    st.markdown('<div class="surm-instruction">ℹ️ Click <b>Update Planner</b> to load actions from Tab 5. Fill in description, resources, dates, owner and progress. Use bulk workplan toggles to add/remove all at once. Click <b>Save Planner</b> when done.</div>', unsafe_allow_html=True)

    # ── Update trigger ────────────────────────────────────────────────
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("🔄 Update Planner from Tab 5", type="primary"):
            options = st.session_state["_mapping"]["resolution_options"]
            ku_df   = pd.DataFrame(ku_list) if ku_list else pd.DataFrame()
            if ku_df.empty:
                st.warning("No key uncertainties found.")
            else:
                res_rows = []
                for _, r in ku_df.iterrows():
                    row = {"Uncertainty": r["Uncertainty"], "Rating": r["Combined Rating"]}
                    row.update(res_list.get(r["Uncertainty"], {}))
                    res_rows.append(row)
                res_df  = pd.DataFrame(res_rows)
                planner = build_resolution_planner(res_df)
                st.session_state["resolution_planner"] = planner.to_dict("records")
                st.session_state["risk_register"] = []
                st.session_state["pra_output"] = []
                save_session(auto=True)
                st.success(f"✅ {len(planner)} actions loaded.")
                st.rerun()

    planner_data = st.session_state.get("resolution_planner", [])
    if not planner_data:
        st.info("Click **Update Planner** above to populate the action plan.")
        return

    st.markdown('<div class="surm-section-header">📅 Resolution Action Plan</div>', unsafe_allow_html=True)

    df_in = pd.DataFrame(planner_data)

    # ── Form: bulk workplan toggles + data editor ─────────────────────
    with st.form("planner_form"):
        st.markdown(
            '<div style="font-size:11px;color:#888;margin-bottom:8px;">'
            '⚠️ Click <b>Save Planner</b> before switching tabs.'
            '</div>', unsafe_allow_html=True)

        bc = st.columns([1, 1, 0.5, 3])
        with bc[0]: btn_add_all = st.form_submit_button("✅ Add All to Workplan")
        with bc[1]: btn_rem_all = st.form_submit_button("☐ Remove All from Workplan")
        with bc[3]: btn_save    = st.form_submit_button("💾 Save Planner", type="primary")

        edited = st.data_editor(
            df_in,
            column_config={
                "#":                       st.column_config.NumberColumn("#", width="small", disabled=True),
                "Resolution Action":       st.column_config.TextColumn("Resolution Action", width="medium", disabled=True),
                "Associated Uncertainties":st.column_config.TextColumn("Addresses", width="large", disabled=True),
                "Ratings":                 st.column_config.TextColumn("Ratings", width="small", disabled=True),
                "Description":             st.column_config.TextColumn("Description of Work", width="large"),
                "Duration (months)":       st.column_config.NumberColumn("Duration (mths)", min_value=0, max_value=60, step=1),
                "Resources":               st.column_config.TextColumn("Resources"),
                "Constraints":             st.column_config.TextColumn("Constraints"),
                "Start Date":              st.column_config.TextColumn("Start Date", help="DD/MM/YYYY", width="small"),
                "Required Completion":     st.column_config.TextColumn("Completion Date", help="DD/MM/YYYY", width="small"),
                "Progress (0-1)":          st.column_config.NumberColumn("Progress", min_value=0.0, max_value=1.0,
                                                                          step=0.05),
                "Action Owner":            st.column_config.TextColumn("Owner"),
                "Part of Workplan":        st.column_config.CheckboxColumn("In Workplan?"),
                "Remarks":                 st.column_config.TextColumn("Remarks", width="large"),
            },
            hide_index=True, width="stretch", num_rows="fixed", key="planner_editor",
        )

    # ── Handle submission ─────────────────────────────────────────────
    any_submit = btn_add_all or btn_rem_all or btn_save
    if any_submit:
        data = edited.to_dict("records")
        if btn_add_all:
            for row in data:
                row["Part of Workplan"] = True
        elif btn_rem_all:
            for row in data:
                row["Part of Workplan"] = False
            st.session_state["resolution_planner"] = data
            st.session_state["risk_register"] = []
            st.session_state["pra_output"] = []
            try:
                save_session(auto=True)
            except Exception:
                pass
            st.rerun()
        elif btn_save:
            # persist edits explicitly
            st.session_state["resolution_planner"] = data
            try:
                ok = save_session(auto=False)
                if ok:
                    st.success("✅ Planner saved.")
                else:
                    st.error("Save failed.")
            except Exception:
                st.error("Save failed.")
            st.rerun()
    st.markdown('<div class="surm-section-header">📊 Progress Dashboard</div>', unsafe_allow_html=True)

    # workplan rows: only those marked as part of workplan
    workplan_rows = [r for r in planner_data if r.get("Part of Workplan")]
    overall = sum(float(r.get("Progress (0-1)", 0) or 0) for r in workplan_rows) / max(len(workplan_rows), 1)
    ov_clr  = "#1F6B3A" if overall >= 0.8 else "#FFD700" if overall >= 0.4 else "#FF8C00"

    st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #E0E0E0;border-radius:6px;
        padding:14px 18px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-size:13px;font-weight:700;color:#1F6B3A;">Overall Workplan Progress</span>
                <span style="font-size:18px;font-weight:700;">{int(overall*100)}%</span>
            </div>
            <div style="background:#E8E8E8;border-radius:6px;height:12px;">
                <div style="width:{int(overall*100)}%;background:{ov_clr};height:12px;border-radius:6px;transition:width 0.4s;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    for row in workplan_rows:
        prog  = float(row.get("Progress (0-1)",0) or 0)
        pct   = int(prog * 100)
        label = str(row.get("Resolution Action",""))[:55]
        owner = str(row.get("Action Owner","") or "Unassigned")
        dur   = str(row.get("Duration (months)","") or "—")
        clr   = "#1F6B3A" if pct >= 80 else "#FFD700" if pct >= 40 else "#FF8C00"
        s_cls = "badge-closed" if pct >= 100 else "badge-progress" if pct > 0 else "badge-hold"
        s_lbl = "Complete" if pct >= 100 else "In Progress" if pct > 0 else "Not Started"
        st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #EEEEEE;border-radius:4px;
            padding:10px 14px;margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
                    <span style="font-size:12px;font-weight:600;">{label}</span>
                    <div style="display:flex;gap:8px;align-items:center;">
                        <span class="badge {s_cls}" style="font-size:10px;">{s_lbl}</span>
                        <span style="font-size:11px;color:#888;">{owner}</span>
                        <span style="font-size:11px;color:#888;">{dur} mths</span>
                        <span style="font-size:12px;font-weight:700;min-width:36px;text-align:right;">{pct}%</span>
                    </div>
                </div>
                <div style="background:#EFEFEF;border-radius:4px;height:8px;">
                    <div style="width:{pct}%;background:{clr};height:8px;border-radius:4px;transition:width 0.3s;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

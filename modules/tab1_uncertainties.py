"""modules/tab1_uncertainties.py — Uncertainty selection with Select All / per-discipline"""
import streamlit as st

_DISC_ICONS = {
    "Geology":"🪨","Geophysics":"📡","Geomechanics":"⚙️",
    "PP":"🧪","RE":"💧","PT":"🔩","PT/PP":"🔩","PT/RE":"💧",
}

def render():
    st.markdown('<div class="surm-instruction">ℹ️ Select every uncertainty relevant to your field. Use <b>Select All / Deselect All</b> at global or discipline level, then deselect what isn\'t applicable.</div>', unsafe_allow_html=True)

    mapping     = st.session_state["_mapping"]
    disciplines = mapping["disciplines"]
    all_risks   = mapping["risks"]

    # ── Global Select / Deselect All ─────────────────────────────────
    st.markdown('<div class="surm-section-header">🎛️ Global Controls</div>', unsafe_allow_html=True)
    g1, g2, g3, g4 = st.columns([1, 1, 1, 5])
    with g1:
        if st.button("✅ Select All", key="g_sel_all"):
            for u in st.session_state["uncertainties"]:
                u["selected"] = True
            st.rerun()
    with g2:
        if st.button("☐ Deselect All", key="g_desel_all"):
            for u in st.session_state["uncertainties"]:
                u["selected"] = False
            st.rerun()
    with g3:
        n_sel = sum(1 for u in st.session_state["uncertainties"] if u["selected"])
        n_tot = len(st.session_state["uncertainties"])
        st.markdown(f'<div style="padding:8px 0;font-size:12px;color:#888;">{n_sel} / {n_tot} selected</div>',
                    unsafe_allow_html=True)

    st.divider()

    # ── Per-discipline sections ───────────────────────────────────────
    for disc in disciplines:
        items = [u for u in st.session_state["uncertainties"] if u["discipline"] == disc]
        if not items:
            continue

        icon   = _DISC_ICONS.get(disc, "🔬")
        ticked = sum(1 for u in items if u["selected"])
        total  = len(items)

        # Discipline header row with per-discipline Select / Deselect
        hcol, scol, dcol = st.columns([7, 1, 1])
        with hcol:
            st.markdown(
                f'<div class="surm-section-header" style="margin-bottom:4px;">'
                f'{icon} {disc}'
                f'<span style="margin-left:auto;background:rgba(255,255,255,0.25);'
                f'padding:1px 8px;border-radius:10px;font-size:11px;font-weight:400;">'
                f'{ticked}/{total}</span></div>',
                unsafe_allow_html=True
            )
        with scol:
            if st.button("✅ All", key=f"sel_{disc}",
                         help=f"Select all {disc} uncertainties"):
                for u in items:
                    u["selected"] = True
                st.rerun()
        with dcol:
            if st.button("☐ None", key=f"desel_{disc}",
                         help=f"Deselect all {disc} uncertainties"):
                for u in items:
                    u["selected"] = False
                st.rerun()

        # Uncertainty rows
        for u in items:
            col_chk, col_name, col_risks = st.columns([0.4, 4, 5])
            with col_chk:
                u["selected"] = st.checkbox(
                    u["name"], value=u["selected"],
                    key=f"unc_{u['id']}", label_visibility="collapsed")
            with col_name:
                weight = "font-weight:700;color:#1F6B3A;" if u["selected"] else "color:#333;"
                st.markdown(f'<div style="{weight}font-size:13px;padding:2px 0;">{u["name"]}</div>',
                            unsafe_allow_html=True)
            with col_risks:
                if u["selected"]:
                    badges = "".join([
                        f'<span style="display:inline-block;background:#E8F5E9;color:#1B5E20;'
                        f'padding:1px 7px;border-radius:10px;font-size:10px;margin:1px 2px;'
                        f'border:1px solid #C8E6C9;">{r}</span>'
                        for r in u["risks"][:3]
                    ])
                    more = (f' <span style="font-size:10px;color:#888;">+{len(u["risks"])-3} more</span>'
                            if len(u["risks"]) > 3 else "")
                    st.markdown(badges + more, unsafe_allow_html=True)
                else:
                    st.markdown('<span style="font-size:11px;color:#CCC;font-style:italic;">—</span>',
                                unsafe_allow_html=True)

    # ── Add custom uncertainty ────────────────────────────────────────
    st.divider()
    st.markdown('<div class="surm-section-header">➕ Add Custom Uncertainty</div>', unsafe_allow_html=True)
    with st.form("custom_unc_form", clear_on_submit=True):
        fc1, fc2, fc3 = st.columns([2, 4, 2])
        with fc1: c_disc  = st.selectbox("Discipline", disciplines)
        with fc2: c_name  = st.text_input("Description", placeholder="Be specific — e.g. 'Fault seal integrity in eastern block'")
        with fc3: c_risks = st.multiselect("Associated Risks", all_risks)
        if st.form_submit_button("➕ Add Uncertainty", type="primary") and c_name.strip():
            new_id = max((u["id"] for u in st.session_state["uncertainties"]), default=0) + 1
            st.session_state["uncertainties"].append({
                "id":new_id,"discipline":c_disc,"name":c_name.strip(),
                "selected":True,"custom":True,"risks":c_risks,
            })
            st.success(f"✅ Added: **{c_name.strip()}**")
            st.rerun()

    # ── Summary ───────────────────────────────────────────────────────
    st.divider()
    n_sel   = sum(1 for u in st.session_state["uncertainties"] if u["selected"])
    flagged = set()
    for u in st.session_state["uncertainties"]:
        if u["selected"]:
            flagged.update(u["risks"])
    m1,m2,m3 = st.columns(3)
    m1.metric("Uncertainties Selected", n_sel)
    m2.metric("Risks Flagged",          len(flagged))
    m3.metric("Custom Added",           sum(1 for u in st.session_state["uncertainties"] if u.get("custom")))
    if n_sel == 0:
        st.info("☝️ Select at least one uncertainty above to begin.")
    elif n_sel >= 5:
        st.success(f"✅ {n_sel} uncertainties selected — proceed to **Tab 2 → Key Decisions**.")

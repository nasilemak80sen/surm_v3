"""
app.py — SURM Web Application
Subsurface Uncertainty & Risk Management Plan Toolkit
Run: streamlit run app.py
"""
import streamlit as st
import os

# ── Page config — must be first Streamlit call ────────────────────────
st.set_page_config(
    page_title="SURM Toolkit | PETRONAS Carigali",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Load CSS ──────────────────────────────────────────────────────────
_css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
with open(_css_path, "r", encoding="utf-8") as _f:
    st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────
from utils.session import init_session
from utils.persistence import resume_latest_session
init_session()
resume_latest_session()

# ── Import tab modules ────────────────────────────────────────────────
from modules.tab_frontpage           import render as render_frontpage
from modules.tab_documentation       import render as render_docs
from modules.tab_how_to_use          import render as render_howto
from modules.tab1_uncertainties      import render as render_tab1
from modules.tab2_key_decisions      import render as render_tab2
from modules.tab3_impact_assessment  import render as render_tab3
from modules.tab4_key_uncertainties  import render as render_tab4
from modules.tab5_resolution_list    import render as render_tab5
from modules.tab6_resolution_planner import render as render_tab6
from modules.tab7_risk_register      import render as render_tab7
from modules.tab_pra_output          import render as render_pra


# ═══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════
def _sidebar():
    ss = st.session_state

    # ── Logo & title ─────────────────────────────────────────────────
    st.sidebar.markdown("""
        <div style="text-align:center;padding:16px 0 10px 0;">
            <div style="font-size:36px;line-height:1;">🛢️</div>
            <div style="font-size:15px;font-weight:700;letter-spacing:0.5px;margin-top:6px;">SURM Toolkit</div>
            <div style="font-size:10px;opacity:0.7;margin-top:2px;letter-spacing:1px;">PETRONAS CARIGALI</div>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.divider()

    # ── Project info ──────────────────────────────────────────────────
    field  = ss.get("field_name", "") or "—"
    proj   = ss.get("project_name", "") or "—"
    phase  = ss.get("project_phase", "") or "—"

    st.sidebar.markdown(f"""
        <div style="padding:4px 0;">
            <div style="font-size:10px;opacity:0.65;text-transform:uppercase;letter-spacing:0.8px;">Field</div>
            <div style="font-size:14px;font-weight:700;margin-bottom:8px;">{field}</div>
            <div style="font-size:10px;opacity:0.65;text-transform:uppercase;letter-spacing:0.8px;">Project</div>
            <div style="font-size:13px;margin-bottom:8px;">{proj}</div>
            <div style="font-size:10px;opacity:0.65;text-transform:uppercase;letter-spacing:0.8px;">Phase</div>
            <div style="font-size:13px;">
                <span style="background:rgba(255,255,255,0.2);padding:2px 10px;
                border-radius:10px;font-weight:700;">{phase}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.divider()

    # ── Live study stats ──────────────────────────────────────────────
    n_unc_sel  = sum(1 for u in ss.get("uncertainties", []) if u.get("selected"))
    n_unc_tot  = len(ss.get("uncertainties", []))
    n_decisions= len([d for d in ss.get("key_decisions", []) if d.get("Key Decision","").strip()])
    n_ku       = len([r for r in ss.get("key_uncertainties", []) if r.get("Include in Plan")])
    n_actions  = len(ss.get("resolution_planner", []))
    n_risks    = len(ss.get("risk_register", []))
    n_team     = len([r for r in ss.get("team_members", []) if (r.get("Name") or "").strip()])

    st.sidebar.markdown('<div style="font-size:10px;opacity:0.65;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">Study Summary</div>', unsafe_allow_html=True)

    stats = [
        ("Uncertainties Selected", f"{n_unc_sel} / {n_unc_tot}"),
        ("Key Decisions",          str(n_decisions)),
        ("Key Uncertainties",      str(n_ku)),
        ("Resolution Actions",     str(n_actions)),
        ("Risks Identified",       str(n_risks)),
        ("Team Members",           str(n_team)),
    ]
    for label, val in stats:
        st.sidebar.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
            padding:5px 8px;margin-bottom:4px;background:rgba(255,255,255,0.1);
            border-radius:4px;">
                <span style="font-size:11px;opacity:0.8;">{label}</span>
                <span style="font-size:13px;font-weight:700;">{val}</span>
            </div>
        """, unsafe_allow_html=True)

    st.sidebar.divider()

    # ── Overall progress bar ──────────────────────────────────────────
    checks = [
        bool(ss.get("project_name", "")),
        n_unc_sel > 0,
        n_decisions > 0,
        bool(ss.get("impact_assessment", [])),
        n_ku > 0,
        bool(ss.get("resolution_list", {})),
        n_actions > 0,
        n_risks > 0,
    ]
    pct = int(sum(checks) / len(checks) * 100)
    bar_color = "#52C990" if pct >= 80 else "#FFD700" if pct >= 40 else "#FF9966"

    st.sidebar.markdown(f"""
        <div style="margin:6px 0 4px 0;">
            <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:5px;opacity:0.8;">
                <span>Study Completion</span>
                <span style="font-weight:700;">{pct}%</span>
            </div>
            <div style="background:rgba(255,255,255,0.2);border-radius:6px;height:8px;">
                <div style="width:{pct}%;background:{bar_color};height:8px;border-radius:6px;
                transition:width 0.5s ease;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.divider()

    # ── Save session ──────────────────────────────────────────────────
    st.sidebar.markdown('<div style="font-size:10px;opacity:0.65;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">Session</div>', unsafe_allow_html=True)

    from utils.persistence import save_session
    if st.sidebar.button("💾 Save Session", key="sidebar_save"):
        if not ss.get("project_name","").strip():
            st.sidebar.warning("Set a Project Name on the Front Page first.")
        else:
            ok = save_session(auto=False)
            if ok:
                st.sidebar.success("✅ Saved!")
            else:
                st.sidebar.error("Save failed — check permissions.")

    last_saved  = ss.get("_last_saved", "")
    last_auto   = ss.get("_last_save_auto", False)
    if last_saved:
        ts    = last_saved.replace("T", " ")
        label = f"{'Auto-saved' if last_auto else 'Saved'}: {ts[11:19]}"
        st.sidebar.markdown(f'<div style="font-size:10px;opacity:0.7;text-align:center;margin-top:4px;">✅ {label}</div>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown('<div style="font-size:10px;opacity:0.55;text-align:center;margin-top:4px;">⚠️ Not saved yet</div>', unsafe_allow_html=True)

    st.sidebar.divider()

    # ── Quick Excel export ────────────────────────────────────────────
    st.sidebar.markdown('<div style="font-size:10px;opacity:0.65;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">Quick Export</div>', unsafe_allow_html=True)

    from utils.export_excel import build_excel_export
    xlsx = build_excel_export()
    fname = f"SURM_{field.replace(' ','_')}.xlsx" if field != "—" else "SURM_Output.xlsx"
    st.sidebar.download_button(
        label="📥 Download SURM (.xlsx)",
        data=xlsx,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.sidebar.divider()
    st.sidebar.markdown("""
        <div style="font-size:10px;opacity:0.5;text-align:center;line-height:1.6;">
            v1.0 &nbsp;·&nbsp; SURM Toolkit<br>
            Sessions saved to <code>sessions/</code> folder
        </div>
    """, unsafe_allow_html=True)


_sidebar()


# ═══════════════════════════════════════════════════════════════════════
# MAIN HEADER
# ═══════════════════════════════════════════════════════════════════════
ss = st.session_state
field = ss.get("field_name","")
phase = ss.get("project_phase","")
proj  = ss.get("project_name","")

_subtitle = ""
if field: _subtitle += f" — {field}"
if proj and proj != field: _subtitle += f" ({proj})"

st.markdown(f"""
    <div class="surm-card" style="margin-bottom:12px;padding:16px 18px;background:linear-gradient(90deg,#F8FCF8 0%,#F1F8F2 100%);border:1px solid #DCE9DD;">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;">
            <div style="display:flex;align-items:center;gap:14px;">
                <div style="font-size:34px;line-height:1;">🛢️</div>
                <div>
                    <div style="font-size:17px;font-weight:700;color:#1F6B3A;line-height:1.2;">
                        Subsurface Uncertainty &amp; Risk Management Plan{_subtitle}
                    </div>
                    <div style="font-size:11px;color:#6B7A6E;margin-top:3px;letter-spacing:0.3px;">
                        PETRONAS Carigali &nbsp;|&nbsp; SURM Toolkit v1.0
                    </div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <span class="surm-pill subtle">{field or 'Field pending'}</span>
                <span class="surm-pill subtle">{proj or 'Project pending'}</span>
                <span class="surm-pill">{phase or 'Phase pending'}</span>
                <span class="surm-pill success">{'Saved' if ss.get('_last_saved') else 'Draft'}</span>
            </div>
        </div>
        <div class="surm-helper" style="margin-top:10px;margin-bottom:0;">
            <span>💡</span>
            <span>Follow the tabs in order, save often, and keep your project details consistent so your study is easy to resume later.</span>
        </div>
    </div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# TAB LAYOUT
# ═══════════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "📋 Front Page",
    "👥 Team",
    "📖 How to Use",
    "1️⃣ Uncertainties",
    "2️⃣ Key Decisions",
    "3️⃣ Impact Assessment",
    "4️⃣ Key Uncertainties",
    "5️⃣ Resolution List",
    "6️⃣ Resolution Planner",
    "7️⃣ Risk Register",
    "📄 PRA Output",
])

with tabs[0]:  render_frontpage()
with tabs[1]:  render_docs()
with tabs[2]:  render_howto()
with tabs[3]:  render_tab1()
with tabs[4]:  render_tab2()
with tabs[5]:  render_tab3()
with tabs[6]:  render_tab4()
with tabs[7]:  render_tab5()
with tabs[8]:  render_tab6()
with tabs[9]:  render_tab7()
with tabs[10]: render_pra()


# ═══════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════
st.markdown("""
    <div class="surm-footer">
        🛢️ SURM Toolkit v1.0 &nbsp;·&nbsp; PETRONAS Carigali &nbsp;·&nbsp;
        Subsurface Uncertainty &amp; Risk Management &nbsp;·&nbsp;
        <span style="opacity:0.6;">Session not saved — export to Excel before closing</span>
    </div>
""", unsafe_allow_html=True)

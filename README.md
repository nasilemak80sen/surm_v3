# 🛢️ SURM Toolkit
**Subsurface Uncertainty & Risk Management Plan**  
PETRONAS Carigali | Web Application v1.0

---

## What Is This?

The SURM Toolkit is a web-based implementation of the PETRONAS Carigali Subsurface Uncertainty & Risk Management process. It mirrors the Excel-based workflow that teams use during Field Development Planning (FDP), replacing manual spreadsheet navigation with a structured, tab-by-tab guided interface.

**Key features:**
- 11-tab workflow mirroring the Excel SURM toolkit
- Automated cascade — select uncertainties → risks auto-flag → scores auto-calculate → register auto-builds
- Uncertainty Matrix and Tornado Chart (Plotly, interactive + PNG export)
- Proper Bowtie Diagram for each risk (PNG export)
- Full styled Excel export (.xlsx, 9 sheets)
- Live project summary sidebar

---

## Option 1 — Run Locally (Recommended for PETRONAS internal use)

### Windows (easiest)
```
1. Download and unzip surm_app.zip
2. Double-click launch.bat
3. Browser opens automatically at http://localhost:8501
```

### Mac / Linux
```bash
chmod +x launch.sh
./launch.sh
```

### Manual setup
```bash
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate      # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
streamlit run surm.py
```

---

## Option 2 — Streamlit Community Cloud (Free, shareable link)

> Best for sharing across the team without IT infrastructure.

### Steps:

1. **Create a GitHub account** at https://github.com if you don't have one.

2. **Create a new repository** called `surm-toolkit` (set to Private if needed).

3. **Upload all files** from this folder into the repository root.  
   Your repo should look like:
   ```
   surm-toolkit/
   ├── surm.py
   ├── requirements.txt
   ├── .streamlit/config.toml
   ├── data/
   ├── modules/
   ├── utils/
   └── assets/
   ```

4. **Go to** https://share.streamlit.io and sign in with GitHub.

5. Click **"New app"** → select your repository → set:
   - **Branch:** `main`
   - **Main file path:** `surm.py`

6. Click **Deploy**. In ~2 minutes you'll have a shareable URL like:  
   `https://your-name-surm-toolkit.streamlit.app`

7. **Share the link** with your team. Anyone with the link can use it — no installation needed.

> 💡 Free tier gives you 1 app and sufficient compute for a small team. Upgrade to Streamlit Teams ($) for private apps with password protection.

### Keep the Community Cloud app warm

The repository includes `.github/workflows/keep-streamlit-awake.yml`. It checks the
deployed app every six hours and can also be run manually from the GitHub Actions
page. This is a best-effort workaround for Community Cloud sleep behaviour, not a
guaranteed always-on service.

Configure it once in GitHub:

1. Open **Settings → Secrets and variables → Actions → Variables**.
2. Add a repository variable named `SURM_APP_URL`, for example:
   `https://your-name-surm-toolkit.streamlit.app/`.
3. Open **Actions → Keep SURM Awake → Run workflow** to test it.

The manual run also accepts an optional URL override. The workflow reports the HTTP
status and fails when the app returns HTTP 400 or higher.

---

## Option 3 — Docker (For IT-managed or server deployment)

```bash
# Build the image
docker build -t surm-toolkit .

# Run (port 8501)
docker run -p 8501:8501 surm-toolkit

# Open
http://localhost:8501
```

**With Docker Compose** (add this as `docker-compose.yml`):
```yaml
version: "3.8"
services:
  surm:
    build: .
    ports:
      - "8501:8501"
    restart: unless-stopped
```
```bash
docker-compose up -d
```

> For intranet deployment, replace `localhost` with the server IP. Ensure port 8501 is open in the firewall.

---

## Workflow Guide

| Tab | Action |
|-----|--------|
| 📋 Front Page | Fill project name, field, phase, sign-off names |
| 👥 Team | Add all contributors |
| 1️⃣ Uncertainties | Tick relevant uncertainties — risks auto-flag |
| 2️⃣ Key Decisions | Add project decisions + weight factors (1–3) |
| 3️⃣ Impact Assessment | Rate each uncertainty H/M/L against each decision |
| 4️⃣ Key Uncertainties | Review auto-ranked list, select what to carry forward |
| 5️⃣ Resolution List | Assign resolution actions per uncertainty |
| 6️⃣ Resolution Planner | Update planner, fill dates/owners/progress |
| 7️⃣ Risk Register | Populate register, fill contingency, generate Bowtie |
| 📄 PRA Output | Review final PRA table, download full Excel |

> Sessions are saved to SQLite locally or PostgreSQL when `DATABASE_URL` is configured.

---

## File Structure

```
surm_app/
├── surm.py                       Main entry point
├── requirements.txt              Python dependencies
├── launch.bat                    Windows one-click launcher
├── launch.sh                     Mac/Linux launcher
├── Dockerfile                    Container deployment
├── .streamlit/
│   └── config.toml               Theme + server config
├── data/
│   └── surm_master_mapping.json  Master uncertainty↔risk mapping
├── modules/                      One file per tab
│   ├── tab_frontpage.py
│   ├── tab_documentation.py
│   ├── tab_how_to_use.py
│   ├── tab1_uncertainties.py
│   ├── tab2_key_decisions.py
│   ├── tab3_impact_assessment.py
│   ├── tab4_key_uncertainties.py
│   ├── tab5_resolution_list.py
│   ├── tab6_resolution_planner.py
│   ├── tab7_risk_register.py
│   └── tab_pra_output.py
├── utils/
│   ├── session.py                Session state manager
│   ├── logic.py                  Cascade scoring engine
│   ├── charts.py                 Plotly charts (Matrix, Tornado, Bowtie)
│   ├── export_excel.py           Excel export builder
│   └── export_png.py             PNG export helper
└── assets/
    └── style.css                 Excel-inspired theme
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | ≥1.35 | Web framework |
| pandas | ≥2.0 | Data handling |
| openpyxl | ≥3.1 | Excel export |
| plotly | ≥5.20 | Interactive charts |
| kaleido | ≥0.2 | PNG export from Plotly |
| numpy | ≥1.26 | Numerical operations |
| Pillow | ≥10.0 | Image handling |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| PNG export not working | `pip install kaleido` |
| `use_container_width` warnings | Update calls to use `width='stretch'` |
| App won't start on port 8501 | Another app may use that port. Run: `streamlit run surm.py --server.port 8502` |
| Blank tab content | Check that session state was initialised — reload the page |

---

## Built By

PETRONAS Carigali — Reservoir Engineering & Technology  
SURM Toolkit v1.0 | 2025

---

*For questions or improvements, contact the RE-LT team.*

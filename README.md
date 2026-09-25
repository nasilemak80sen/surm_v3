# 🛢️ SURM Toolkit

Subsurface Uncertainty & Risk Management Plan
PETRONAS Carigali | Streamlit application

SURM Toolkit is a guided web implementation of the PETRONAS Carigali subsurface uncertainty and risk-management workflow. It preserves the engineering methodology while turning the Excel process into a structured form-filling experience with validation, persistence, visual analysis, risk governance and export.

## Current workflow

| Step | User activity | SURM output |
|---|---|---|
| 1️⃣ Uncertainties | Select relevant subsurface uncertainties and define custom items when needed | Study uncertainty population + linked risks |
| 2️⃣ Key Decisions | Define the decisions the study must support and weight them 1–3 | Decision drivers |
| 3️⃣ Impact Assessment | Rate degree of uncertainty and impact on each active decision | Weighted impact + combined HH–LL rating |
| 4️⃣ Key Uncertainties | Review the calculated ranking and decide what carries forward | Prioritised planning set |
| 5️⃣ Resolution List | Select engineering actions for each included uncertainty | Resolution coverage matrix |
| 6️⃣ Resolution Planner | Assign owners, dates, resources, status and progress | Action workplan |
| 7️⃣ Risk Register | Complete owner, consequence, contingency, likelihood and impact | Assessed risk register |
| 📄 PRA Output | Review the read-only final risk view | PRA-ready output + workbook |

Supporting pages are ordered for users as: Study Repository → How to Use → Overview (report front page) → Team. The workflow then runs from Uncertainties through PRA Output.



## UI / UX direction

P2 focuses on information density without changing the engineering methodology:

- **How to Use** is a visual onboarding page with a study-flow figure instead of a text-only manual.
- **Overview** is treated as the report front page: study identity, readiness, governance and export live together without duplicating every downstream detail.
- Workflow pages use a **work-left / inspect-right** layout where practical, keeping the user's primary input alongside the immediate chart, coverage, execution or risk output.
- The sidebar is the single primary navigation surface, grouped into Study, Workflow, Insights & governance and Support. Redundant top-level page switchers and previous/next navigation have been removed.
- Workflow pages use a compact task header and reserve visual emphasis for the active form and its decision-support output.
- Sidebar content is intentionally structured around study context, workflow navigation, frequent Save/New actions and progressive disclosure for session settings, export and account controls.

## Design principles

### Preserve the methodology
The existing H/M/L scoring, weighted-decision logic, combined rating order, resolution master list and 3×3 risk matrix are preserved unless a concrete data-integrity or workflow gap requires a change.

### Treat SURM as a guided form
Each workflow page explains what the user is deciding, what is calculated automatically, what is still required and what happens next.

New assessments are not silently pre-filled with a human judgement. For example, a new risk begins as Not Assessed until likelihood and impact are explicitly entered.

### One durable study model
StudyDocument is the canonical durable representation. Database persistence, JSON snapshots and Excel export use the same study model so governance fields, methodology version and workflow state do not drift between outputs.

### Downstream data stays trustworthy
Changing an upstream stage invalidates dependent outputs through one central workflow dependency map. The app can therefore tell the user why a later stage is blocked instead of showing stale results.

## Persistence and governance

Saved studies record:

- Study ID
- Project / field / phase
- Study owner and team
- Methodology version
- Workflow revisions
- Sign-off information
- Study lifecycle
- Full workflow data

Current study schema: 2.2
Current methodology identifier: SURM-2026.01

Sessions use SQLite locally and PostgreSQL when DATABASE_URL is configured.

## Excel output

The exporter currently produces 14 worksheets:

1. Front Page
2. Documentation
3. 1. Uncertainties List
4. 2. Key Decisions
5. 3. Impact Assessment
6. 4. Key Uncertainties
7. 5. Resolution List
8. 6. Resolution Planner
9. 7. Risk Register
10. 7b. Bowtie Register
11. 8. Barrier Management
12. 9. Assurance & Reviews
13. 10. Traceability
14. PRA Output

The workbook is an output projection of the canonical study model; it is not the application's source of truth.

## Development maturity — Phase 4 onward

The current branch has moved beyond workflow-only UX into a decision-intelligence
layer:

- **Study Intelligence** consolidates risk, action, barrier, QA, traceability and saved-study portfolio signals.
- **Barrier Management** turns Bowtie barriers into managed records with owner, status, progress, due date, effectiveness, criticality and verification.
- **Bowtie QA** checks structural completeness without changing SURM risk scoring.
- **Assurance & Review** controls lifecycle transitions and records review decisions.
- **Revision History** supports immutable revision listing and durable-field comparison.
- **Historical Intelligence** provides descriptive recurring-pattern analysis across saved studies.

Corporate-data integrations are intentionally **shelved** for this development
wave. SURM remains self-contained around its canonical study model and local /
configured database backends.

See `docs/ROADMAP_PHASE4_10.md` for the active roadmap.

## Regression protection

The repository includes deterministic tests for weighted scoring and NA handling, rating thresholds, explicit risk assessment, workflow gating, resolution coverage, downstream invalidation, workflow revision tracking and StudyDocument governance/sign-off round trips.

GitHub Actions runs two hardening lanes on the main branch and enhancement branches:

- Python regression coverage for workflow, persistence, governance, export, intelligence and database concurrency.
- Playwright browser regression coverage for the custom Bowtie component.

Phase 9 production-hardening controls are documented in `docs/PRODUCTION_HARDENING.md`.

## Run locally

Windows:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run surm.py

macOS / Linux:

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    streamlit run surm.py

The default Streamlit port is 8501.

## Deployment

The project supports Streamlit Community Cloud, Docker, Docker Compose, SQLite for local use and PostgreSQL for shared/production deployments.

For secured deployments, set `SURM_AUTH_REQUIRED=1` and configure `SURM_ROLE_MAP` as documented in `docs/PRODUCTION_HARDENING.md`. Streamlit's native OIDC identity is used through `st.user`; role assignment remains an application authorization layer.

The repository also includes the existing Streamlit keep-awake GitHub workflow.

## Repository structure

    surm_v3/
    ├── surm.py
    ├── components/
    ├── modules/
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
    │   ├── tab_pra_output.py
    │   └── tab_study_repository.py
    ├── utils/
    │   ├── session.py
    │   ├── study_document.py
    │   ├── workflow.py
    │   ├── logic.py
    │   ├── persistence.py
    │   ├── study_export.py
    │   ├── export_excel.py
    │   └── form_ui.py
    ├── data/
    │   └── surm_master_mapping.json
    ├── tests/
    └── .github/workflows/

## Methodology versioning

The master mapping in data/surm_master_mapping.json contains domain methodology data such as uncertainties, associated risks, resolution options and rating configuration. When the methodology evolves, the methodology version should be changed deliberately so older studies remain reproducible.

## Built for

PETRONAS Carigali — Reservoir Engineering & Technology

SURM Toolkit is intended to support engineering decision-making, traceability and structured study documentation. It does not replace engineering review or professional judgement.
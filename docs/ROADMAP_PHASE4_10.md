# SURM Development Roadmap — Phase 4 onward

## Current baseline

Phases 0–3 and Sprint 1–7 established:
- canonical StudyDocument and durable workflow state
- explicit form transactions and downstream invalidation
- governance/sign-off and revision persistence
- the seven-stage SURM workflow
- dashboard/UX overhaul
- interactive Risk Register + Bowtie integration

## Phase 4 — Decision Intelligence

### Sprint 8 — Risk Intelligence Dashboard
Status: implemented in this wave.

Includes:
- risk assessment coverage
- risk rating and status distribution
- resolution action pulse and overdue count
- barrier health summary
- Bowtie QA findings
- study traceability table
- saved-study portfolio summary

### Sprint 9 — Cross-stage Traceability
Status: implemented in this wave.

Canonical links now expose:
Risk → Uncertainty → Resolution → Action → Bowtie Barrier.

### Sprint 10 — Barrier Management
Status: implemented in this wave.

Managed barrier records include owner, status, progress, due date,
effectiveness, health, criticality, verification and evidence count.

### Sprint 11 — Degradation / Escalation
Status: foundation prepared.

The barrier model is designed to accept degradation factors and controls
without changing SURM scoring. Detailed authoring is the next Bowtie editor
expansion.

### Sprint 12 — Bowtie QA
Status: implemented in this wave.

Checks cover missing causes, consequences, preventive/mitigative barriers,
unowned barriers, and missing effectiveness metadata.

## Phase 6 — Governance & Assurance

### Sprint 13 — Review / Approval
Status: implemented in this wave.

Lifecycle states:
Draft → In Review → Reviewed → Approved → Archived.

Transitions are controlled by workflow completion, study role, governance
sign-offs and Bowtie assurance findings.

### Sprint 14 — Revision History
Status: implemented in this wave.

The database retains immutable study revisions and the UI can compare durable
fields between revisions.

## Phase 7 — Analytics & Historical Intelligence

### Sprint 15 — Portfolio Analytics
Status: implemented in this wave.

Saved-study summaries can be aggregated by lifecycle, phase, completion and
editor.

### Sprint 16 — Historical Risk Intelligence
Status: implemented in this wave as descriptive pattern analysis.

The current implementation reports recurring uncertainties, resolutions and
risks across saved studies. It does not predict outcomes or modify engineering
scores.

A future predictive layer must be evidence-backed and must remain separate from
the authoritative SURM methodology.

## Phase 8 — Integration

Corporate data integrations are intentionally shelved for now.

This means no SharePoint/enterprise repository ingestion is part of the
current development wave.

A future API/service boundary may still be introduced when it has a concrete
product need; it is not a prerequisite for the current SURM roadmap.

## Phase 9 — Production Hardening

Status: implemented.

Includes:
- deployment-aware authenticated identity hooks with role-map enforcement
- ownership-aware study mutation and Admin-only deletion in secured deployments
- strict sequential lifecycle transitions and governance matrix coverage
- SQLite WAL/busy-timeout hardening and PostgreSQL row-locking
- optimistic revision conflict protection for stale editors
- end-to-end workflow regression coverage through 100% completion
- 14-sheet Excel export contract validation
- larger-study performance diagnostics and a 500-risk regression profile
- browser-level Playwright regression coverage for the custom Bowtie component
- separate CI jobs for Python regression and browser regression

The Study Role control remains a governance state; secured deployments bind it
to the authenticated identity and configured deployment role map.

See `docs/PRODUCTION_HARDENING.md` for deployment configuration.

## Phase 10 — Enterprise SURM

Planned:
- executive command center
- portfolio-level barrier health
- historical knowledge base
- management-ready exports
- deeper assurance and audit capabilities

The new Intelligence page is the first implementation of this direction.

## Architectural rule

SURM remains authoritative for:
- uncertainty ranking
- decision weights
- impact methodology
- risk likelihood/impact
- risk rating
- workflow gating

Bowtie remains a structured barrier visualisation and management layer. It must
never silently recalculate or replace SURM risk scoring.

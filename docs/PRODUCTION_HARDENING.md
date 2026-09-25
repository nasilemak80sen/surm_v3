# SURM Production Hardening — Phase 9

Phase 9 hardens SURM without changing the authoritative engineering methodology.

## Deployment identity and role enforcement

Local development remains available by default.

For a secured deployment, set:

```text
SURM_AUTH_REQUIRED=1
SURM_ROLE_MAP={"alice@example.com":["Author","Reviewer"],"lead@example.com":["Approver"],"admin@example.com":["Admin"]}
```

The deployment must expose an authenticated Streamlit identity. SURM uses that
identity to:

- require authentication before study mutation
- require the authenticated identity to hold the selected study role
- bind newly saved studies to the authenticated identity
- prevent non-owners from editing an owned study unless they are Admin
- restrict saved-study deletion to Admin

The existing Study Role control remains a governance state. In a secured
deployment it is no longer sufficient by itself; the authenticated identity
must also be granted the selected role.

## Database and concurrency hardening

SQLite remains suitable for local/single-node use and now uses:

- WAL journal mode
- 30-second busy timeout
- explicit transactional writes
- optimistic revision conflict detection

A stale editor cannot silently overwrite a newer study revision.

For multi-user production deployment, PostgreSQL is the intended shared
database backend through `DATABASE_URL`.

## Browser regression coverage

The Bowtie custom component has Playwright coverage for:

- Streamlit v1 component handshake
- initial render
- node dragging
- add/edit operations
- component-value emission
- undo/redo
- SVG export

CI runs Python regression tests and browser regression tests as separate jobs.
Chromium is installed only for the browser job.

## Workflow and governance hardening

Lifecycle transitions are sequential:

```text
Draft → In Review → Reviewed → Approved → Archived
```

Backward moves and skipped states are rejected.

Approval continues to require the core workflow, governance sign-offs,
Bowtie coverage and Bowtie QA clearance.

## Export verification

The hardening suite validates the complete 14-sheet Excel workbook contract,
including Bowtie, Barrier Management, Assurance & Reviews and Traceability.

## Performance diagnostics

Set:

```text
SURM_PERF_DEBUG=1
```

to display Intelligence computation time in the Intelligence page.

The regression suite also profiles a 500-risk / 500-action synthetic study to
detect accidental scaling regressions.

## Operational guidance

Before enabling secured deployment:

1. configure the authenticated identity provider for the Streamlit deployment
2. configure `SURM_AUTH_REQUIRED` and `SURM_ROLE_MAP`
3. use PostgreSQL for shared multi-user operation
4. back up the database before schema or deployment changes
5. run the full CI suite, including browser regression coverage

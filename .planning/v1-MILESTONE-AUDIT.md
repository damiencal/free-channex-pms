---
milestone: v1
audited: 2026-02-28
status: gaps_found
scores:
  requirements: 39/44
  phases: 6/8 passed
  integration: 14/18 wired
  flows: 3/5 complete
gaps:
  critical:
    - "No frontend UI for data entry or import — dashboard is read-only; all data operations (CSV upload, manual entry, expense recording, categorization, reconciliation, revenue recognition) require direct API calls"
    - "Router prefix mismatch — compliance and communication routers lack /api prefix but frontend apiFetch unconditionally prepends /api; both Actions tab buttons (Submit resort form, Mark VRBO message sent) return 404"
    - "Airbnb pre-arrival operator notification missing — scheduler fires, status flips to 'sent' silently; operator never knows to copy-paste message into Airbnb app"
  integration:
    - "LLM schema attribution values wrong — prompt.py says 'property', 'shared', 'personal' but actual data stores 'jay', 'minnie', 'shared'"
    - "Revenue recognition not automated — operator must manually call POST /api/accounting/revenue/recognize-all after every CSV import"
  requirements:
    - "COMM-01: PARTIAL — Airbnb welcome depends on external native messaging one-time setup"
    - "COMM-02: PARTIAL — Airbnb pre-arrival rendered but no delivery mechanism"
    - "COMM-04: PARTIAL — native messaging only covers welcome, not pre-arrival"
    - "COMP-06: UNCERTAIN — host info in PDF from template annotations, not config at runtime"
    - "DASH-07: BLOCKED — both action buttons 404 due to router prefix"
tech_debt:
  - phase: 01-foundation
    items:
      - "Hardcoded DB fallback URL in app/db.py and alembic/env.py (dev convenience, non-blocking)"
      - "CHANGE_ME placeholders in config/jay.yaml and config/minnie.yaml (expected for operator setup)"
  - phase: 02-data-ingestion
    items:
      - "Airbnb CSV column names unverified against real export (SYNTHETIC — may fail on real data)"
      - "Mercury CSV column names unverified against real export (LOW confidence)"
      - "VRBO CSV column names from official docs (MEDIUM confidence — not verified against real export)"
      - "listing_slug_map contains CHANGE_ME placeholder keys"
  - phase: 05-resort-pdf-compliance
    items:
      - "host_name and host_phone config fields exist but not connected to PDF fill — host info is pre-baked in PDF template annotations"
      - "CHANGE_ME placeholders in resort_contact_email, host_name, host_phone"
  - phase: 07-dashboard
    items:
      - "Reports tab is placeholder — shows API endpoint info but no interactive report UI"
      - "No data management UI — no CSV upload, no manual entry, no expense recording, no categorization, no reconciliation"
  - phase: 08-llm-natural-language-interface
    items:
      - "attribution enum values in prompt.py do not match actual stored values"
---

# v1 Milestone Audit Report

**Project:** Rental Management Suite (airbnb-tools)
**Audited:** 2026-02-28
**Status:** GAPS FOUND
**Overall Score:** 39/44 requirements satisfied

## Executive Summary

The v1 milestone has achieved strong backend coverage — all 8 phases are structurally complete with real implementations (no stubs). The backend API layer covers data ingestion, accounting, compliance, communication, reporting, and LLM queries. The frontend dashboard provides read-only visibility into financials, bookings, and pending actions.

**However, a critical gap exists: the frontend has NO data entry or import capabilities.** All data operations (CSV upload, manual booking entry, expense recording, bank transaction categorization, reconciliation, revenue recognition) require direct API calls via curl or Postman. A non-technical user (Kim) cannot operate the system independently using only the dashboard.

Additionally, three integration defects prevent existing dashboard features from working correctly.

---

## Phase Status

| Phase | Verification | Score | Status |
|-------|-------------|-------|--------|
| 1. Foundation | passed | 5/5 | Complete |
| 2. Data Ingestion | human_needed | 6/6 | Complete (needs real CSV verification) |
| 3. Accounting Engine | passed | 5/5 | Complete |
| 4. Financial Reports | passed | 4/4 | Complete |
| 5. Resort PDF Compliance | human_needed | 4/5 | Complete (host info design nuance) |
| 6. Guest Communication | gaps_found | 4/5 | Airbnb pre-arrival gap |
| 7. Dashboard | gaps_found | 4/5 | Action buttons broken |
| 8. LLM Natural Language Interface | passed | 4/4 | Complete |

---

## Critical Gaps

### 1. No Frontend Data Entry or Import UI

**Severity:** Critical — renders system unusable for non-technical users

The frontend dashboard (Phase 7) is entirely read-only. There is no UI for:
- Uploading CSV files (Airbnb, VRBO, Mercury)
- Entering RVshare bookings manually
- Triggering revenue recognition
- Recording expenses
- Managing loan payments
- Categorizing bank transactions
- Running bank reconciliation
- Viewing full financial reports (P&L, balance sheet, income statement)

The backend API endpoints for all these operations exist and are functional, but they are only accessible via direct HTTP calls. This means Kim cannot use the system without Thomas making API calls on her behalf — defeating the project's core value proposition.

**Missing frontend pages:**
- Import/Upload page (CSV file upload for each platform)
- RVshare manual entry form
- Bank transaction categorization view
- Expense management view
- Reconciliation dashboard
- Full report viewers (P&L, balance sheet, income statement)
- Accounting operations (revenue recognition trigger, loan payments)

### 2. Router Prefix Mismatch — Actions Tab Buttons 404

**Severity:** High — both action dismiss buttons are broken

The `apiFetch` wrapper in `frontend/src/api/client.ts` prepends `/api` to all paths. Two backend routers are mounted WITHOUT the `/api` prefix:

| Router | Prefix | apiFetch Result | Actual Route |
|--------|--------|----------------|--------------|
| compliance | `/compliance` | `/api/compliance/submit/{id}` (404) | `/compliance/submit/{id}` |
| communication | `/communication` | `/api/communication/confirm/{id}` (404) | `/communication/confirm/{id}` |

This breaks both action buttons in the Actions tab:
- "Submit" for resort forms → 404
- "Mark as Sent" for VRBO messages → 404

**Fix:** Add `/api` prefix to compliance and communication routers to match dashboard, reports, accounting, and query routers.

### 3. Airbnb Pre-Arrival — No Operator Notification

**Severity:** Medium — Airbnb guests may not receive pre-arrival details

In `app/communication/messenger.py`, the Airbnb pre-arrival path:
1. Renders the template with lock code and property details
2. Sets `status = 'sent'` immediately
3. Does NOT email the operator

The item disappears from the Actions tab (which only shows `status='pending'`). The operator never knows a pre-arrival message is ready to be sent via the Airbnb app. The VRBO/RVshare path correctly emails the operator.

---

## Integration Issues

### 4. LLM Schema Attribution Mismatch

**Severity:** Low — affects accuracy of some LLM queries about expenses

`app/query/prompt.py` line 81 tells the LLM that expense `attribution` values are `'property', 'shared', 'personal'`. The actual stored values are `'jay', 'minnie', 'shared'`. Queries about property-specific expenses may generate incorrect WHERE clauses.

### 5. Revenue Recognition Not Automated

**Severity:** Informational — documented design decision

After CSV import, the operator must separately call `POST /api/accounting/revenue/recognize-all` to create journal entries. This is by design but not surfaced in the UI. Without this step, financial metrics on the dashboard show zero revenue.

---

## Requirements Coverage

### Fully Satisfied (39/44)

| Group | Requirements | Count |
|-------|-------------|-------|
| Infrastructure | INFR-01 through INFR-06 | 6 |
| Data Ingestion | INGS-01 through INGS-07 | 7 |
| Accounting | ACCT-01 through ACCT-09 | 9 |
| Resort Compliance | COMP-01 through COMP-05, COMP-07 | 6 |
| Guest Communication | COMM-03, COMM-05, COMM-06, COMM-07 | 4 |
| Dashboard & Reporting | DASH-01 through DASH-06, DASH-08 | 7 |

### Partially Satisfied (4/44)

| Requirement | Status | Issue |
|-------------|--------|-------|
| COMM-01 | PARTIAL | Airbnb welcome depends on operator's one-time native messaging setup — cannot verify from code |
| COMM-02 | PARTIAL | Airbnb pre-arrival rendered but operator not notified — no delivery mechanism |
| COMM-04 | PARTIAL | Native messaging only covers welcome trigger, not pre-arrival |
| COMP-06 | UNCERTAIN | Host info from config fields exists but not connected to PDF fill at runtime — pre-baked in template |

### Blocked (1/44)

| Requirement | Status | Issue |
|-------------|--------|-------|
| DASH-07 | BLOCKED | Both action dismiss buttons 404 due to router prefix mismatch |

---

## Cross-Phase Integration

| Integration Point | Status | Notes |
|---|---|---|
| Ingestion → Compliance (resort submissions) | WIRED | normalizer creates submissions, background task processes |
| Ingestion → Communication (logs + scheduler) | WIRED | Communication logs created, pre-arrival jobs scheduled |
| Ingestion → Accounting (revenue recognition) | PARTIAL | Bookings stored; recognition is manual operator step |
| Accounting → Reports (P&L, balance sheet, income) | WIRED | Reports query journal_entries + journal_lines |
| Accounting → Dashboard metrics | WIRED | Dashboard metrics aggregate journal lines |
| Compliance → Dashboard actions | WIRED | Pending resort submissions appear as actions |
| Communication → Dashboard actions | WIRED | Pending VRBO messages appear as actions |
| Dashboard → Compliance submit | BROKEN | apiFetch 404 — router prefix mismatch |
| Dashboard → Communication confirm | BROKEN | apiFetch 404 — router prefix mismatch |
| LLM Query → live data | WIRED | Full SSE pipeline through sqlglot validation |
| LLM Schema → actual tables | PARTIAL | Attribution enum values wrong in prompt |
| Ollama health gate → Query tab | WIRED | Health polling disables tab when unavailable |
| Bank reconciliation → Dashboard actions | WIRED | Unreconciled items appear as actions |
| Airbnb pre-arrival → operator notification | BROKEN | Status flips to 'sent' with no notification |
| VRBO welcome → operator notification | WIRED | Background task emails operator |
| VRBO pre-arrival → operator notification | WIRED | Scheduler fires, emails operator |
| Expense categorization → journal → P&L | WIRED | Full chain wired |
| Startup → scheduler rebuild | WIRED | Lifespan rebuilds pre-arrival jobs |

**Score:** 14/18 integration points wired, 3 broken, 1 partial

---

## E2E User Flows

| Flow | Status | Break Point |
|------|--------|-------------|
| Airbnb booking → dashboard visibility | PARTIAL | Revenue recognition not automated; action buttons broken |
| VRBO booking → operator notifications | PARTIAL | Welcome email works; action buttons broken |
| Financial query via LLM | COMPLETE | Full pipeline works (requires Ollama + data) |
| Bank reconciliation → dashboard | PARTIAL | Backend works; no frontend for running reconciliation |
| Expense tracking → P&L | PARTIAL | Backend works; no frontend for categorizing transactions |

**Score:** 1/5 flows fully complete through the UI, 4 partial (backend works but missing frontend or have broken wiring)

---

## Tech Debt by Phase

### Phase 1: Foundation
- Hardcoded DB fallback URL in `app/db.py` and `alembic/env.py` (dev convenience)
- `CHANGE_ME` placeholders in property config files (expected for operator setup)

### Phase 2: Data Ingestion
- Airbnb CSV column names unverified against real export (SYNTHETIC)
- Mercury CSV column names unverified (LOW confidence)
- VRBO CSV column names from docs only (MEDIUM confidence)
- `listing_slug_map` contains `CHANGE_ME` placeholder keys

### Phase 5: Resort PDF Compliance
- `host_name`/`host_phone` config fields not connected to PDF fill (pre-baked in template)
- `CHANGE_ME` placeholders in resort contact fields

### Phase 7: Dashboard
- Reports tab is a placeholder with endpoint descriptions
- No data management UI anywhere in the frontend

### Phase 8: LLM Natural Language Interface
- Attribution enum values in `prompt.py` don't match actual data

**Total: 12 tech debt items across 5 phases**

---

## Human Verification Items (Accumulated)

These items require live system testing and cannot be verified from code analysis:

1. Docker Compose cold start (Phase 1)
2. Ollama status reporting (Phase 1)
3. Config fail-fast behavior (Phase 1)
4. Real Airbnb CSV column names (Phase 2)
5. Real Mercury CSV column names (Phase 2)
6. End-to-end CSV import + bookings list (Phase 2)
7. Reconciliation amount matching (Phase 3)
8. Chart of accounts seeded by migration (Phase 3)
9. P&L revenue sign convention (Phase 4)
10. Balance sheet accounting equation (Phase 4)
11. Expense category auto-creates journal entry (Phase 4)
12. PDF cross-viewer display test (Phase 5)
13. End-to-end email delivery (Phase 5)
14. Host info source in PDF template (Phase 5)
15. Airbnb native scheduled messages configured (Phase 6)
16. VRBO operator email delivery (Phase 6)
17. APScheduler pre-arrival job fire (Phase 6)
18. Dark mode visual consistency (Phase 7)
19. Mobile responsiveness (Phase 7)
20. Property selector filter behavior (Phase 7)
21. Calendar booking bar rendering (Phase 7)
22. LLM end-to-end streaming response (Phase 8)
23. LLM clarification behavior (Phase 8)
24. Ollama health gate behavior (Phase 8)

---

*Audited: 2026-02-28*
*Auditor: Claude (gsd-milestone-auditor)*

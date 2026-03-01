# Roadmap: Rental Management Suite

## Overview

Build a self-hosted vacation rental management platform in twelve phases. Phases 1-8 deliver the core backend and read-only dashboard. Phases 9-12 close gaps identified by the v1 milestone audit: integration bug fixes, data import UI, financial management UI, and interactive reports. Each phase delivers a coherent, independently verifiable capability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Project scaffolding, Docker deployment, config schema, and database with migrations
- [ ] **Phase 2: Data Ingestion** - CSV import pipelines for Airbnb, VRBO, Mercury, and manual RVshare entry with unified booking schema
- [x] **Phase 3: Accounting Engine** - Double-entry bookkeeping ledger, multi-platform transaction tracking, and bank reconciliation
- [x] **Phase 4: Financial Reports** - P&L statements, balance sheets, income statements, and bank transaction categorization
- [x] **Phase 5: Resort PDF Compliance** - Automated PDF form filling, email submission, deadline tracking, and submission audit trail
- [x] **Phase 6: Guest Communication** - Booking confirmation and pre-arrival messages via platform messaging with config-driven templates
- [x] **Phase 7: Dashboard** - Web dashboard showing financial metrics, occupancy, booking calendar, and pending actions
- [x] **Phase 8: LLM Natural Language Interface** - Ollama-powered text-to-SQL query interface for plain-English financial questions
- [ ] **Phase 9: Integration & Wiring Fixes** - Router prefix fixes, Airbnb pre-arrival notification, LLM schema correction, revenue recognition automation
- [ ] **Phase 10: Data Import UI** - Frontend CSV upload, RVshare manual entry form, import history view
- [ ] **Phase 11: Financial Management UI** - Bank transaction categorization, expense management, loan payments, reconciliation dashboard
- [ ] **Phase 12: Reports UI** - Interactive P&L, balance sheet, and income statement viewers

## Phase Details

### Phase 1: Foundation
**Goal**: The system runs, deploys, and loads configuration — everything else is built on top of this
**Depends on**: Nothing (first phase)
**Requirements**: INFR-01, INFR-02, INFR-03, INFR-04, INFR-05, INFR-06
**Success Criteria** (what must be TRUE):
  1. Running `docker-compose up` starts all services with no manual setup steps beyond copying config.example.yaml
  2. The system connects to the local Ollama instance and reports its status at startup
  3. All property-specific data (unit names, lock codes, resort contacts, templates) lives in config files — no hardcoded values in source code
  4. Database schema deploys via Alembic migration on first start with no manual SQL required
  5. Email and PDF field mapping templates are stored in config files and editable without touching code
**Plans:** 6 plans

Plans:
- [ ] 01-01-PLAN.md — Docker Compose services, Dockerfile, pyproject.toml with uv, .env.example, .gitignore
- [ ] 01-02-PLAN.md — Pydantic Settings config schema with YAML loading and per-property config discovery
- [ ] 01-03-PLAN.md — SQLAlchemy 2.0 models, database engine, and Alembic migration for properties table
- [ ] 01-04-PLAN.md — FastAPI app with lifespan startup checks, structured logging, and GET /health endpoint
- [ ] 01-05-PLAN.md — Jinja2 template engine with per-property overrides, PDF field mapping schema, and CLI setup wizard
- [ ] 01-06-PLAN.md — Gap closure: README setup docs, config-driven resort check-in instructions, entry point fix

### Phase 2: Data Ingestion
**Goal**: Real booking and transaction data flows from all three platforms into a unified ledger
**Depends on**: Phase 1
**Requirements**: INGS-01, INGS-02, INGS-03, INGS-04, INGS-05, INGS-06, INGS-07
**Success Criteria** (what must be TRUE):
  1. User can upload an Airbnb Transaction History CSV and see bookings appear in the system with correct guest details and amounts
  2. User can upload a VRBO Payments Report CSV and see VRBO reservations normalized to the same schema as Airbnb bookings
  3. User can upload a Mercury bank transaction CSV and see bank transactions appear in the system with correct amounts and dates
  4. User can manually enter an RVshare booking with all required fields and see it in the unified booking list alongside Airbnb and VRBO bookings
  5. Re-importing the same CSV does not create duplicate records
  6. Raw CSV files are archived with timestamp before processing so every import is auditable
**Plans:** 6 plans

Plans:
- [ ] 02-01-PLAN.md — ORM models (Booking, BankTransaction, ImportRun), Pydantic schemas, Alembic migration, new deps (polars, python-multipart), config additions (archive_dir, listing_slug_map)
- [ ] 02-02-PLAN.md — Normalizer core: CSV reading, archive-before-write, PostgreSQL upsert with xmax detection, ImportRun recording, property slug resolution
- [ ] 02-03-PLAN.md — Airbnb CSV adapter: header validation, apostrophe/date normalization, multi-row grouping by confirmation code
- [ ] 02-04-PLAN.md — VRBO CSV adapter: header validation, payout grouping by Reservation ID, Check In/Check Out date parsing
- [ ] 02-05-PLAN.md — Mercury CSV adapter: header validation, transaction deduplication key determination, amount parsing
- [ ] 02-06-PLAN.md — API endpoints: 3 CSV upload routes, RVshare manual entry, import history, bookings list, bank transactions list

### Phase 3: Accounting Engine
**Goal**: Every booking and bank transaction is correctly recorded as double-entry journal entries, with platform payouts reconciled against bank deposits
**Depends on**: Phase 2
**Requirements**: ACCT-01, ACCT-05, ACCT-06, ACCT-07, ACCT-08, ACCT-09
**Success Criteria** (what must be TRUE):
  1. Every imported booking produces journal entries where debits equal credits — the ledger never has an imbalanced entry
  2. Multi-row Airbnb payout events (booking creation, payout release, adjustments) group correctly by confirmation code and produce a single net revenue figure
  3. User can see unreconciled transactions — platform payouts that have no matching bank deposit and bank deposits that have no matching payout
  4. Expenses can be recorded and categorized (rent, utilities, maintenance, supplies) with each category appearing as a separate line in reports
  5. Loan payments split correctly into principal and interest components in the ledger
**Plans:** 6 plans

Plans:
- [ ] 03-01-PLAN.md — Account, JournalEntry, JournalLine models + journal builder with balance enforcement + Alembic migration 003 with chart of accounts seed
- [ ] 03-02-PLAN.md — Revenue recognition: Airbnb deferred-then-recognized pattern, VRBO/RVshare single-event, configurable fee model
- [ ] 03-03-PLAN.md — Expense tracking: Expense model, record_expense with journal entry, bulk CSV import, 12 Schedule E categories
- [ ] 03-04-PLAN.md — Loan tracking: Loan model, record_loan_payment with principal/interest split, loan balance calculation
- [ ] 03-05-PLAN.md — Bank reconciliation: exact amount + 7-day window matching, auto-match/needs-review/unreconciled queue
- [ ] 03-06-PLAN.md — Accounting API: 12 endpoints for journal entries, expenses, loans, reconciliation, and account balances

### Phase 4: Financial Reports
**Goal**: Users can view accurate P&L statements, balance sheets, and income statements per property, and categorize bank transactions
**Depends on**: Phase 3
**Requirements**: ACCT-02, ACCT-03, ACCT-04, DASH-08
**Success Criteria** (what must be TRUE):
  1. User can generate a P&L statement for a single property or combined, filtered by month or year-to-date, showing revenue by source and expenses by category
  2. User can generate a balance sheet showing current assets, liabilities, and equity with correct totals
  3. User can generate an income statement showing revenue and expense breakdown for any date range
  4. User can view imported bank transactions and assign each a category (rent, utilities, maintenance, etc.) with the categorization persisting across sessions
**Plans**: 4 plans

Plans:
- [x] 04-01-PLAN.md — Migration 004 (category/journal_entry_id on bank_transactions, property_id on loans), ORM updates, resolve_period() helper, category constants
- [x] 04-02-PLAN.md — P&L statement generator with platform+month revenue breakdown, per-property and combined views, shared expense allocation
- [x] 04-03-PLAN.md — Balance sheet (loan balances via get_loan_balance, retained earnings) and income statement (totals/monthly breakdown)
- [x] 04-04-PLAN.md — Bank transaction categorization: list/filter, single/bulk assignment, auto-expense creation for expense categories

### Phase 5: Resort PDF Compliance
**Goal**: New bookings automatically trigger PDF form preparation and email submission to the resort, with deadline tracking ensuring no 3-day submission window is missed
**Depends on**: Phase 2
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06, COMP-07
**Success Criteria** (what must be TRUE):
  1. When a new booking arrives, the system fills the resort booking form with guest details and unit/site number from config — the filled PDF displays correctly in Adobe Reader, macOS Preview, and iOS Mail (no blank fields)
  2. The filled form and the platform booking confirmation are emailed to the resort contact address from config without manual intervention
  3. User can see the submission status of every booking (pending, submitted, confirmed) from a single view
  4. Bookings within 3 days of the arrival date that have not been submitted are visibly flagged as urgent
  5. Host information in the form comes from config — no property-specific data is hardcoded
**Plans**: 6 plans

Plans:
- [x] 05-01-PLAN.md — Foundation: new deps (pymupdf, aiosmtplib, apscheduler, tenacity), SMTP config, host info on PropertyConfig, ResortSubmission model + migration 005, docker-compose confirmations volume
- [x] 05-02-PLAN.md — PDF form filling: AcroForm detection, field-mapping-driven filling with field.update() + doc.bake(), field enumeration; checkpoint to verify actual Sun Retreats form
- [x] 05-03-PLAN.md — Email delivery (aiosmtplib + tenacity retry) and confirmation file matching + email subject/body formatting
- [x] 05-04-PLAN.md — Submission orchestrator: PDF fill + email send + DB status + preview mode; wire into booking import for auto-creation
- [x] 05-05-PLAN.md — Urgency checker: daily APScheduler job flags pending submissions within 3 days of check-in, sends operator digest alert
- [x] 05-06-PLAN.md — Compliance API: submissions list, manual submit, n8n confirmation webhook, preview approval, batch pending processor

### Phase 6: Guest Communication
**Goal**: Guests receive a welcome message upon booking and arrival details 2-3 days before check-in, driven entirely by config-editable templates
**Depends on**: Phase 2
**Requirements**: COMM-01, COMM-02, COMM-03, COMM-04, COMM-05, COMM-06, COMM-07
**Success Criteria** (what must be TRUE):
  1. A new Airbnb booking triggers a welcome message sent through Airbnb's native scheduled messaging — no manual action required
  2. 2-3 days before check-in, an arrival message is sent with the correct lock code and property details for the booked unit, pulled from config
  3. Templates use variable substitution so guest name, check-in date, property name, and lock code appear correctly in every message
  4. For VRBO bookings, the system prepares the complete message text and notifies the operator to send manually (no VRBO messaging API available)
  5. Message templates are editable in config files without code changes or system restart
**Plans**: 5 plans

Plans:
- [x] 06-01-PLAN.md — CommunicationLog model, PropertyConfig extensions, message templates, migration 006
- [x] 06-02-PLAN.md — Messenger service with template rendering and platform-specific send logic
- [x] 06-03-PLAN.md — Pre-arrival scheduler with DateTrigger and startup rebuild
- [x] 06-04-PLAN.md — Ingestion pipeline hooks for automatic communication triggers
- [x] 06-05-PLAN.md — Communication API router and lifespan startup wiring

### Phase 7: Dashboard
**Goal**: Users can see the operational state of the business at a glance — financials, occupancy, upcoming bookings, and pending actions — from a clean interface that non-technical users can navigate
**Depends on**: Phase 4, Phase 5, Phase 6
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-07
**Success Criteria** (what must be TRUE):
  1. The dashboard home page shows YTD revenue, YTD expenses, and current-month profit for each property without any navigation
  2. User can see occupancy rate and a booking trend chart for each property covering the last 12 months
  3. A calendar view shows all upcoming and past bookings across both properties in a single view, color-coded by platform
  4. Pending actions (unsubmitted resort forms approaching deadline, VRBO messages awaiting manual send) are visible on the dashboard and dismissable when actioned
  5. Kim can use the dashboard to check financial and booking status without requiring explanation of financial concepts
**Plans**: 6 plans

Plans:
- [ ] 07-01-PLAN.md — Frontend scaffold: React + Vite + shadcn/ui project, Docker multi-stage build, FastAPI SPA serving with CORS
- [ ] 07-02-PLAN.md — Dashboard backend API: 5 endpoints for properties, metrics, bookings, occupancy, and pending actions
- [ ] 07-03-PLAN.md — App shell and Home tab: header with property selector, tabs, dark mode, stat cards, booking trend and occupancy charts
- [ ] 07-04-PLAN.md — Calendar tab: month grid view with booking bars, timeline/Gantt view, booking detail popovers
- [ ] 07-05-PLAN.md — Actions tab with expandable pending items and Reports tab placeholder
- [ ] 07-06-PLAN.md — Polish: badge counts, empty/error/loading states, mobile responsiveness, dark mode audit, human verification

### Phase 8: LLM Natural Language Interface
**Goal**: Kim (and Thomas) can ask financial questions in plain English and receive accurate answers backed by SQL queries against the live ledger — never from LLM arithmetic
**Depends on**: Phase 4, Phase 7
**Requirements**: DASH-04, DASH-05, DASH-06
**Success Criteria** (what must be TRUE):
  1. Kim can type "how much did we make on Jay in January?" and receive a correct answer that matches the P&L statement
  2. The system never performs arithmetic in the LLM — every number in the response comes from a SQL query result
  3. Thomas can see the SQL query that produced each answer for debugging and verification
  4. When the LLM cannot generate a valid query (ambiguous question, schema gap), it says so clearly rather than returning a hallucinated number
**Plans:** 4 plans

Plans:
- [x] 08-01-PLAN.md — Backend query modules: schema-aware prompt, sqlglot SQL validator, Ollama AsyncClient, new deps (ollama, sse-starlette, sqlglot)
- [x] 08-02-PLAN.md — SSE streaming API endpoint: POST /api/query/ask with two-phase LLM pipeline (SQL gen + narrative streaming)
- [x] 08-03-PLAN.md — Frontend chat UI: Zustand ephemeral store, SSE streaming hook, chat components (starter prompts, message bubbles, Show SQL, result tables)
- [x] 08-04-PLAN.md — Dashboard integration: Query tab in AppShell, Ollama health gate, end-to-end human verification

### Phase 9: Integration & Wiring Fixes
**Goal**: All existing features work correctly end-to-end — action buttons dismiss, operator notifications fire, LLM queries return accurate results, and revenue recognition triggers automatically after import
**Depends on**: Phase 8
**Requirements**: DASH-07, COMM-02, COMM-04
**Gap Closure**: Closes 3 critical/high gaps and 2 integration issues from v1 audit
**Success Criteria** (what must be TRUE):
  1. Clicking "Submit" on a pending resort form in the Actions tab succeeds (no 404) and the submission status updates
  2. Clicking "Mark as Sent" on a pending VRBO message in the Actions tab succeeds (no 404) and the action disappears
  3. When the Airbnb pre-arrival scheduler fires, the operator receives an email with the rendered message text — the status does NOT flip to 'sent' until the operator confirms
  4. LLM queries about property-specific expenses generate correct WHERE clauses using actual attribution values ('jay', 'minnie', 'shared')
  5. After CSV import, revenue recognition runs automatically — dashboard financial metrics reflect imported booking revenue without a separate manual API call
**Plans:** 2 plans

Plans:
- [x] 09-01-PLAN.md — Router prefix fixes for compliance/communication, LLM attribution correction, Airbnb pre-arrival verification
- [x] 09-02-PLAN.md — Automatic revenue recognition after CSV import via BackgroundTask

### Phase 10: Data Import UI
**Goal**: Non-technical users can upload CSV files and enter bookings through the web dashboard — no API calls or command-line knowledge required
**Depends on**: Phase 9
**Requirements**: (Satisfies DASH-07 non-technical usability for data operations)
**Gap Closure**: Closes the critical "no frontend data entry" gap from v1 audit
**Success Criteria** (what must be TRUE):
  1. User can drag-and-drop or file-pick an Airbnb CSV, VRBO CSV, or Mercury CSV and see a success/error result with import details
  2. User can fill out an RVshare booking form in the browser and see the new booking appear in the bookings list
  3. User can view import history showing past uploads with timestamps, file names, and record counts
  4. After a successful CSV import, new bookings and bank transactions appear on the dashboard without any additional manual steps

### Phase 11: Financial Management UI
**Goal**: Users can categorize bank transactions, record expenses, manage loan payments, and run bank reconciliation entirely from the web dashboard
**Depends on**: Phase 10
**Requirements**: (Satisfies DASH-07 non-technical usability for financial operations)
**Gap Closure**: Closes the "no data management UI" gap from v1 audit
**Success Criteria** (what must be TRUE):
  1. User can view bank transactions and assign categories (rent, utilities, maintenance, etc.) with bulk or individual assignment
  2. User can record a new expense with amount, category, date, and description — the expense appears in the P&L
  3. User can record a loan payment with principal/interest split — the loan balance updates
  4. User can view unreconciled items and confirm or reject suggested matches between platform payouts and bank deposits

### Phase 12: Reports UI
**Goal**: Users can generate and view financial reports (P&L, balance sheet, income statement) interactively from the dashboard with property and date filters
**Depends on**: Phase 11
**Requirements**: (Completes DASH-07 by replacing Reports tab placeholder with real report viewers)
**Gap Closure**: Closes the "Reports tab is placeholder" tech debt from v1 audit
**Success Criteria** (what must be TRUE):
  1. User can view a P&L statement filtered by property (individual or combined) and date range (month, quarter, YTD, custom)
  2. User can view a balance sheet showing assets, liabilities, equity, and loan balances as of a selected date
  3. User can view an income statement with revenue and expense breakdown, with optional monthly detail view
  4. Reports display cleanly on both desktop and mobile with proper number formatting and section grouping

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> ... -> 8 -> 9 -> 10 -> 11 -> 12

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 6/6 | Complete ✓ | 2026-02-27 |
| 2. Data Ingestion | 6/6 | Complete ✓ | 2026-02-27 |
| 3. Accounting Engine | 6/6 | Complete ✓ | 2026-02-27 |
| 4. Financial Reports | 4/4 | Complete ✓ | 2026-02-28 |
| 5. Resort PDF Compliance | 6/6 | Complete ✓ | 2026-02-28 |
| 6. Guest Communication | 5/5 | Complete ✓ | 2026-02-28 |
| 7. Dashboard | 6/6 | Complete ✓ | 2026-02-28 |
| 8. LLM Natural Language Interface | 4/4 | Complete ✓ | 2026-03-01 |
| 9. Integration & Wiring Fixes | 2/2 | Complete ✓ | 2026-02-28 |
| 10. Data Import UI | 0/? | Not Started | — |
| 11. Financial Management UI | 0/? | Not Started | — |
| 12. Reports UI | 0/? | Not Started | — |

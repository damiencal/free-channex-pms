# Roadmap: Rental Management Suite

## Overview

Build a self-hosted vacation rental management platform in eight phases, following the dependency order that research validated: foundation before data, data before accounting, accounting before reports and compliance, compliance and communication before the dashboard that displays their status, and the LLM query interface last when the schema is stable and live data exists to make it useful. Each phase delivers a coherent, independently verifiable capability — the system is never partially functional for an extended period.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Project scaffolding, Docker deployment, config schema, and database with migrations
- [ ] **Phase 2: Data Ingestion** - CSV import pipelines for Airbnb, VRBO, Mercury, and manual RVshare entry with unified booking schema
- [ ] **Phase 3: Accounting Engine** - Double-entry bookkeeping ledger, multi-platform transaction tracking, and bank reconciliation
- [ ] **Phase 4: Financial Reports** - P&L statements, balance sheets, income statements, and bank transaction categorization
- [ ] **Phase 5: Resort PDF Compliance** - Automated PDF form filling, email submission, deadline tracking, and submission audit trail
- [ ] **Phase 6: Guest Communication** - Booking confirmation and pre-arrival messages via platform messaging with config-driven templates
- [ ] **Phase 7: Dashboard** - Web dashboard showing financial metrics, occupancy, booking calendar, and pending actions
- [ ] **Phase 8: LLM Natural Language Interface** - Ollama-powered text-to-SQL query interface for plain-English financial questions

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
**Plans**: TBD

Plans:
- [ ] 03-01: Double-entry journal entry models with debit/credit enforcement and idempotent upsert by stable transaction ID
- [ ] 03-02: Revenue recognition — booking ingestion triggers journal entries; Airbnb multi-row grouping by confirmation code
- [ ] 03-03: Expense tracking — categorized expense entry with Schedule E-aligned categories
- [ ] 03-04: Loan tracking — principal/interest split on loan payments
- [ ] 03-05: Bank reconciliation — match platform payouts to Mercury deposits; unreconciled queue with mismatch flagging
- [ ] 03-06: Accounting engine API endpoints (journal entry query, unreconciled list, ledger balance)

### Phase 4: Financial Reports
**Goal**: Users can view accurate P&L statements, balance sheets, and income statements per property, and categorize bank transactions
**Depends on**: Phase 3
**Requirements**: ACCT-02, ACCT-03, ACCT-04, DASH-08
**Success Criteria** (what must be TRUE):
  1. User can generate a P&L statement for a single property or combined, filtered by month or year-to-date, showing revenue by source and expenses by category
  2. User can generate a balance sheet showing current assets, liabilities, and equity with correct totals
  3. User can generate an income statement showing revenue and expense breakdown for any date range
  4. User can view imported bank transactions and assign each a category (rent, utilities, maintenance, etc.) with the categorization persisting across sessions
**Plans**: TBD

Plans:
- [ ] 04-01: P&L statement generator — per-property and combined, monthly and YTD, revenue by platform and expenses by category
- [ ] 04-02: Balance sheet generator — assets, liabilities, equity with period-end snapshot
- [ ] 04-03: Income statement generator — revenue and expense breakdown for configurable date range
- [ ] 04-04: Bank transaction categorization — view uncategorized transactions, assign categories, persist assignments

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
**Plans**: TBD

Plans:
- [ ] 05-01: PDF form filling with PyMuPDF — config-driven field mapping, appearance stream generation, and flattening; test in three viewers before any live submission
- [ ] 05-02: Unit-to-site-number mapping via config (Jay → 110, Minnie → 170) and host info pre-population from config
- [ ] 05-03: Platform booking confirmation attachment — retrieve confirmation from ingestion archive and attach to email
- [ ] 05-04: Resort email submission with fastapi-mail — configurable recipient, subject, and body template
- [ ] 05-05: Submission status tracking (pending/submitted/confirmed) with idempotent submission prevention
- [ ] 05-06: Deadline flagging — scheduler job per booking; flag as urgent when arrival is within 3 days and form not submitted
- [ ] 05-07: Compliance API endpoints (submission status list, manual trigger, confirm submission)

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
**Plans**: TBD

Plans:
- [ ] 06-01: Message template engine — config-driven templates with variable substitution (guest name, dates, property, lock code)
- [ ] 06-02: Airbnb native scheduled messaging integration — configure welcome and pre-arrival triggers in Airbnb platform; system tracks send status
- [ ] 06-03: APScheduler setup with SQLAlchemy job store — scheduler service embedded in FastAPI process; dynamic job creation per booking
- [ ] 06-04: Pre-arrival message scheduler — job created on booking ingestion, fires 2-3 days before check-in (configurable timing)
- [ ] 06-05: VRBO semi-automated messaging — system prepares message text with substituted variables; dashboard notification prompts operator to send manually
- [ ] 06-06: Communication log — record of all sent/prepared messages per booking with timestamps

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
**Plans**: TBD

Plans:
- [ ] 07-01: React + Vite + shadcn/ui project setup within Docker; FastAPI CORS config; API client layer
- [ ] 07-02: Financial metrics panel — YTD revenue, expenses, profit per property; connects to Phase 4 report endpoints
- [ ] 07-03: Occupancy and booking trend charts — per-property occupancy rate and 12-month booking volume; shadcn chart components
- [ ] 07-04: Booking calendar — cross-property calendar view with platform color-coding; upcoming and past bookings
- [ ] 07-05: Pending actions queue — unsubmitted forms, VRBO messages awaiting send, unreconciled transactions; dismissable with confirmation
- [ ] 07-06: Navigation and layout — clean top-nav or sidebar; mobile-readable; no financial jargon in labels

### Phase 8: LLM Natural Language Interface
**Goal**: Kim (and Thomas) can ask financial questions in plain English and receive accurate answers backed by SQL queries against the live ledger — never from LLM arithmetic
**Depends on**: Phase 4, Phase 7
**Requirements**: DASH-04, DASH-05, DASH-06
**Success Criteria** (what must be TRUE):
  1. Kim can type "how much did we make on Jay in January?" and receive a correct answer that matches the P&L statement
  2. The system never performs arithmetic in the LLM — every number in the response comes from a SQL query result
  3. Thomas can see the SQL query that produced each answer for debugging and verification
  4. When the LLM cannot generate a valid query (ambiguous question, schema gap), it says so clearly rather than returning a hallucinated number
**Plans**: TBD

Plans:
- [ ] 08-01: Schema-aware prompt construction — inject schema definition at startup, cache, include table/column descriptions and example queries
- [ ] 08-02: Text-to-SQL pipeline — Ollama client, relative date resolution to absolute ranges before querying, read-only SQL validation
- [ ] 08-03: Query execution and response — run validated SQL, format results, generate natural language description of pre-computed results (LLM never computes)
- [ ] 08-04: Dashboard query interface — text input, response display with source data rows, show-SQL toggle for Thomas, graceful failure messages
- [ ] 08-05: LLM model benchmarking and selection — test Qwen2.5-Coder 14B vs. available models against real schema before committing

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 6/6 | Complete ✓ | 2026-02-27 |
| 2. Data Ingestion | 6/6 | Complete ✓ | 2026-02-27 |
| 3. Accounting Engine | 0/6 | Not started | - |
| 4. Financial Reports | 0/4 | Not started | - |
| 5. Resort PDF Compliance | 0/7 | Not started | - |
| 6. Guest Communication | 0/6 | Not started | - |
| 7. Dashboard | 0/6 | Not started | - |
| 8. LLM Natural Language Interface | 0/5 | Not started | - |

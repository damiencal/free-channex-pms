# Project Research Summary

**Project:** Roost — Self-Hosted Vacation Rental Operations Platform
**Domain:** Vacation rental operations automation (accounting, compliance, guest communication, financial reporting)
**Researched:** 2026-02-26
**Confidence:** MEDIUM (platform-specific data access constraints limit some areas)

## Executive Summary

This is a self-hosted operations tool for a 2-unit short-term rental business at Sun Retreats Fort Myers Beach, managing bookings across Airbnb, VRBO, and RVshare with Mercury Bank as the financial account. The core problem it solves: manual PDF form submission to the resort (3-day deadline, failure-prone), fragmented financial tracking across three platforms, and a non-technical co-owner (Kim) who needs to ask financial questions in plain English. The right approach is a FastAPI + SQLite backend with React dashboard, using CSV-import-based ingestion (not platform APIs, which are unavailable to individual hosts), double-entry accounting via SQLAlchemy models, APScheduler for time-triggered compliance automation, and a local Ollama LLM for natural language financial queries. The system should be config-driven from day one so it can be open-sourced without leaking property data.

The recommended build order follows clear dependency layers: foundation first (database schema, config loading, Docker), then ingestion adapters (the fastest path to real data), then the accounting engine and PDF automation (the two highest-value features), then the dashboard and scheduler (glue and automation), and finally the LLM query interface (which requires a stable schema and live data to be useful). This order is not arbitrary — accounting correctness gates everything downstream, and the resort compliance deadline makes PDF automation the most time-critical deliverable.

The most dangerous risks are architectural mistakes that are expensive to undo: using Airbnb iCal as a data source (it strips all guest data), letting the LLM compute financial numbers (it hallucinates), and relying on VRBO's messaging API (it does not exist for non-partners). RVshare's data access is entirely unverified — no documented export API exists, and manual entry fallback must be designed in from the start. These are not edge cases to handle later; they are load-bearing constraints that shape the ingestion and LLM architecture on day one.

---

## Key Findings

### Recommended Stack

Python 3.12 + FastAPI + SQLite (via aiosqlite) is the right core for a single-host self-hosted tool with one concurrent user. Adding PostgreSQL would add Docker complexity for zero practical gain at this scale. SQLAlchemy 2.x with async sessions bridges both databases if migration ever becomes necessary. For the frontend, React + Vite + shadcn/ui is the clear choice: shadcn's admin dashboard components are production-ready and reduce UI build time significantly for a financial dashboard with charts and tables.

For integrations: Polars (not pandas) for CSV ingestion (5-25x faster, less memory), `pypdf` + `pikepdf` for PDF form filling (with PyMuPDF as the safer alternative for appearance stream rendering), the official `ollama` Python client directly (no LangChain abstraction needed for a simple text-to-SQL pipeline), and APScheduler 3.x (not 4.0 alpha, not Celery) for in-process scheduling with no external broker. The `python-accounting` library is dormant and should not be used — implement double-entry bookkeeping directly in SQLAlchemy models.

**Core technologies:**
- Python 3.12 + FastAPI 0.133.1: async-native API server, auto-docs, Pydantic integration
- SQLite + aiosqlite + SQLAlchemy 2.x: right-sized database for single-host; async-capable; Alembic migrations
- Pydantic + pydantic-settings: config validation and YAML/env config loading
- React 18 + Vite 6 + shadcn/ui: financial dashboard with charts, tables, and query interface
- Polars 1.38.1: primary CSV ingestion and normalization
- pypdf 6.7.3 + pikepdf 10.3.0: PDF form filling (prefer PyMuPDF for flattened output)
- ollama 0.6.1: direct LLM client for local Ollama text-to-SQL interface
- APScheduler 3.11.2: in-process job scheduling with SQLAlchemy job store
- Docker + Docker Compose: single-command deployment

### Expected Features

**Must have (table stakes — v1 launch):**
- Airbnb, VRBO, and Mercury CSV import pipelines — core accounting inputs
- Unified transaction ledger — all income/expenses in one queryable schema
- Per-property P&L statement (monthly + YTD) — primary financial report
- Resort PDF auto-fill and email — the defining compliance use case; 3-day deadline
- Booking confirmation and pre-arrival messages — Airbnb native; VRBO/RVshare manual fallback
- Dashboard with key metrics (occupancy, YTD revenue, YTD expenses, pending bookings)
- Config-driven templates and property data — enables open-source deployment
- Docker container deployment

**Should have (v1.x, add within first month):**
- Natural language financial queries via Ollama — Kim's primary interaction model; add once ledger schema is stable
- Schedule E expense report — must exist before first tax season post-launch
- Balance sheet — requires depreciation tracking to be scoped first
- VRBO messaging integration — via OwnerRez/Uplisting or VRBO beta API

**Defer (v2+):**
- RVshare automated booking detection — blocked on verifying whether any export mechanism exists
- Cross-platform booking revenue reconciliation (matching platform deposits to Mercury transactions)
- Occupancy heatmap calendar
- Per-platform expense attribution report
- Annual income statement / CPA-ready financial package

**Anti-features (explicitly excluded):**
- Real-time platform sync via webhooks (APIs unavailable; CSV import is sufficient)
- Multi-user RBAC (two admin users on a local network; complexity without benefit)
- Dynamic lock code generation (out of scope; smart lock hardware integration)
- AI-generated message personalization (template + shortcodes is already sufficient for 2 units)

### Architecture Approach

The architecture is a layered monolith: Ingestion Layer (platform adapters) feeds a Core Data Layer (SQLite via SQLAlchemy), which is consumed by an Application Layer (Accounting Engine, Scheduler, PDF Generator, Notifier, LLM Query Interface), exposed through a Presentation Layer (FastAPI REST API + React dashboard). The key architectural decision is one adapter class per platform — adding a new platform is additive, never modifying existing code. All platform-specific quirks are contained within the adapter; the canonical schema is shared. Config-driven property data (YAML loaded via Pydantic Settings) keeps all property-specific values out of code from day one.

**Major components:**
1. Platform Adapters (ingestion/adapters/) — one class per platform; CSV to canonical BookingRecord/BankTransaction
2. Normalizer (ingestion/normalizer.py) — deduplication, validation, DB writes
3. Accounting Engine (accounting/engine.py) — double-entry journal entries; P&L, balance sheet generation
4. PDF Generator (pdf/generator.py) — pypdf/PyMuPDF form filling + flattening; config-driven field mapping
5. Scheduler (scheduler/) — APScheduler with SQLAlchemy job store; dynamic job creation per booking
6. Notifier (notifications/) — fastapi-mail for resort PDF email; platform messaging with manual fallback
7. LLM Query Interface (llm/) — schema-aware prompt construction; SQL generation; read-only execution; natural language response
8. FastAPI App + React Dashboard — thin API layer over the above; financial dashboard with charts

**Build order (per architecture dependency analysis):**
1. DB schema + config loading + Docker
2. Ingestion adapters (self-contained; test against fixture CSVs)
3. Accounting engine (correctness gates all downstream features)
4. PDF generation (standalone; testable with hardcoded data)
5. Scheduler + Notifier (depends on bookings in DB)
6. FastAPI + Dashboard (glue code; build last)
7. LLM query interface (add after schema is stable and live data exists)

### Critical Pitfalls

1. **Airbnb iCal has no guest data** — Since 2019, Airbnb iCal exports contain only blocked dates and a reservation link; no guest name, confirmation code, or email. Never use iCal as the booking data source. Use Airbnb's Transaction History CSV (from the earnings dashboard) as the financial source and parse booking confirmation emails sent to the host for guest details. Design the ingestion pipeline around CSV + email, not iCal.

2. **CSV export format is silently brittle** — Platform CSV exports are UI-generated files with no versioning or changelog. Known Airbnb issues: apostrophe-prefixed numeric fields, mixed US/UK date formats, and missing quote marks causing column spillage. Validate the header row schema on every ingest run; store raw source files unmodified for re-parsing; alert if the header hash changes; never parse by column index.

3. **LLM arithmetic hallucination on financial numbers** — Local Ollama models produce confident incorrect numbers when asked to calculate totals. The LLM interface must never perform arithmetic. Architecture: LLM translates natural language to SQL intent, the database computes the result, the LLM describes the pre-computed result in natural language. This is a hard architectural constraint — enforce it via a `validate_sql()` read-only check and always show the source data rows that produced the answer.

4. **PDF NeedAppearances rendering trap** — pypdf fills form fields but does not regenerate appearance streams, causing PDFs to display as blank in non-compliant viewers (iOS Mail, macOS Preview). Resort staff receive empty forms. Use PyMuPDF (fitz) instead, which generates appearance streams on fill. Always flatten the filled PDF before emailing. Test in Adobe Reader, macOS Preview, and iOS Mail attachment view before any live submission.

5. **VRBO messaging API does not exist for non-partners** — VRBO has no public messaging API for individual hosts. Automated messaging through VRBO requires partner-status API access (OwnerRez, Uplisting). For v1, VRBO messaging must be semi-automated: system prepares message text, notifies the operator to send manually. Alternatively, send direct email to guest using address from the VRBO reservation CSV export. Scope this explicitly to avoid building against an unavailable API.

6. **Airbnb payout timing makes reconciliation non-trivial** — One booking does not equal one payout row. Airbnb payouts are event-driven (booking creation, payout release, adjustments, reversals, BNPL cancellations). Group all transaction rows by confirmation code before computing net income. The fee model also changed in October 2025 (host-only fee at 15.5% for PMS users vs. split-fee model) — flag this as a configurable field.

---

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation and Ingestion
**Rationale:** Everything else depends on having a correct database schema, config loading, and real booking data flowing in. The ingestion adapters are self-contained and testable against fixture CSV files, making them the fastest path to real data. Docker infrastructure must be set up before any other work — named volumes and `.gitignore` from the first commit prevent the most expensive recovery scenarios.
**Delivers:** Working Docker deployment; all three platform CSV parsers and Mercury bank parser; unified transaction ledger populated with real booking data; config.yaml schema with config.example.yaml for open-source use
**Addresses:** Airbnb CSV import, VRBO CSV import, Mercury CSV import, unified transaction ledger, config-driven setup, Docker deployment
**Avoids:** iCal-as-data-source pitfall; CSV format fragility (schema validation from day one); secrets-in-git (gitignore + .env.example from first commit); Docker data loss (named volumes)
**Research flag:** LOW — CSV parsing and Docker setup are well-documented standard patterns. No phase research needed.

### Phase 2: Accounting Engine and Financial Reports
**Rationale:** Accounting correctness is the foundation that P&L reports, Schedule E export, balance sheet, and LLM queries all depend on. The double-entry engine must be built and tested before building anything that reads financial data. This phase is also where Airbnb payout reconciliation complexity (multiple rows per booking) must be handled correctly — it cannot be patched in later without touching every downstream report.
**Delivers:** Double-entry journal entry engine; per-property P&L statement (monthly + YTD); expense categorization aligned with Schedule E; booking-to-payout matching with unreconciled transactions queue
**Addresses:** Per-property P&L, expense categorization, balance sheet (initial), cross-platform income tracking
**Avoids:** Airbnb payout reconciliation pitfall; duplicate ledger entries on re-import (idempotent upserts with stable transaction IDs)
**Research flag:** LOW for double-entry patterns (well-documented). MEDIUM for Schedule E category mapping — verify IRS 2026 category updates before implementation.

### Phase 3: Resort PDF Compliance Automation
**Rationale:** This is the most operationally critical feature — a missed 3-day deadline is a compliance failure. PDF generation is architecturally independent (standalone, testable with hardcoded data) and should be built and validated before connecting to live bookings. The NeedAppearances rendering trap must be solved before any submission reaches the resort.
**Delivers:** Config-driven PDF form filling (PyMuPDF for appearance stream generation + flattening); email submission to resort with attachment; scheduler jobs created on booking ingestion; duplicate submission prevention; audit log of all submissions
**Addresses:** Resort PDF auto-fill, email resort form
**Avoids:** PDF NeedAppearances rendering trap (use PyMuPDF, flatten before send, test in three viewers); duplicate submission (idempotent submission tracking); automated failure silently missed (all automation outcomes logged, dashboard shows pending actions)
**Research flag:** MEDIUM — resort form must be verified as AcroForm (not XFA) before building the PDF pipeline. XFA forms require a different approach entirely.

### Phase 4: Scheduler, Messaging, and Dashboard
**Rationale:** The scheduler depends on bookings existing in the database (Phase 1) and accounting records being correct (Phase 2). Guest messaging depends on the scheduler. The dashboard depends on all the above — it is glue code and should be built last, not first.
**Delivers:** APScheduler with SQLAlchemy job store; automated booking detection (new CSV vs. last-seen hash); booking confirmation messages (Airbnb native; VRBO/RVshare manual fallback with dashboard notification); pre-arrival messages (Airbnb; configurable timing); React dashboard with P&L charts, occupancy metrics, pending actions queue
**Addresses:** Booking confirmation message, pre-arrival message, dashboard with key metrics, booking auto-detection
**Avoids:** VRBO messaging API pitfall (scope v1 messaging as semi-automated; document explicitly); automation silently failing (dashboard pending actions queue); scheduler embedded in API initially (split to own service only if interference observed)
**Research flag:** LOW for APScheduler patterns. LOW for Airbnb native messaging (configure in platform UI, not API). LOW for dashboard (shadcn admin templates are mature).

### Phase 5: LLM Natural Language Query Interface
**Rationale:** The LLM interface requires a stable, queryable schema (Phases 1-2) and meaningful live data to be testable and useful. Building it last ensures the schema won't change underneath it. The LLM-arithmetic-never rule must be established as a hard constraint before writing a single line of the query interface.
**Delivers:** Ollama text-to-SQL pipeline; schema-aware prompt construction (schema injected at startup, cached); SQL validation (read-only enforcement); natural language response with source data attribution; show-generated-SQL debug mode for Thomas
**Addresses:** Natural language financial queries (Kim's use case)
**Avoids:** LLM arithmetic hallucination (LLM describes pre-computed SQL results, never computes); LLM with vague time ranges (resolve relative dates to absolute ranges before querying; show resolved range in response)
**Research flag:** MEDIUM — model selection (Qwen2.5-Coder 14B vs. Devstral 24B) depends on hardware available. Benchmark against real schema before committing to a model. Text-to-SQL accuracy on easy tasks is ~50-54%; design the UI to surface failures gracefully.

### Phase 6: Extended Reporting and v1.x Features
**Rationale:** Tax reporting (Schedule E), balance sheet completion, and VRBO messaging integration add value but do not block core operations. Deliver after v1 is validated in production.
**Delivers:** Schedule E expense export; depreciation tracking (27.5-year residential schedule); balance sheet; VRBO messaging via OwnerRez/Uplisting or VRBO beta API; occupancy heatmap calendar
**Addresses:** Schedule E report, balance sheet, depreciation, VRBO messaging, occupancy heatmap
**Research flag:** HIGH for VRBO messaging integration — requires evaluating OwnerRez/Uplisting API access costs and terms, or VRBO beta API program eligibility. Do not start implementation without confirming the integration path.

### Phase Ordering Rationale

- Foundation before everything: named Docker volumes and .gitignore from the first commit prevent the two highest-cost recovery scenarios (data loss, secrets exposure)
- Ingestion before accounting: the accounting engine needs real data to be meaningfully tested
- Accounting before reports and LLM: all financial outputs share the same underlying journal entries; get the double-entry logic correct once
- PDF automation early (Phase 3, not deferred): resort compliance deadline is operationally critical; this is the feature most at risk from a subtle rendering bug that only manifests in production
- Dashboard and messaging after data exists (Phase 4): building UI before the data model is stable wastes rework
- LLM last (Phase 5): text-to-SQL accuracy is meaningfully higher with human-readable schema and real data; building it earlier means building it twice
- Extended features post-validation (Phase 6): Schedule E and balance sheet require depreciation scoping; VRBO messaging requires external partner evaluation; neither blocks v1 value delivery

### Research Flags

Phases needing deeper research during planning:
- **Phase 3 (PDF Automation):** Verify the resort's actual PDF form type (AcroForm vs. XFA) before building the PDF pipeline. XFA forms require a completely different approach (HTML-to-PDF generation via Playwright instead of form filling). This is a binary decision that changes the implementation plan.
- **Phase 5 (LLM Interface):** Benchmark Qwen2.5-Coder 14B and Devstral 24B against the actual project schema on representative questions before committing. Hardware constraints (available VRAM) may force the model choice.
- **Phase 6 (VRBO Messaging):** Evaluate OwnerRez/Uplisting API access terms and costs before starting implementation. VRBO beta API program eligibility is unclear for self-hosted tools.

Phases with standard patterns (skip research):
- **Phase 1 (Foundation + Ingestion):** CSV parsing, Docker Compose, SQLAlchemy migrations — all well-documented. No research needed.
- **Phase 2 (Accounting Engine):** Double-entry bookkeeping patterns are mature. Implement directly in SQLAlchemy models (python-accounting library is dormant).
- **Phase 4 (Scheduler + Dashboard):** APScheduler 3.x patterns are stable. shadcn/ui admin dashboard templates are well-documented.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions confirmed via PyPI as of Feb 2026; compatibility matrix documented; only PDF library choice has a nuance (pypdf vs PyMuPDF for appearance streams) |
| Features | MEDIUM | Airbnb and VRBO export formats verified via official docs and community sources; RVshare export capabilities are LOW confidence (no public documentation found); Mercury CSV confirmed via secondary sources |
| Architecture | MEDIUM-HIGH | Patterns are standard for this type of system; build order is clear from dependency analysis; Docker service boundaries well-reasoned |
| Pitfalls | MEDIUM | Six critical pitfalls identified with prevention strategies; all have verified sources; RVshare API specifics remain LOW confidence due to sparse official documentation |

**Overall confidence:** MEDIUM-HIGH

The stack and architecture decisions are solid. The main uncertainty is operational: RVshare data access is unverified, and the resort PDF form type (AcroForm vs. XFA) is unknown until the actual form is examined. Both are discoverable early in Phase 1/Phase 3 and should be validated before those phases lock in.

### Gaps to Address

- **RVshare data access:** No documented CSV export or booking API found. Verify by logging into the actual host dashboard before designing the RVshare ingestion path. Budget for manual entry fallback in v1 — design the manual entry UI as a first-class feature, not an afterthought.
- **Resort PDF form type:** Verify whether the Sun Retreats form is AcroForm (pypdf works) or XFA/LiveCycle (requires HTML-to-PDF or conversion). This binary decision gates Phase 3 implementation approach.
- **Airbnb fee model:** The host-only fee transition (October 2025) changes the gross-to-net calculation. Confirm which fee model applies to this account before finalizing the accounting engine's fee attribution logic.
- **Mercury API vs. CSV:** Mercury has a proper REST API (`mercury.com/api`). Evaluate whether API polling is simpler than CSV export workflows — it may reduce manual steps for the most frequent import. Decide before building the Mercury adapter.
- **Ollama model selection:** Qwen2.5-Coder 14B (50% accuracy on easy SQL, 16GB VRAM with 4-bit quantization) vs. Devstral 24B (54% accuracy, more VRAM). Actual hardware constraints will determine feasibility. Benchmark before Phase 5.

---

## Sources

### Primary (HIGH confidence)
- FastAPI, SQLAlchemy, Pydantic, APScheduler, pypdf, polars — PyPI versions confirmed Feb 2026
- VRBO Payments Report columns — https://help.vrbo.com/articles/How-do-I-read-my-payments-report (official docs, fetched directly)
- IRS Publication 527 (2025) + Schedule E instructions — Schedule E category mapping
- Mercury API overview — https://mercury.com/api
- pypdf official docs — https://pypdf.readthedocs.io/en/stable/user/forms.html (NeedAppearances behavior)
- PyMuPDF / Artifex — https://artifex.com/blog/automating-pdf-form-filling-and-flattening-with-pymupdf

### Secondary (MEDIUM confidence)
- Airbnb CSV export columns — multiple community sources consistent with Airbnb help docs
- Airbnb iCal limitations — Uplisting, OwnerRez corroborating sources (2019 guest data removal)
- Airbnb scheduled messaging — community + third-party sources consistent
- Airbnb payout timing changes (BNPL, host-only fee Oct 2025) — Rental Scale-Up, Jenny Rutherford
- VRBO messaging API unavailability — Hospitable, OwnerRez support articles
- Text-to-SQL Ollama benchmarks — nilenso blog, May 2025 (single source but verifiable methodology)
- APScheduler vs. Celery — leapcell.io comparison (MEDIUM — corroborates community consensus)
- Mercury bank CSV export — secondary sources consistent (official URL 403-blocked)
- LLM arithmetic hallucination in financial contexts — BizTech, MATLAB Blog

### Tertiary (LOW confidence)
- RVshare data access — RVshare Owner Toolkit pages; iCal sync confirmed, CSV export not documented; no public API docs found. Requires verification against actual host dashboard.

---

*Research completed: 2026-02-26*
*Ready for roadmap: yes*

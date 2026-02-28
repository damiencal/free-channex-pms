# Requirements: Rental Management Suite

**Defined:** 2026-02-26
**Core Value:** Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration.

## v1 Requirements

### Data Ingestion

- [x] **INGS-01**: System can import Airbnb earnings/transaction CSV exports with schema validation
- [x] **INGS-02**: System can import VRBO reservation/financial CSV exports with schema validation
- [x] **INGS-03**: System supports manual entry of RVshare bookings and financials
- [x] **INGS-04**: System can import Mercury bank transaction CSV exports with schema validation
- [x] **INGS-05**: System validates CSV column headers and data types on every import
- [x] **INGS-06**: System archives raw CSV files before processing for audit trail
- [x] **INGS-07**: System normalizes all platform data into a unified booking and transaction schema

### Accounting

- [x] **ACCT-01**: System maintains a double-entry bookkeeping ledger with journal entries (debits/credits)
- [x] **ACCT-02**: System generates profit & loss statements per property and combined
- [x] **ACCT-03**: System generates balance sheets showing assets, liabilities, and equity
- [x] **ACCT-04**: System generates income statements with revenue and expense breakdown by period
- [x] **ACCT-05**: System tracks revenue from multiple sources (Airbnb, VRBO, RVshare) per property
- [x] **ACCT-06**: System tracks expenses across categories (rent, utilities, maintenance, supplies, etc.)
- [x] **ACCT-07**: System tracks loans with principal and interest components
- [x] **ACCT-08**: System reconciles platform payouts against bank deposits
- [x] **ACCT-09**: System handles multi-row Airbnb payout events (booking, payout, adjustments)

### Resort Compliance

- [x] **COMP-01**: System auto-fills a configurable PDF booking form from booking data and config
- [x] **COMP-02**: System maps unit names to site numbers via configuration (e.g., Jay→110, Minnie→170)
- [x] **COMP-03**: System attaches the platform booking confirmation to the completed form
- [x] **COMP-04**: System emails the completed form + confirmation to a configurable resort contact
- [x] **COMP-05**: System tracks submission status per booking (pending, submitted, confirmed)
- [x] **COMP-06**: System flags bookings approaching the 3-day pre-arrival submission deadline
- [x] **COMP-07**: System pre-populates host information from config (not hardcoded)

### Guest Communication

- [ ] **COMM-01**: System sends a welcome message via platform messaging upon booking confirmation
- [ ] **COMM-02**: System sends an arrival message via platform messaging 2-3 days before check-in
- [ ] **COMM-03**: Arrival message includes property details and lock codes from config
- [ ] **COMM-04**: System uses Airbnb's native scheduled messaging triggers where available
- [ ] **COMM-05**: System composes VRBO messages for manual sending (no API available)
- [ ] **COMM-06**: Message templates are user-editable and stored in configuration files
- [ ] **COMM-07**: Templates support variable substitution (guest name, dates, property name, lock code, etc.)

### Dashboard & Reporting

- [ ] **DASH-01**: Web dashboard shows key financial metrics (revenue, expenses, profit) at a glance
- [ ] **DASH-02**: Dashboard shows occupancy rates and booking trends per property
- [ ] **DASH-03**: Dashboard includes a calendar view of upcoming and past bookings across properties
- [ ] **DASH-04**: User can ask financial questions in plain English via Ollama-powered interface
- [ ] **DASH-05**: LLM interface generates SQL queries (never performs arithmetic directly)
- [ ] **DASH-06**: LLM interface shows generated SQL for transparency and debugging
- [ ] **DASH-07**: Dashboard is accessible to non-technical users (simple, clean interface)
- [x] **DASH-08**: User can view and categorize bank transactions (rent, utilities, maintenance, etc.)

### Infrastructure

- [x] **INFR-01**: Entire system deploys via single `docker-compose up` command
- [x] **INFR-02**: All property-specific data lives in configuration files (YAML/JSON), not code
- [x] **INFR-03**: System connects to local Ollama instance (no external LLM API calls)
- [x] **INFR-04**: Email templates are stored in config and editable without code changes
- [x] **INFR-05**: PDF form field mappings are configurable (not hardcoded to one form layout)
- [x] **INFR-06**: System persists all data in a local database with volume-mounted storage

## v2 Requirements

### Extended Reporting

- **RPTX-01**: System generates IRS Schedule E-compatible reports for tax filing
- **RPTX-02**: System tracks depreciation of rental property assets
- **RPTX-03**: System exports financial data in standard formats (QBO, CSV)

### Platform Integration

- **PLAT-01**: System integrates with Mercury Bank REST API (replace CSV import)
- **PLAT-02**: System integrates with VRBO messaging via partner API when available
- **PLAT-03**: System supports RVshare CSV import if export format becomes available

### Advanced Automation

- **AUTO-01**: System supports dynamic guest-specific lock codes
- **AUTO-02**: System auto-detects new bookings via email parsing or iCal polling
- **AUTO-03**: System sends automated payment reminders or follow-up messages

## Out of Scope

| Feature | Reason |
|---------|--------|
| Direct booking / own website | Relies entirely on third-party platforms |
| Mobile native app | Web dashboard accessible from any device |
| Multi-user role-based access control | Two users only (owner + spouse) |
| Real-time webhook integrations | No platform API access for small hosts; batch/polling sufficient |
| RVshare automated import | No documented export format; manual entry for v1 |
| VRBO programmatic messaging | No public API for non-partner hosts |
| Cloud hosting / SaaS deployment | Self-hosted by design |
| Property listing management | Listings managed on platforms directly |
| Guest review management | Reviews handled on platforms directly |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFR-01 | Phase 1 | Complete |
| INFR-02 | Phase 1 | Complete |
| INFR-03 | Phase 1 | Complete |
| INFR-04 | Phase 1 | Complete |
| INFR-05 | Phase 1 | Complete |
| INFR-06 | Phase 1 | Complete |
| INGS-01 | Phase 2 | Complete |
| INGS-02 | Phase 2 | Complete |
| INGS-03 | Phase 2 | Complete |
| INGS-04 | Phase 2 | Complete |
| INGS-05 | Phase 2 | Complete |
| INGS-06 | Phase 2 | Complete |
| INGS-07 | Phase 2 | Complete |
| ACCT-01 | Phase 3 | Complete |
| ACCT-05 | Phase 3 | Complete |
| ACCT-06 | Phase 3 | Complete |
| ACCT-07 | Phase 3 | Complete |
| ACCT-08 | Phase 3 | Complete |
| ACCT-09 | Phase 3 | Complete |
| ACCT-02 | Phase 4 | Complete |
| ACCT-03 | Phase 4 | Complete |
| ACCT-04 | Phase 4 | Complete |
| DASH-08 | Phase 4 | Complete |
| COMP-01 | Phase 5 | Complete |
| COMP-02 | Phase 5 | Complete |
| COMP-03 | Phase 5 | Complete |
| COMP-04 | Phase 5 | Complete |
| COMP-05 | Phase 5 | Complete |
| COMP-06 | Phase 5 | Complete |
| COMP-07 | Phase 5 | Complete |
| COMM-01 | Phase 6 | Pending |
| COMM-02 | Phase 6 | Pending |
| COMM-03 | Phase 6 | Pending |
| COMM-04 | Phase 6 | Pending |
| COMM-05 | Phase 6 | Pending |
| COMM-06 | Phase 6 | Pending |
| COMM-07 | Phase 6 | Pending |
| DASH-01 | Phase 7 | Pending |
| DASH-02 | Phase 7 | Pending |
| DASH-03 | Phase 7 | Pending |
| DASH-07 | Phase 7 | Pending |
| DASH-04 | Phase 8 | Pending |
| DASH-05 | Phase 8 | Pending |
| DASH-06 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 44 total
- Mapped to phases: 44
- Unmapped: 0

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-28 after Phase 5 completion — COMP-01 through COMP-07 marked Complete*

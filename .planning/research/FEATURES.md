# Feature Research

**Domain:** Self-hosted vacation rental management suite (accounting, compliance, guest communication)
**Researched:** 2026-02-26
**Confidence:** MEDIUM — Platform export formats verified via official VRBO docs and community sources; Airbnb columns partially verified via secondary sources; RVshare export capabilities LOW confidence (no public API docs found)

---

## Platform Data Access: What's Actually Available

This section documents what each platform actually exports before mapping to features, since feature design depends on what data is accessible.

### Airbnb

**Export types (MEDIUM confidence — multiple community sources consistent with Airbnb help docs):**

- **Transaction History CSV** — Available via Hosting dashboard > Transaction History > Gross Earnings tab > Download CSV
  - Columns include: Date, Type, Confirmation Code, Guest Name, Nights, Amount, Paid Out, Host Service Fee, Cleaning Fee, Taxes Withheld, Payout details
  - Two variants: "Completed Payouts" (per-listing) and "Gross Earnings" (all listings)
  - Manual download required; no webhook or API push
- **Reservations CSV** — Available via Hosting dashboard > Reservations > Export
  - Contains guest names, email addresses, phone numbers, check-in/check-out dates, pricing details
- **iCal feed** — Available at `https://www.airbnb.com/calendar/ical/{id}.ics`
  - Contains: blocked dates only, last 4 digits of guest phone number
  - Does NOT include: guest name, email, price, full contact information
  - Updates: 30 minutes to several hours lag; only pushes 365 days forward

**Native messaging:**
- Scheduled Quick Replies — natively supported with three triggers:
  - Booking confirmed
  - Check-in (up to 14 days before or after)
  - Checkout (up to 14 days before or after)
- Shortcodes available: guest name, check-in date, listing address, house rules, and other listing fields
- API access: Restricted to approved partners only; not available to individual hosts; Airbnb is not accepting new API partner requests as of 2025

### VRBO

**Export types (HIGH confidence — fetched from official VRBO help documentation):**

- **Payments Report CSV** — Available via Reservation Manager > Financial Reporting > Download
  - Confirmed columns: RefID, Payout ID, Reservation ID, Check In, Check Out, Number of Nights, Source, Subscription Model, Payment Date, Disbursement Date, Payment Type, Property ID, Guest Name, Payment Method, Taxable Revenue, Non-Taxable Revenue, Guest Payment, Your Revenue, Payable To You, Tax, Service Fee, Currency, Commission, VAT on Commission, Payment Processing Fee, Deposit Amount, Stay Tax We Remit, Stay Tax You Remit, Refundable Deposit, Payout
  - Date range selectable; report can be exported as CSV/XLS/PDF
- **Payout Summary Report** — Separate from payments report; overview of received funds after fees
- **iCal calendar export** — For calendar synchronization only; blocked dates

**Native messaging:**
- VRBO does NOT have automated scheduled messaging natively (confirmed by multiple sources)
- VRBO sends a static Welcome Guide email 7 days before check-in automatically
- VRBO messaging API integration is in public beta via partners like OwnerRez and Uplisting
- Direct API access requires contacting Expedia Group (pmsalesinquiry@expediagroup.com); not self-service
- Practical implication: messaging through VRBO requires either a channel manager integration or manual action

### RVshare

**Export types (LOW confidence — no public API documentation found; only Owner Toolkit marketing pages accessible):**

- **iCal calendar sync** — Confirmed supported; syncs blocked dates to prevent double bookings
- **Reservation data** — Viewable in dashboard with dates, pricing, optional fees; no CSV export documented
- **Financial/payment data** — Accessible per-reservation via Payments tab; no bulk export documented
- **Performance metrics** — Dashboard shows Response Time, Response Rate, Acceptance Rate, Cancellation Rate, Expiration Rate; PDF download available for these metrics only

**Native messaging:**
- No automated messaging system documented in Owner Toolkit
- RVshare focuses on RV rentals; messaging appears manual
- No API access documented for third-party integration

**RVshare practical finding:** RVshare has the most limited data export and automation capabilities of the three platforms. Financial data extraction will likely require manual data entry or screen scraping unless official exports are found in the actual host dashboard.

### Mercury Bank

**Export types (MEDIUM confidence — official support page confirmed but 403 blocked; secondary sources consistent):**

- **Transaction CSV exports** — Multiple formats:
  - Standard CSV
  - QuickBooks-formatted CSV
  - NetSuite-formatted CSV
- **Statement PDFs** — Monthly statements available
- **Integration**: Mercury has direct QuickBooks integration for bank feed syncing

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that must work for the product to feel functional. Missing any of these means the product doesn't deliver its stated value.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Import Airbnb transaction CSV | Core accounting input; Airbnb is primary revenue source | LOW | CSV format is stable and documented; manual download required |
| Import VRBO payments report CSV | Core accounting input; VRBO has richest export of the three | LOW | 29 confirmed columns; manual download required |
| Import Mercury bank CSV | Expense tracking requires bank data | LOW | Multiple format options; QuickBooks CSV most structured |
| Unified transaction ledger | All income/expenses in one place | MEDIUM | Must de-duplicate and reconcile across sources |
| Per-property P&L statement | Owner needs to know each unit's performance separately | MEDIUM | Schedule E requires per-property tracking |
| Monthly/annual income statement | Standard financial report | LOW | Aggregates the ledger |
| Balance sheet | Assets, liabilities, equity snapshot | MEDIUM | Requires tracking loan balances, depreciation |
| Expense categorization aligned with Schedule E | IRS tax preparation requirement | MEDIUM | 15 Schedule E categories; repair vs improvement distinction is critical |
| Dashboard with key metrics | Quick daily/weekly situational awareness | MEDIUM | Occupancy rate, YTD revenue, YTD expenses, net income |
| Auto-fill resort PDF booking form | Defined project requirement; 3-day advance deadline means manual is failure-prone | HIGH | PDF field mapping is config-driven; requires `pypdf2` or `pdfplumber` + form field detection |
| Email completed resort form | Compliance requires submission to resort Welcome Center | LOW | Triggered automation after PDF fill |
| Send booking confirmation message | Guest expects acknowledgment; Airbnb natively supports this | LOW | Airbnb: native shortcodes; VRBO/RVshare: platform API or manual |
| Send pre-arrival message 2-3 days before check-in | Standard guest communication practice; reduces day-of questions | LOW | Airbnb: native scheduling; VRBO: beta API integration; RVshare: no native support |
| Message template storage in config files | Open-source requirement; personal data must not be in code | LOW | YAML/JSON template files with variable interpolation |
| Docker container deployment | Defined project requirement | MEDIUM | docker-compose with service dependencies |

### Differentiators (Competitive Advantage)

Features that go beyond typical tools and create real value for this specific use case. These are the reasons to build a custom system rather than use a SaaS product.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Natural language financial queries via Ollama | Kim can ask "how much did Jay make this month?" without knowing SQL or spreadsheets | HIGH | Text-to-SQL pipeline; Devstral 24B or Qwen2.5-Coder 14B recommended; 50-54% accuracy on easy tasks; requires schema injection into prompt |
| Cross-platform revenue reconciliation | Single view of income across Airbnb + VRBO + RVshare + Mercury | MEDIUM | Matching reservation IDs to bank transactions; identifying platform fee deductions |
| Automated resort compliance workflow | Eliminates manual PDF fill + email before every booking; prevents compliance failures | HIGH | PDF form field detection varies; config-driven field mapping; triggered by booking detection |
| Config-driven multi-property setup | Open-source deployable by any rental owner, not just this one | LOW | All property specifics (unit names, contacts, lock codes, form paths) in YAML/JSON |
| Booking auto-detection from CSV polling | Zero-touch from booking to accounting entry | MEDIUM | Hash or ID comparison between last-seen exports; scheduled polling rather than webhooks |
| Per-platform expense attribution | Track Airbnb service fees vs VRBO commissions vs cleaning costs per unit | MEDIUM | Enables true net revenue per platform per unit |
| Occupancy calendar heatmap | Visual density of bookings across units and platforms | LOW | Simple date visualization; high value for planning |
| Schedule E expense report generation | Tax time: one-click export of all expenses in IRS Schedule E format | MEDIUM | Maps existing expense categories to form lines; saves accountant hours |
| Depreciation tracking | 27.5-year residential depreciation; automatically calculated | MEDIUM | Set once per property; calculated automatically each reporting period |

### Anti-Features (Commonly Requested, Often Problematic)

Features to explicitly not build. These create complexity without proportionate value for this use case.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time platform sync via webhooks | Instant booking notifications feel important | Airbnb API is partner-only; VRBO is beta; RVshare has no API. Building webhook infrastructure for platforms that don't support it is a rabbit hole. | Polling: check for new exports every hour or on demand. Latency is acceptable — resort form needs 3 days notice. |
| Dynamic lock code generation per guest | Security enhancement; personalized per stay | Defined out of scope for v1. Requires smart lock hardware integration and per-platform integration per lock manufacturer. Major complexity for marginal security gain at a resort property. | Static lock codes in config; change between seasons manually |
| Direct booking website | Eliminate platform fees | Requires payment processing, trust & safety, marketing — a separate full product. Competes with Airbnb for discoverability. | Continue using platforms; track net revenue after fees |
| Multi-user role-based access control | Seems like good practice | Two users who both have admin needs. No strangers accessing this system. RBAC adds auth complexity for zero practical benefit. | Single shared login; run on local network only |
| Mobile native app | Convenient for on-the-go access | Web dashboard works on mobile browsers. Building and maintaining a native app doubles the UI surface area. | Responsive web dashboard |
| Automatic price optimization / dynamic pricing | Maximize revenue per night | Requires market data feeds (AirDNA, PriceLabs), competitor pricing APIs, and ML models. A separate product entirely. | Set seasonal rates manually in each platform |
| Multi-property portfolio management for 10+ units | Future growth path | This system is designed for 2 units at one resort. Generalization to large portfolios changes architectural assumptions. | Build for 2 units; document how to extend via config for 3-5 units max |
| Tenant long-term lease management | Landlord software often includes this | Sun Retreats Fort Myers Beach is vacation rental only; no long-term tenants. Adds irrelevant complexity. | Keep scope to short-term vacation rentals |
| In-app review response management | Guest reviews need responses | Nice-to-have, but review response is not time-critical, not compliance-related, and requires per-platform API access. | Handle reviews directly in each platform |
| AI-generated message personalization | More personalized guest communication | For 2 units, template messages with variable substitution are already highly personalized. LLM-written messages are harder to audit and could produce off-brand content. | Editable templates with shortcodes for guest name, dates, property details |

---

## Feature Dependencies

```
[Mercury CSV Import]
    └──feeds──> [Unified Transaction Ledger]

[Airbnb CSV Import]
    └──feeds──> [Unified Transaction Ledger]
               └──powers──> [P&L Statement]
                            └──powers──> [Dashboard Metrics]
                            └──powers──> [Schedule E Report]
                            └──powers──> [Natural Language Query]

[VRBO CSV Import]
    └──feeds──> [Unified Transaction Ledger]

[RVshare Manual Entry OR CSV Import (if found)]
    └──feeds──> [Unified Transaction Ledger]

[Booking Detection] (polling CSV for new reservations)
    └──triggers──> [Auto-fill Resort PDF]
                   └──triggers──> [Email PDF to Resort]
    └──triggers──> [Send Booking Confirmation Message]
    └──schedules──> [Pre-Arrival Message] (2-3 days before check-in)

[Config Files] (property data, templates, form mappings)
    └──required by──> [Auto-fill Resort PDF]
    └──required by──> [Send Booking Confirmation Message]
    └──required by──> [Pre-Arrival Message]
    └──required by──> [All Per-Property Reporting]

[Unified Transaction Ledger]
    └──required by──> [Balance Sheet]
    └──required by──> [Natural Language Query]
```

### Dependency Notes

- **Booking Detection requires Airbnb/VRBO CSV Import:** New reservation detection depends on comparing previously-seen export against current export, or polling a calendar feed. iCal provides dates only (not financial data); full CSV must be downloaded for accounting. These workflows need separate polling intervals.
- **Natural Language Query requires Unified Transaction Ledger:** The Ollama text-to-SQL interface needs a stable, queryable schema. The ledger schema must be finalized before the LLM query interface can be built.
- **Resort PDF AutoFill requires Config Files:** The form field mapping (which PDF form field = which booking data field) must be config-driven. This means the config schema must be defined before the PDF automation is built.
- **Pre-Arrival Message requires Booking Detection:** Messages cannot be scheduled without knowing the check-in date. The booking record must exist in the local database before the scheduler can queue the message.
- **VRBO Messaging is a Platform Constraint:** VRBO does not support native scheduled messaging and has no self-service API. Sending through VRBO messaging requires either manual action or a channel manager integration. This is a dependency on a third-party service (OwnerRez, Uplisting) OR on VRBO's beta API partnership program. For v1, consider fallback: send guest email directly if platform messaging unavailable.
- **RVshare Data Access is Unverified:** RVshare has no documented CSV export or financial API. The project must assume manual data entry for RVshare reservations until verified otherwise by logging into the actual host dashboard. This blocks automated booking detection for RVshare.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to deliver the core value ("automated end-to-end rental operations with zero manual intervention after initial configuration").

- [ ] **Airbnb CSV import pipeline** — Parse and normalize transaction CSV into unified ledger; required for accounting and booking detection
- [ ] **VRBO CSV import pipeline** — Parse payments report CSV into unified ledger
- [ ] **Mercury CSV import pipeline** — Parse bank transactions into unified ledger as expense entries
- [ ] **Unified transaction ledger** — SQLite or Postgres schema that holds all transactions with property, platform, and category attribution
- [ ] **P&L statement per property** — Monthly and YTD; the most-needed financial report
- [ ] **Dashboard with key metrics** — Occupancy rate, YTD revenue, YTD expenses, pending bookings
- [ ] **Resort PDF auto-fill** — Config-driven field mapping; triggered by new booking detection
- [ ] **Email resort form** — Send filled PDF to resort contact on booking detection
- [ ] **Booking confirmation message** — Send via Airbnb native messaging (other platforms: manual fallback for v1)
- [ ] **Pre-arrival message** — Scheduled send 2-3 days before check-in via Airbnb; manual fallback for VRBO/RVshare
- [ ] **Config-driven templates and property data** — YAML/JSON config; no hardcoded property data in code
- [ ] **Docker deployment** — docker-compose with all services

### Add After Validation (v1.x)

- [ ] **Natural language query interface** — Ollama text-to-SQL; add once ledger schema is stable; Kim's primary use case but can be delivered after core accounting works
- [ ] **Schedule E expense report** — Tax export; add before first tax season after launch
- [ ] **Balance sheet** — Add once depreciation tracking is scoped; requires loan balance setup
- [ ] **VRBO messaging integration** — Via OwnerRez/Uplisting API or VRBO beta API; add once v1 messaging via fallback is validated
- [ ] **Depreciation tracking** — Property value + 27.5-year schedule; needed for accurate P&L

### Future Consideration (v2+)

- [ ] **RVshare automated booking detection** — Blocked on verifying whether RVshare has a usable export or API; manual entry acceptable for v1 given RVshare likely lower booking volume
- [ ] **Income statement / annual financial report** — More formal than P&L; needed for lending or CPA review
- [ ] **Occupancy heatmap calendar** — Visual; nice to have once core data is working
- [ ] **Per-platform expense attribution report** — Useful insight but not blocking operations
- [ ] **Cross-platform booking revenue reconciliation** — Matching platform deposits to Mercury transactions; reduces manual bookkeeping

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Airbnb CSV import | HIGH | LOW | P1 |
| VRBO CSV import | HIGH | LOW | P1 |
| Mercury CSV import | HIGH | LOW | P1 |
| Unified transaction ledger | HIGH | MEDIUM | P1 |
| P&L statement per property | HIGH | LOW | P1 |
| Resort PDF auto-fill | HIGH | HIGH | P1 |
| Email resort form | HIGH | LOW | P1 |
| Booking confirmation message (Airbnb) | HIGH | LOW | P1 |
| Pre-arrival message (Airbnb) | HIGH | LOW | P1 |
| Config-driven templates | HIGH | LOW | P1 |
| Docker deployment | HIGH | MEDIUM | P1 |
| Dashboard with key metrics | HIGH | MEDIUM | P1 |
| Natural language query (Ollama) | HIGH | HIGH | P2 |
| Schedule E expense report | MEDIUM | MEDIUM | P2 |
| Balance sheet | MEDIUM | MEDIUM | P2 |
| VRBO messaging integration | MEDIUM | HIGH | P2 |
| Depreciation tracking | MEDIUM | MEDIUM | P2 |
| RVshare data integration | MEDIUM | HIGH | P3 |
| Occupancy heatmap | LOW | LOW | P3 |
| Per-platform revenue attribution | MEDIUM | MEDIUM | P3 |
| Cross-platform reconciliation | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch — delivers the core value proposition
- P2: Should have — add within first month post-launch
- P3: Nice to have — add when core is stable

---

## Competitor Feature Analysis

These are SaaS platforms doing similar things. We are NOT building a competitor — we are building a simpler, self-hosted, config-driven tool for a specific 2-unit use case.

| Feature | Hostaway/Hospitable | OwnerRez | Our Approach |
|---------|---------------------|----------|--------------|
| Channel management | Full sync via official APIs | Full sync via official APIs | CSV import only (API access unavailable without partner status) |
| Guest messaging | Unified inbox, all platforms, AI-assisted | All platforms via API | Airbnb native + fallback for VRBO/RVshare |
| Accounting | Basic; integrates with QuickBooks | Built-in trust accounting | Full built-in P&L; no QuickBooks dependency |
| Resort/HOA compliance | Not applicable (general tool) | Not applicable | Specific PDF form automation — our differentiation |
| Natural language queries | Not available | Not available | Ollama text-to-SQL — our differentiation |
| Self-hosted | No — cloud SaaS only | No — cloud SaaS only | Yes — Docker, local network |
| Open source | No | No | Yes |
| Pricing | $100-500+/month | $40-100+/month | Free (self-hosted) |

---

## Platform Messaging Constraints Summary

This deserves its own section because it shapes implementation significantly.

| Platform | Native Scheduled Messaging | API Access | v1 Approach |
|----------|---------------------------|------------|-------------|
| Airbnb | Yes — 3 triggers, shortcodes, native | Partner-only (unavailable) | Use native Airbnb scheduled quick replies via web automation or manual setup |
| VRBO | No — only a static Welcome Guide 7 days pre-check-in | Beta via partners (OwnerRez, Uplisting) | Manual fallback for v1; evaluate OwnerRez/Uplisting integration for v1.x |
| RVshare | No documentation found | No documented API | Manual fallback for v1; investigate actual dashboard |

**Key architectural implication:** For v1, "automated messaging" for VRBO and RVshare means the system prepares a message and alerts the operator to send it manually, not a true fire-and-forget automation. Airbnb is the only platform where genuine automation is accessible to a self-hosted tool.

An alternative for VRBO/RVshare: Use platform's own email (guest's email is in the reservation export) to send messages directly. This bypasses the platform messaging system but ensures the guest receives the information. This approach should be config-selectable since it trades platform-mediated communication for reliability.

---

## Airbnb Scheduled Messaging — Native Trigger Reference

(MEDIUM confidence — multiple community and third-party sources consistent; official help page rendered JS only)

Airbnb natively supports scheduled quick replies with:

**Triggers:**
- Booking Confirmed
- Check-in (14 days before to 14 days after, any time of day)
- Checkout (14 days before to 14 days after, any time of day)

**Shortcodes available:**
- Guest name
- Check-in date
- Check-out date
- Listing address / city
- House rules
- Listing-specific details (WiFi, check-in instructions, etc.)

**Practical note:** Shortcodes require the corresponding listing fields to be populated in Airbnb. If a field is empty, the shortcode renders as "unavailable" in the sent message.

---

## Schedule E Expense Categories Reference

(HIGH confidence — verified against IRS Publication 527 and IRS Schedule E instructions 2025)

Rental property expenses must map to these 15 Schedule E categories:

1. Advertising (platform listing fees count here)
2. Auto and travel (mileage to properties at $0.70/mile for 2025)
3. Cleaning and maintenance
4. Commissions (platform service fees)
5. Insurance
6. Legal and professional fees
7. Management fees
8. Mortgage interest (interest only, not principal)
9. Other interest
10. Repairs (maintaining current condition — no added value)
11. Supplies
12. Taxes (property taxes, occupancy taxes, licensing)
13. Utilities
14. Depreciation (27.5-year residential schedule)
15. Other (HOA fees, miscellaneous)

**Critical distinction:** Repairs are deductible immediately. Capital improvements (roof replacement, major renovations) must be capitalized and depreciated over 27.5 years. The system must support flagging transactions as either repair or capital improvement during categorization.

---

## Natural Language Query — Implementation Reality

(MEDIUM confidence — based on verified benchmarks from nilenso blog, May 2025)

The Ollama text-to-SQL approach for Kim's "ask questions in plain English" use case:

**What works:**
- Simple queries: "How much did Jay earn in January?" — high accuracy on well-structured schemas
- Aggregation queries: "What's the total in cleaning fees this year?" — reliable for common SQL patterns
- Comparative queries: "Which unit made more money last month?" — manageable complexity

**What doesn't work reliably:**
- Multi-table joins with ambiguous naming
- Complex date arithmetic
- Queries requiring knowledge of business logic not in schema

**Model recommendations for this use case:**
- Qwen2.5-Coder 14B: Best speed-to-performance ratio; works on 16GB VRAM with 4-bit quantization; 50% accuracy on easy tasks
- Devstral 24B: Highest accuracy (54%); requires more VRAM; consider if accuracy is more important than speed
- Avoid models smaller than 7B for SQL generation — unreliable output

**Architectural requirements:**
- Schema must be injected into every LLM prompt (few-shot context)
- Schema design matters enormously — table and column names should be human-readable business terms
- Error recovery: LLM generates SQL, system executes, if error occurs, resend with error context for one retry
- Result formatting: LLM converts raw SQL results back to natural language answer

**Practical expectation:** Works well for Kim's actual needs (financial questions, occupancy questions). Will fail on unusual or complex queries. Design the interface to show the generated SQL so Thomas can debug when it fails.

---

## Sources

- VRBO Payments Report columns: https://help.vrbo.com/articles/How-do-I-read-my-payments-report (fetched directly — HIGH confidence)
- Airbnb export columns: Multiple community sources and county government instructions (MEDIUM — consistent but indirect)
- Airbnb iCal limitations: https://www.ownerrez.com/support/articles/channel-management-calendar-import-export-airbnb and multiple corroborating sources (MEDIUM confidence)
- Airbnb scheduled messaging: https://www.airbnb.com/help/article/2897 and community corroboration (MEDIUM — official URL but JS-only render)
- VRBO messaging limitations: https://zeevou.com/blog/does-vrbo-use-automated-messaging/ and https://www.ownerrez.com/forums/requests/vrbo-native-messaging (MEDIUM — multiple sources agree)
- RVshare Owner Toolkit: https://owner-toolkit.rvshare.com/reservations/ and https://owner-toolkit.rvshare.com/accurate-calendars/ (LOW — only iCal sync confirmed; no export documented)
- Mercury bank export: https://support.mercury.com/hc/en-us/articles/28768700685844-Exporting-transaction-data (MEDIUM — 403 blocked but secondary sources consistent)
- Schedule E categories: IRS Publication 527 (2025), https://www.landlordstudio.com/blog/schedule-e-categories (HIGH — IRS authoritative)
- Text-to-SQL Ollama benchmarks: https://blog.nilenso.com/blog/2025/05/27/experimenting-with-self-hosted-llms-for-text-to-sql/ (MEDIUM — single source but verifiable)
- Vacation rental software features checklist: https://www.escapia.com/resources/articles/vacation-rental-property-management-software-shopping-checklist/ (MEDIUM — industry source)
- Rental property accounting: https://madrasaccountancy.com/blog-posts/rental-property-accounting-complete-guide-for-landlords-in-2025 (MEDIUM)

---
*Feature research for: Self-hosted vacation rental management suite*
*Researched: 2026-02-26*

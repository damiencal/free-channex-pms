# Phase 4: Financial Reports - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate financial reports (P&L, balance sheet, income statement) from the double-entry ledger built in Phase 3, and allow bank transactions to be categorized with category assignments automatically creating journal/expense entries. Reports are served via API endpoints; the dashboard (Phase 7) will consume them. Creating new data or modifying the accounting engine is out of scope.

</domain>

<decisions>
## Implementation Decisions

### Report granularity
- P&L revenue broken down by platform + month (Airbnb/VRBO/RVshare subtotals, each with monthly rows)
- Expenses shown as category totals only (one line per category — no per-transaction drill-down)
- Balance sheet is a period-end snapshot, not current balances — caller passes an as-of date
- P&L and income statement are the same underlying data, different framing: P&L = per-property with platform/month breakdown; income statement = combined totals for tax/accounting purposes

### Date range & periods
- All reports support: specific month, quarter, YTD, calendar year, and fully flexible start_date/end_date
- Calendar year only (Jan–Dec); no fiscal year offset needed
- Reports return current period data only — no prior-period comparison columns
- Income statement supports `?breakdown=monthly` parameter to return month-by-month rows within the date range; default is totals for the full range

### Transaction categorization
- Available categories: the 12 Schedule E categories (rent, utilities, maintenance, supplies, etc.) plus non-expense categories for non-P&L transactions (owner deposit, loan payment, transfer, etc.)
- Two endpoints: single update (PATCH /bank-transactions/{id}/category) and bulk assignment (PATCH /bank-transactions/categorize with list of {id, category} pairs)
- No auto-suggest — manual categorization only
- Categorizing a bank transaction auto-creates a corresponding expense journal entry so the transaction appears in P&L reports without a separate manual step

### Multi-property aggregation
- Combined report structure available via `?breakdown=property` parameter — returns per-property columns (Jay, Minnie, …) plus a combined total column; default is combined totals only
- Shared expenses (property_id = None) split evenly across all active properties (N properties, not hardcoded 50/50) — designed to scale beyond 2 properties
- Property-specific loans (e.g., RV loan on Jay) attributed to that property only; working capital loans (no property_id) are split evenly
- Per-property P&L includes that property's allocated share of shared expenses to reflect true per-property profitability
- Balance sheet is combined-only — no per-property balance sheet breakdown

### Claude's Discretion
- Exact JSON response shape for each report endpoint
- How "quarter" is parameterized (e.g., `?quarter=Q1&year=2026` vs `?start=2026-01-01&end=2026-03-31`)
- How to handle partial months at period boundaries
- Whether P&L and income statement are one endpoint with a `type` parameter or two separate endpoints

</decisions>

<specifics>
## Specific Ideas

- The system currently has 2 properties (Jay and Minnie) but shared expense allocation should be based on total active property count — not hardcoded to 2
- Some loans are property-specific (RV loans) and others are shared (working capital loans) — the existing `property_id` nullable field on journal entries already captures this distinction

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-financial-reports*
*Context gathered: 2026-02-27*

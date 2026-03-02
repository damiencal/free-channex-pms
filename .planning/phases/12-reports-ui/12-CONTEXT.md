# Phase 12: Reports UI - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Interactive financial report viewers (P&L, balance sheet, income statement) in the existing dashboard, replacing the current Reports tab placeholder. Backend report generation already exists (Phase 4). This phase is purely frontend presentation with property and date filters.

</domain>

<decisions>
## Implementation Decisions

### Report layout & structure
- Card sections for each major report section (Revenue, Expenses, Assets, etc.) — visual breathing room, not dense spreadsheet
- Sections collapsible, expanded by default — user can collapse to focus
- Three reports navigated via sub-tabs within Reports tab: P&L | Balance Sheet | Income Statement — consistent with Finance tab pattern
- Print-friendly CSS (@media print) so browser Print produces clean output — no export button

### Filter controls & date selection
- Use global AppShell property selector + add "Combined" option if not already present — no per-report property dropdown
- Preset buttons (This Month, This Quarter, YTD, Last Year) plus custom date range picker for P&L and Income Statement
- Balance Sheet uses same preset buttons — shows end-of-period snapshot for selected preset
- "Generate" button required to fetch report — filters don't auto-fetch on change; prevents unnecessary requests during multi-filter adjustment

### Number formatting & visual cues
- Negative amount display: Claude's discretion (pick best for non-accountant readability)
- Totals/subtotals: background shading — subtotals get subtle tint, grand totals darker tint; modern feel
- Zero-balance line items: show with em-dash ("—") — consistent structure every report view
- P&L includes percentage column showing each line item as % of total revenue

### Monthly detail view
- Income Statement has "Totals" and "Monthly" as separate sub-views (not a toggle) — clearly separated navigation
- Monthly breakdown also available on P&L (same Totals/Monthly sub-view pattern)
- Monthly column overflow on small screens: Claude's discretion (horizontal scroll vs limit, based on responsive best practices)
- Monthly view always includes a Total column at the end — sum across displayed months for easy reference

### Claude's Discretion
- Negative amount formatting (parentheses vs minus sign, red styling)
- Monthly view responsive handling (horizontal scroll with pinned labels vs month limit)
- Loading/error state design
- Exact spacing, typography, and card styling
- Empty report state messaging
- Balance sheet section ordering

</decisions>

<specifics>
## Specific Ideas

- Sub-tab pattern should match Phase 11 Finance tab (Transactions | Expenses & Loans | Reconciliation) — consistent UI language
- Card sections like the dashboard stat cards — clean, modern, not cluttered
- "Generate" button pattern gives user explicit control — avoids surprise network requests when adjusting multiple filters

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-reports-ui*
*Context gathered: 2026-03-02*

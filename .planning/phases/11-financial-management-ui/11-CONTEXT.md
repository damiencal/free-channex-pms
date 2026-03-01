# Phase 11: Financial Management UI - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose four existing backend capabilities through the web dashboard: bank transaction categorization, expense recording, loan payment entry, and bank reconciliation management. All backend APIs exist from Phases 3-4. This phase builds the frontend UI only.

</domain>

<decisions>
## Implementation Decisions

### Transaction Categorization
- Compact table layout (dense rows like a bank statement) — date, description, amount, category column
- Checkboxes on each row for multi-select; toolbar appears at top when any are checked with select-all/clear-all and bulk category assignment
- Filters: category (including "uncategorized"), date range, and min/max amount
- Auto-save on category select — picking a category from dropdown immediately persists; brief inline confirmation (checkmark flash)

### Expense & Loan Entry
- Single form with type toggle (expense vs loan payment) — fields change based on type selection
- Inline success message + form reset after successful submit — supports batch entry sessions
- Loan selection via dropdown of active loans (e.g., "Mortgage - Jay - $X remaining"); user enters payment amount and P&I split
- Property attribution is a required field on expenses — every expense must be attributed to a property (jay, minnie) or marked "shared"

### Reconciliation Workflow
- Split panel layout — left side: platform payouts, right side: bank deposits; suggested matches highlighted with lines/colors between them
- All suggested matches (auto-matched by system) require user approval — nothing is reconciled until the user clicks Confirm
- "Needs review" deposits (multiple candidate bookings) show candidate list; user picks the correct booking and confirms
- Summary stats at top: X matched, Y needs review, Z unmatched, plus total unreconciled dollar amount

### Tab/Page Layout
- New top-level "Finance" tab in dashboard alongside Home, Calendar, Actions, Query
- Internal sub-tabs within Finance: Transactions | Expenses & Loans | Reconciliation
- Finance tab badge shows combined count of uncategorized transactions + unreconciled items
- Property selector filters Finance tab data, with explicit "All Properties" option for cross-property views (shared expenses, combined reconciliation)

### Claude's Discretion
- Exact table column widths and responsive breakpoints
- Empty state designs for each sub-tab
- Loading skeleton patterns
- Error state handling and retry UX
- Pagination vs infinite scroll for transaction list (choose based on data volume patterns)
- Mobile layout adaptations for split-panel reconciliation view

</decisions>

<specifics>
## Specific Ideas

- Auto-save on category select should match the fast, no-friction feel of the existing dashboard interactions
- Split-panel reconciliation is the most complex UI in this phase — suggested matches connected visually between the two panels
- Finance tab badge serves the same "pending work" purpose as the Actions tab badge — draws operator attention to unfinished financial tasks
- "All Properties" in the property selector is new behavior that other tabs don't have — needed because shared expenses and cross-property reconciliation are common workflows

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-financial-management-ui*
*Context gathered: 2026-03-01*

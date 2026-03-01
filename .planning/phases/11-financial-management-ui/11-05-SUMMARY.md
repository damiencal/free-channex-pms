---
phase: 11-financial-management-ui
plan: 05
subsystem: ui
tags: [react, typescript, tanstack-query, reconciliation, finance, tailwind]

# Dependency graph
requires:
  - phase: 11-01
    provides: backend reconciliation endpoints (fetchUnreconciled, runReconciliation, confirmMatch, rejectMatch) and UI primitives (ScrollArea)
  - phase: 11-02
    provides: useReconciliation hooks, FinanceTab shell with ReconciliationTab placeholder
provides:
  - MatchCandidateList component with client-side candidate derivation (amount + 7-day window)
  - ReconciliationPanel component (payouts or deposits panel with status-based highlighting)
  - Full ReconciliationTab replacing placeholder from Plan 02
affects: [11-summary, future finance phases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Status-based panel highlighting (amber=pending_confirmation, orange=needs_review)
    - Client-side candidate derivation mirroring server algorithm for needs-review deposits
    - Hover cross-highlight between matched pairs in split-panel layout
    - Collapsible candidate list for needs-review deposits using Radix Collapsible

key-files:
  created:
    - frontend/src/components/finance/MatchCandidateList.tsx
    - frontend/src/components/finance/ReconciliationPanel.tsx
  modified:
    - frontend/src/components/finance/ReconciliationTab.tsx

key-decisions:
  - "Client-side candidate derivation reproduces server algorithm: amount equality + 7-day check_in_date window — allows needs-review deposits to show candidates without a new API endpoint"
  - "ReconciliationPanel accepts typed PayoutPanelItem/DepositPanelItem arrays with _matchId/_isPending/_isNeedsReview discriminator fields — cleanly separates rendering logic per status"
  - "Hover cross-highlight uses hoveredMatchId state in ReconciliationTab, passed down to both panels — highlights counterpart item without duplicating state"
  - "Confirm/Reject buttons only on deposit side (right panel) — payout side shows amber highlight only; avoids double-confirm UX confusion"
  - "Deposit panel rendering order: pending_confirmation → needs_review → unmatched — operator sees actionable items first"

patterns-established:
  - "Split-panel layout: grid-cols-1 lg:grid-cols-2 for mobile-responsive stacking"
  - "Stat card grid: grid-cols-2 md:grid-cols-4 for summary statistics"
  - "Border-left color coding: border-amber-500 for pending, border-orange-500 for needs_review, border-transparent for unmatched"

# Metrics
duration: 4min
completed: 2026-03-01
---

# Phase 11 Plan 05: Reconciliation UI Summary

**Split-panel reconciliation interface with amber/orange status highlighting, hover cross-match, client-side candidate derivation for needs-review deposits, and confirm/reject actions**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-01T17:31:23Z
- **Completed:** 2026-03-01T17:35:30Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `MatchCandidateList` derives candidate bookings client-side (amount + 7-day window) from unmatched payouts — zero new API endpoints required
- `ReconciliationPanel` renders scrollable payout or deposit lists with status-based border-left color coding and hover cross-highlight ring
- `ReconciliationTab` replaces placeholder with full implementation: summary stats bar, Run Reconciliation button, split-panel layout, confirm/reject handlers, and empty/error/loading states

## Task Commits

1. **Task 1: Create MatchCandidateList and ReconciliationPanel** - `8b912fa` (feat)
2. **Task 2: Create ReconciliationTab with summary stats and split-panel layout** - `f19c977` (feat)

## Files Created/Modified

- `frontend/src/components/finance/MatchCandidateList.tsx` - Candidate booking list for needs-review deposits with client-side amount+date filtering
- `frontend/src/components/finance/ReconciliationPanel.tsx` - Generic left/right panel with payout rows, deposit rows (pending/needs-review/unmatched), Collapsible candidate expansion
- `frontend/src/components/finance/ReconciliationTab.tsx` - Full reconciliation sub-tab with summary stats, mutation handlers, split-panel layout, hover cross-highlight

## Decisions Made

- **Client-side candidate derivation:** `getCandidates()` in `MatchCandidateList` mirrors the server's MATCH_WINDOW_DAYS=7 algorithm — avoids a dedicated `/candidates/{deposit_id}` endpoint while keeping UX identical
- **Discriminator fields on panel items:** `_matchId`, `_isPending`, `_isNeedsReview` added at ReconciliationTab before passing to panels — lets panels render conditionally without prop explosion
- **Hover state in parent:** `hoveredMatchId` state lives in `ReconciliationTab` and is passed to both panels — single source of truth for cross-panel highlight without context or store
- **Confirm only on deposit side:** Avoids double-confirm confusion; payout side shows amber only as visual confirmation the pair exists

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Reconciliation sub-tab is complete and production-ready
- Phase 11 Plans 03-04 (TransactionsTab, ExpensesLoansTab) were noted as stubs in STATE.md — those are the remaining finance sub-tabs
- No blockers or concerns

---
*Phase: 11-financial-management-ui*
*Completed: 2026-03-01*

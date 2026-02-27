---
phase: 03-accounting-engine
plan: 02
subsystem: accounting
tags: [sqlalchemy, decimal, double-entry, airbnb, vrbo, rvshare, revenue-recognition, journal]

# Dependency graph
requires:
  - phase: 03-accounting-engine/03-01
    provides: create_journal_entry() builder, LineSpec, Account/JournalEntry/JournalLine ORM models, chart of accounts seeded in DB

provides:
  - recognize_booking_revenue() — operator-triggered, returns list of journal entries for all platforms
  - create_unearned_revenue_entry() — deferred revenue liability entry for Airbnb pre-payout bookings
  - record_adjustment_entries() — per-row journal entries for Adjustment/Credit/Resolution rows
  - reverse_journal_entry() — audit-preserving reversal for cancellations
  - _calculate_platform_fee() — gross = net / (1 - fee_rate) for both fee models
  - AppConfig.airbnb_fee_model field (default "split_fee")
  - AppConfig.airbnb_host_fee_rate field (default 0.03)
  - config/base.yaml defaults for both fee model fields

affects:
  - 03-06 (accounting API — will expose recognize_booking_revenue via POST endpoint)
  - 04-xx (reporting — revenue entries are the primary source for P&L reports)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Revenue recognition is operator-triggered (not auto on import) — explicit API call required"
    - "Deferred-then-recognized pattern for Airbnb: Unearned Revenue on booking, Rental Income on payout"
    - "Single-event recognition for VRBO/RVshare: net treated as gross (no fee data in CSV)"
    - "Per-row adjustment entries: each Adjustment/Credit/Resolution row its own journal entry"
    - "gross = net / (1 - fee_rate) formula works for both split_fee and host_only models"
    - "Module-level account cache (_account_cache) avoids repeated SELECTs for static chart of accounts"
    - "All config float rates converted via Decimal(str(rate)) before any arithmetic"
    - "source_id patterns: booking_payout:{platform}:{id}, booking_unearned:airbnb:{id}, adjustment:{platform}:{id}:{idx}, discount:{platform}:{id}:{idx}, reversal:{original}"

key-files:
  created:
    - app/accounting/revenue.py
  modified:
    - app/config.py
    - config/base.yaml

key-decisions:
  - "Airbnb fee model: default split_fee (0.03) per user decision — account is on legacy 3% host fee; host_only (15.5%) also fully implemented for future transition"
  - "Both fee models use same gross reconstruction formula: gross = net / (1 - fee_rate)"
  - "Switching fee models requires re-recognition of historical bookings (documented in config docstrings)"
  - "Airbnb Unearned Revenue clearing: if prior deferred entry exists, clearing entry generated automatically during payout recognition"
  - "Discount rows: debug log when absent (LOW CSV confidence from research), no error"
  - "VRBO/RVshare net = gross: no fee reconstruction without per-booking fee data in CSV"
  - "record_adjustment_entries() called from within recognize_booking_revenue() for Airbnb — caller does not need to call both"

patterns-established:
  - "Revenue recognition pattern: always returns list[JournalEntry|None] (not single entry) to accommodate multi-row bookings"
  - "Account cache pattern: module-level dict populated lazily on first query per account name"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 3 Plan 02: Revenue Recognition Summary

**Configurable double-entry revenue recognition for Airbnb (deferred-then-recognized with split_fee/host_only models), VRBO, and RVshare, with per-row adjustment entries and idempotent source_ids**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T21:45:56Z
- **Completed:** 2026-02-27T21:48:41Z
- **Tasks:** 2 (checkpoint:decision was pre-resolved by user; tasks 2 and 3 executed)
- **Files modified:** 3

## Accomplishments

- `recognize_booking_revenue()` produces correct double-entry entries for all three platforms; Airbnb uses deferred-then-recognized pattern; VRBO/RVshare use single-event recognition
- Fee reconstruction formula `gross = net / (1 - fee_rate)` verified for both models: host_only 15.5% produces gross=1183.43, fee=183.43 on net=1000; split_fee 3% produces gross=1030.93, fee=30.93
- `record_adjustment_entries()` handles Adjustment, Credit, Resolution rows (positive = credit to host, negative = clawback), plus Promotional Discount rows to contra-revenue account 4010
- AppConfig gains `airbnb_fee_model` (default "split_fee") and `airbnb_host_fee_rate` (default 0.03) fields matching user's current account type, with clear note that re-recognition is required if config changes

## Task Commits

Each task was committed atomically:

1. **Task 2: Add Airbnb fee model config fields to AppConfig** - `3246350` (feat)
2. **Task 3: Implement revenue recognition module** - `ad60f2b` (feat)

## Files Created/Modified

- `app/accounting/revenue.py` - Revenue recognition module: recognize_booking_revenue, create_unearned_revenue_entry, record_adjustment_entries, reverse_journal_entry, _calculate_platform_fee, _get_account_by_name with module-level cache
- `app/config.py` - Added airbnb_fee_model (default "split_fee") and airbnb_host_fee_rate (default 0.03) fields with docstrings explaining both models and re-recognition requirement
- `config/base.yaml` - Added matching defaults for both fee model fields

## Decisions Made

- **Default fee model is split_fee (0.03)**: Per user's confirmed account state — currently on legacy 3% host fee model. Both models (split_fee and host_only) are fully implemented. Config can be changed to "host_only" with rate 0.155 when account transitions.
- **Same formula for both models**: `gross = net / (1 - fee_rate)` works correctly for both because in both cases the Airbnb CSV net_amount is the host payout after the fee deduction.
- **Unearned Revenue auto-clearing**: When `recognize_booking_revenue()` processes a Payout row, it automatically checks for and clears any prior `booking_unearned:airbnb:{id}` entry via a second journal entry. Caller does not need to manage this.
- **VRBO/RVshare net = gross**: No fee line created since CSV exports do not contain per-booking fee breakdowns. If fee data becomes available in a future adapter update, `_recognize_vrbo_revenue()` should be updated.
- **DEBUG log for missing discounts**: Research assessed LOW confidence that discount rows appear in Airbnb CSV exports. Module logs DEBUG (not WARN) when no discount rows found — expected in most imports.
- **record_adjustment_entries called internally**: For Airbnb, `recognize_booking_revenue()` calls `record_adjustment_entries()` internally after processing the Payout row. API endpoints only need to call `recognize_booking_revenue()`.

## Deviations from Plan

None — plan executed exactly as written (checkpoint:decision was pre-resolved in execution context).

## Issues Encountered

None. `python` was not on PATH; used `uv run python` throughout. Config verification required DATABASE_URL env var (pydantic-settings cannot accept positional init arg as documented in plan's verify command).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `recognize_booking_revenue()` is importable and ready to be wired into API endpoints in 03-06
- Both fee models verified mathematically correct via Decimal arithmetic
- All source_id patterns documented and deterministic — safe for idempotent replay
- `reverse_journal_entry()` ready for cancellation handling (any future plan that implements cancellation endpoint)
- Blocker resolved: Airbnb fee model confirmed (split_fee default, host_only supported) — removed from STATE.md blockers

---
*Phase: 03-accounting-engine*
*Completed: 2026-02-27*

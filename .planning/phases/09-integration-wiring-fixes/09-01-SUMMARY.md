---
phase: 09-integration-wiring-fixes
plan: 01
subsystem: api
tags: [fastapi, router, llm, prompt, compliance, communication]

# Dependency graph
requires:
  - phase: 05-resort-pdf-compliance
    provides: compliance router (app/api/compliance.py) used as fix target
  - phase: 06-guest-communication
    provides: communication router (app/api/communication.py) and messenger.py used as fix targets
  - phase: 08-llm-natural-language-interface
    provides: SYSTEM_PROMPT in app/query/prompt.py used as fix target
provides:
  - Compliance router with /api/compliance prefix — frontend apiFetch calls no longer 404
  - Communication router with /api/communication prefix — frontend apiFetch calls no longer 404
  - LLM SYSTEM_PROMPT with correct attribution values ('jay', 'minnie', 'shared')
  - Verified Airbnb pre-arrival sends operator email and keeps status pending until confirmed
affects:
  - 09-02 (remaining gap closure plans in phase 9)
  - frontend ActionItem.tsx (compliance submit / communication confirm buttons now functional)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "All FastAPI routers except ingestion carry /api/ prefix to match frontend apiFetch convention"

key-files:
  created: []
  modified:
    - app/api/compliance.py
    - app/api/communication.py
    - app/query/prompt.py
    - app/communication/messenger.py

key-decisions:
  - "[09-01]: compliance router prefix /compliance -> /api/compliance — matches apiFetch('/compliance/...')"
  - "[09-01]: communication router prefix /communication -> /api/communication — matches apiFetch('/communication/...')"
  - "[09-01]: ingestion router prefix intentionally kept as /ingestion — uses FormData fetch, not apiFetch; changing it would break file uploads"
  - "[09-01]: attribution values corrected to 'jay', 'minnie', 'shared' in SYSTEM_PROMPT — matches _VALID_ATTRIBUTIONS frozenset in expenses.py"
  - "[09-01]: Gap 2 (Airbnb pre-arrival) confirmed already fixed in Phase 6 — no code change needed; verified operator email sent, status stays pending"

patterns-established:
  - "Router prefix convention: all /api/* routers except ingestion — ingestion uses raw /ingestion path"

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 9 Plan 01: Integration Wiring Fixes Summary

**Three surgical fixes: /api prefix added to compliance and communication routers ending 404s on Action tab buttons, LLM prompt attribution corrected from placeholder values to actual DB-enforced values ('jay', 'minnie', 'shared'), and Airbnb pre-arrival behavior verified as correct with stale docstring fixed**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-01T02:19:59Z
- **Completed:** 2026-03-01T02:21:08Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Compliance and communication routers now include `/api/` prefix — Action tab "Submit" and "Confirm" buttons will hit working endpoints instead of 404-ing
- LLM SYSTEM_PROMPT attribution field corrected from `'property', 'shared', 'personal'` (placeholder values) to `'jay', 'minnie', 'shared'` (actual DB-enforced values from `_VALID_ATTRIBUTIONS`)
- Airbnb pre-arrival gap verified as fixed in Phase 6: code correctly sends operator notification email and sets only `operator_notified_at`; status stays `pending` until operator confirms via API

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix router prefixes for compliance and communication** - `d00e65e` (fix)
2. **Task 2: Fix LLM attribution values and verify Airbnb pre-arrival** - `a76a3d6` (fix)

**Plan metadata:** (pending)

## Files Created/Modified
- `app/api/compliance.py` - Router prefix changed from `/compliance` to `/api/compliance`; docstring updated
- `app/api/communication.py` - Router prefix changed from `/communication` to `/api/communication`; docstring updated
- `app/query/prompt.py` - Attribution comment corrected from `'property','shared','personal'` to `'jay','minnie','shared'`
- `app/communication/messenger.py` - Stale docstring for `send_pre_arrival_message()` corrected: Airbnb branch description now matches actual code behavior

## Decisions Made
- Ingestion router prefix left unchanged at `/ingestion` — uses FormData fetch directly, not `apiFetch` which prepends `/api/`; changing it would break file uploads
- Gap 2 (Airbnb pre-arrival) documented as already satisfied in Phase 6 — no code change needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stale docstring in send_pre_arrival_message()**
- **Found during:** Task 2 (Airbnb pre-arrival verification)
- **Issue:** `send_pre_arrival_message()` docstring stated Airbnb branch "Updates status to 'sent' and sets sent_at" — the opposite of the actual code behavior. The actual code correctly sets only `operator_notified_at` and keeps status as `pending`.
- **Fix:** Updated Airbnb branch description in docstring to accurately describe the operator notification + pending status behavior (same pattern as VRBO/RVshare)
- **Files modified:** `app/communication/messenger.py`
- **Verification:** Docstring now matches actual code on lines 179-198; description confirmed accurate by reading the implementation
- **Committed in:** `a76a3d6` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - misleading docstring)
**Impact on plan:** Docstring fix necessary for correctness — stale description would mislead operators and future developers about Airbnb pre-arrival behavior. No scope creep.

## Gap 2: Airbnb Pre-Arrival Verification

Gap 2 confirmed already fixed in Phase 6 — no code change needed.

Evidence from `app/communication/messenger.py` `send_pre_arrival_message()`:
- Line 179: `if booking.platform == "airbnb":` — Airbnb branch entered
- Lines 184-197: `send_operator_notification_with_retry()` called — operator email sent
- Line 198: `comm_log.operator_notified_at = datetime.now(timezone.utc)` — only timestamp set
- There is NO `comm_log.status = "sent"` or `comm_log.sent_at` in the Airbnb branch
- Status remains at its original `pending` value until operator confirms via `POST /api/communication/confirm/{log_id}`

This matches the Phase 6 architectural decision (STATE.md line 173): "Airbnb pre-arrival sends operator notification email (same as VRBO/RVshare), status stays 'pending' until operator confirms via API — gap fix: was originally marking 'sent' without notification"

## Issues Encountered
None — both fixes were simple one-line changes. Verification commands all passed on first run.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Action tab buttons (Submit Resort Form, Confirm Communication) are now functional — frontend apiFetch calls route correctly to server endpoints
- LLM can now generate valid `WHERE e.attribution = 'jay'` clauses (was generating invalid `'property'` values)
- Phase 9 Plan 02 can proceed

---
*Phase: 09-integration-wiring-fixes*
*Completed: 2026-02-28*

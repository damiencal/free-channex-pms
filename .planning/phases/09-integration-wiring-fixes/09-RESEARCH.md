# Phase 9: Integration & Wiring Fixes - Research

**Researched:** 2026-02-28
**Domain:** FastAPI router configuration, frontend fetch routing, LLM prompt engineering, FastAPI BackgroundTasks
**Confidence:** HIGH — all four gaps verified against actual source files; no external library research required

## Summary

Phase 9 closes four discrete bugs identified in the v1 milestone audit. All four are small, surgical fixes — no new architecture, no new libraries, no new migrations. Three of the four are one-line or two-line changes; the fourth (revenue recognition automation) adds a background task to the existing ingestion pattern.

**Gap 1 — Router prefix mismatch (CRITICAL):** The compliance and communication routers define `prefix="/compliance"` and `prefix="/communication"` respectively. The frontend `apiFetch()` unconditionally prepends `/api` to every path. The result is that frontend calls hit `/api/compliance/...` and `/api/communication/...`, but the server only listens at `/compliance/...` and `/communication/...`. Fix: change both router prefixes to `/api/compliance` and `/api/communication`.

**Gap 2 — Airbnb pre-arrival notification (CRITICAL, partially fixed):** The audit reported this as missing, but the code in `app/communication/messenger.py` already implements operator notification for Airbnb pre-arrival (sends email, keeps status `pending`). The gap is now a mismatch between the audit report and the current implementation. Research confirms the fix was already applied in Phase 6 (`[06-02]` decision). This gap may be a false positive — the plan should verify the current state of `send_pre_arrival_message()` against the success criterion (status does NOT flip to `sent` until operator confirms). Current code does NOT set `sent_at` or flip to `sent` for Airbnb — it only sets `operator_notified_at`. The success criterion is already satisfied.

**Gap 3 — LLM attribution values wrong (INTEGRATION):** `app/query/prompt.py` line 81 documents the `expenses.attribution` column as `-- 'property', 'shared', 'personal'`. The actual valid values enforced by `app/accounting/expenses.py` are `frozenset({"jay", "minnie", "shared"})`. Fix: update the comment in SYSTEM_PROMPT from `'property', 'shared', 'personal'` to `'jay', 'minnie', 'shared'`.

**Gap 4 — Revenue recognition not automated (INTEGRATION):** The ingestion API already fires `_fire_background_submissions` (compliance) and `_fire_background_welcome_messages` (communication) as BackgroundTasks after CSV import. The pattern for adding revenue recognition automation is identical: add a `_fire_background_revenue_recognition` background task that calls `recognize_booking_revenue()` for each newly inserted booking ID. This keeps recognition operator-triggered in spirit but automates it after import.

**Primary recommendation:** Fix all four gaps with surgical file edits — no new files, no new dependencies, no migrations.

## Standard Stack

This phase uses no new libraries. All necessary tools are already installed.

### Core (Already in Use)
| Component | Location | Purpose |
|-----------|----------|---------|
| FastAPI `APIRouter` | `app/api/*.py` | Router prefix defines URL namespace |
| `apiFetch` | `frontend/src/api/client.ts` | Unconditionally prepends `/api` |
| `BackgroundTasks` | `app/api/ingestion.py` | Pattern for post-import async work |
| `recognize_booking_revenue` | `app/accounting/revenue.py` | Revenue recognition logic |
| `SYSTEM_PROMPT` | `app/query/prompt.py` | Hardcoded schema description for LLM |

### No New Installations Needed
All four fixes are configuration/content changes to existing files.

## Architecture Patterns

### Router Prefix Convention (Existing)

Routers with `/api` prefix (correct):
- `app/api/accounting.py`: `prefix="/api/accounting"`
- `app/api/dashboard.py`: `prefix="/api/dashboard"`
- `app/api/reports.py`: `prefix="/api/reports"`
- `app/api/query.py`: `prefix="/api/query"`

Routers WITHOUT `/api` prefix (broken — frontend gets 404):
- `app/api/compliance.py`: `prefix="/compliance"` → must be `prefix="/api/compliance"`
- `app/api/communication.py`: `prefix="/communication"` → must be `prefix="/api/communication"`

The ingestion router (`prefix="/ingestion"`) is also missing `/api`, but the ingestion endpoints are only called by file upload forms (not `apiFetch`) — verify whether these also 404. The audit only reports compliance and communication as broken Actions tab buttons, so ingestion may be exempt or handled differently.

### BackgroundTask Revenue Recognition Pattern (Existing)

The ingestion API already follows this exact pattern for compliance submissions:

```python
# In app/api/ingestion.py — existing pattern to replicate
async def _fire_background_submissions(booking_db_ids: list[int], db: Session) -> None:
    for booking_id in booking_db_ids:
        try:
            await process_booking_submission(booking_id, db)
        except Exception:
            bg_log.exception("Background submission failed", booking_id=booking_id)

# In upload_airbnb_csv():
inserted_db_ids = result.get("inserted_db_ids", [])
if inserted_db_ids:
    config = get_config()
    if should_auto_submit(db, config.auto_submit_threshold):
        background_tasks.add_task(_fire_background_submissions, inserted_db_ids, db)
```

Revenue recognition follows the same pattern — add a `_fire_background_revenue_recognition` function and call `background_tasks.add_task(...)` after the existing auto-submit block in all three upload endpoints (Airbnb, VRBO, RVshare manual entry).

### SYSTEM_PROMPT Schema Documentation (Existing)

The prompt is a single hardcoded string in `app/query/prompt.py`. The schema comment to fix is on line 81:

```python
# BEFORE (wrong):
  attribution  VARCHAR(32)             -- 'property', 'shared', 'personal'

# AFTER (correct):
  attribution  VARCHAR(32)             -- 'jay', 'minnie', 'shared'
```

No other prompt changes are needed. Property slug and display_name comments on lines 43-44 already correctly document `'jay', 'minnie'`.

### Anti-Patterns to Avoid

- **Do not change `apiFetch` to NOT prepend `/api`** — the routers that already have `/api/` prefix would break. The correct fix is always to add the prefix to the missing routers.
- **Do not add revenue recognition inside the normalizer** — the normalizer is a pure Python module with no access to `AppConfig` fee models or async capabilities. The API layer is the correct place.
- **Do not make revenue recognition conditional on `should_auto_submit`** — compliance submission has a preview threshold; revenue recognition has no equivalent gate. Always run on insert.
- **Do not change `ingestion` router prefix** — file upload endpoints are not called via `apiFetch`; they use a `FormData` fetch pattern. Changing the ingestion prefix could break upload unless frontend calls are also updated.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Post-import revenue recognition | Custom event/signal system | FastAPI `BackgroundTasks.add_task()` | Already used for compliance, identical pattern |
| Router URL mapping | Middleware or URL rewriting | Set `prefix="/api/compliance"` in `APIRouter()` | One-line fix |

## Common Pitfalls

### Pitfall 1: Forgetting to Update the `ingestion` Router Prefix
**What goes wrong:** The audit only calls out compliance and communication as broken, but the `ingestion` router also lacks `/api`. If frontend upload forms call `/api/ingestion/...` they will also 404.
**Why it happens:** Three routers share the same pattern of missing `/api`. The audit only tested the Actions tab buttons.
**How to avoid:** Check all routers in `app/api/` for prefix consistency. Verify that `ingestion` endpoints are actually called from `apiFetch` or a different fetch path before deciding whether to fix them.
**Verification:** `grep -n "prefix=" app/api/*.py` — should all show `/api/` prefix.

### Pitfall 2: Revenue Recognition Running Before DB Commit
**What goes wrong:** `_fire_background_revenue_recognition` calls `recognize_booking_revenue()` which queries `Booking` by ID. If the DB hasn't committed the new bookings before the background task runs, the bookings won't be found.
**Why it happens:** FastAPI background tasks run AFTER the response is sent, which means after the request handler returns — but the DB commit happens inside the request handler (normalizer calls `db.commit()` or the endpoint does).
**How to avoid:** Verify that `ingest_csv()` calls `db.commit()` before returning. Existing background submission tasks (`_fire_background_submissions`) work correctly, proving the commit happens before background tasks fire.
**Warning signs:** Revenue recognition background task logs "Booking not found" for freshly inserted bookings.

### Pitfall 3: Revenue Recognition Duplicate Entries
**What goes wrong:** Calling `recognize_booking_revenue()` twice for the same booking creates duplicate journal entries.
**Why it happens:** If the operator also calls `POST /api/accounting/revenue/recognize-all` after the automated recognition, each booking gets recognized twice.
**How to avoid:** `recognize_booking_revenue()` already calls `create_journal_entry()` which checks `source_id` uniqueness (idempotent — returns `None` if source_id already exists). The existing `recognize-all` endpoint already filters to bookings without existing journal entries. Both are safe.
**Verification:** Check `app/accounting/journal.py` for idempotent `create_journal_entry()` implementation.

### Pitfall 4: Airbnb Pre-Arrival Gap Is Already Fixed
**What goes wrong:** The planner creates a task to fix the Airbnb pre-arrival notification, but the code already implements it correctly.
**Why it happens:** The v1 audit report captures a state that was already partially fixed during Phase 6 planning sessions.
**How to avoid:** Read `app/communication/messenger.py` `send_pre_arrival_message()`. For `platform == "airbnb"`, it already calls `send_operator_notification_with_retry()` and sets `operator_notified_at` without flipping `status` to `sent`. The success criterion (status stays `pending`) is already satisfied.
**Recommended plan task:** Add a verification-only task to confirm behavior matches the success criterion, then document it as already-satisfied. No code change needed.

### Pitfall 5: SYSTEM_PROMPT Example Queries Reference Wrong Attribution
**What goes wrong:** After fixing the schema comment, the example query for "cleaning expenses for Minnie" doesn't filter by attribution. This is fine — the example only filters by `p.slug`. But if example queries were to demonstrate attribution filtering, they would need updating too.
**Why it happens:** The example queries in the prompt don't use `WHERE e.attribution = ...` at all, so no example query is broken.
**How to avoid:** Only fix line 81's comment — the example queries are correct as-is.

## Code Examples

### Gap 1: Router Prefix Fix
```python
# app/api/compliance.py — line 25
# BEFORE:
router = APIRouter(prefix="/compliance", tags=["compliance"])

# AFTER:
router = APIRouter(prefix="/api/compliance", tags=["compliance"])
```

```python
# app/api/communication.py — line 20
# BEFORE:
router = APIRouter(prefix="/communication", tags=["communication"])

# AFTER:
router = APIRouter(prefix="/api/communication", tags=["communication"])
```

### Gap 3: LLM Attribution Values Fix
```python
# app/query/prompt.py — line 81
# BEFORE:
  attribution  VARCHAR(32)             -- 'property', 'shared', 'personal'

# AFTER:
  attribution  VARCHAR(32)             -- 'jay', 'minnie', 'shared'
```

### Gap 4: Revenue Recognition BackgroundTask
```python
# app/api/ingestion.py — new helper function (follow existing pattern)
async def _fire_background_revenue_recognition(booking_db_ids: list[int], db: Session) -> None:
    """Recognize revenue for newly imported bookings.

    Called as BackgroundTask after CSV import. Mirrors the pattern of
    _fire_background_submissions(). Errors are logged, never propagated.
    """
    from app.accounting.revenue import recognize_booking_revenue
    from app.config import get_config

    bg_log = structlog.get_logger()
    config = get_config()
    for booking_id in booking_db_ids:
        try:
            booking = db.get(Booking, booking_id)
            if booking is None:
                bg_log.warning("Revenue recognition: booking not found", booking_id=booking_id)
                continue
            results = recognize_booking_revenue(db, booking, config)
            db.commit()
            bg_log.info(
                "Revenue recognized",
                booking_id=booking_id,
                entries_created=sum(1 for r in results if r is not None),
            )
        except Exception:
            db.rollback()
            bg_log.exception("Background revenue recognition failed", booking_id=booking_id)


# In upload_airbnb_csv(), upload_vrbo_csv(), create_rvshare_booking():
# Add after existing auto-submit block:
if inserted_db_ids:
    background_tasks.add_task(_fire_background_revenue_recognition, inserted_db_ids, db)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Revenue recognition operator-triggered only | Automated via BackgroundTask on import | Phase 9 | Operator no longer needs to call recognize-all manually |
| Compliance/communication endpoints at `/compliance/...` | Endpoints at `/api/compliance/...` and `/api/communication/...` | Phase 9 | Action buttons work without 404 |
| LLM prompt documents attribution as `'property', 'shared', 'personal'` | Correct values: `'jay', 'minnie', 'shared'` | Phase 9 | LLM generates correct WHERE clauses for attribution queries |

## Open Questions

1. **Should the `ingestion` router also gain the `/api/` prefix?**
   - What we know: `prefix="/ingestion"` (no `/api`). Upload endpoints use `FormData` fetch from the future Data Import UI (Phase 10), not `apiFetch`. The Actions tab does not call ingestion endpoints.
   - What's unclear: Whether Phase 10's frontend upload forms will use `apiFetch` (which prepends `/api`) or a raw `fetch()` call.
   - Recommendation: Leave ingestion prefix as-is for Phase 9. Phase 10 will define the upload UI and can align the prefix at that time. Document this as a known inconsistency to address in Phase 10.

2. **Should revenue recognition run for ALL inserted bookings or only those past preview threshold?**
   - What we know: Compliance auto-submit is gated by `should_auto_submit()` (preview threshold). Revenue recognition has no equivalent gate in the existing `recognize-all` endpoint.
   - What's unclear: Whether Kim (the operator) wants bookings to appear in financial metrics immediately after import, or only after manual review.
   - Recommendation: Run revenue recognition unconditionally for all inserted bookings. The `recognize_booking_revenue()` function is idempotent, and the success criterion says "dashboard financial metrics reflect imported booking revenue without a separate manual API call" — no gate mentioned.

## Sources

### Primary (HIGH confidence)
- Direct source reading: `app/api/compliance.py` line 25 — router prefix confirmed `/compliance`
- Direct source reading: `app/api/communication.py` line 20 — router prefix confirmed `/communication`
- Direct source reading: `frontend/src/api/client.ts` lines 8-9 — `apiFetch` prepends `/api` unconditionally
- Direct source reading: `app/query/prompt.py` line 81 — attribution documented as `'property', 'shared', 'personal'`
- Direct source reading: `app/accounting/expenses.py` line 60 — `_VALID_ATTRIBUTIONS = frozenset({"jay", "minnie", "shared"})`
- Direct source reading: `app/api/ingestion.py` — BackgroundTasks pattern for compliance and welcome messages
- Direct source reading: `app/communication/messenger.py` `send_pre_arrival_message()` — Airbnb branch already sends notification, keeps status `pending`
- Direct source reading: `.planning/v1-MILESTONE-AUDIT.md` — original gap descriptions

### No External Sources Required
All gaps are verified from codebase source files. No library documentation, WebSearch, or Context7 queries needed — this is pure configuration/content correction work.

## Metadata

**Confidence breakdown:**
- Gap 1 (router prefix): HIGH — verified `prefix=` values in both routers and `apiFetch` source
- Gap 2 (Airbnb notification): HIGH — `send_pre_arrival_message()` code read line by line; gap already fixed in Phase 6
- Gap 3 (LLM attribution): HIGH — both the wrong value (prompt.py:81) and correct value (expenses.py:60) verified
- Gap 4 (revenue automation): HIGH — BackgroundTasks pattern already used twice in same file; identical replication

**Research date:** 2026-02-28
**Valid until:** Indefinite — all findings are from static source files in this repo, not external APIs or library docs

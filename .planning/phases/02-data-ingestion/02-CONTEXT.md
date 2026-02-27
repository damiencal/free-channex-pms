# Phase 2: Data Ingestion - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

CSV import pipelines for Airbnb, VRBO, and Mercury bank transactions, plus a manual entry API endpoint for RVshare bookings — all normalized to a unified booking/transaction schema and stored in the database. The dashboard UI for manual entry and the accounting engine that processes these records are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Import trigger & workflow
- Import mechanism: Claude's discretion — fit to existing FastAPI setup (API endpoint is expected)
- Raw CSV archive path: Configurable in settings (`archive_dir`) — operator sets path, can point anywhere on host
- Archive timing: Archive first, then process — even failed imports leave a trace in the archive
- RVshare manual entry: Phase 2 provides the API endpoint only; the admin form UI is deferred to Phase 7 dashboard

### Error handling & partial failures
- Bad row behavior: Halt-and-report — validate the entire CSV before writing anything; list all errors, then require operator to fix and re-import. Nothing is written to the database on validation failure.
- Error report format: Row number + field name + problem description for each bad row (e.g., "Row 47: check_in_date is missing. Row 52: amount is not a number.")
- Wrong structure/headers: Fail immediately with a clear message — "This doesn't look like an Airbnb Transaction History CSV. Expected headers: …" — no point validating rows if the file is wrong
- Airbnb format quirks (apostrophes in amounts, non-standard dates): Silently normalize — adapter handles these transparently as expected behavior, no warning needed

### Deduplication behavior
- Re-import behavior: Update in place — overwrite existing record with new values from the re-imported CSV
- Airbnb stable ID: Confirmation code from CSV column
- Airbnb multi-row events: Group at ingestion — collapse booking creation, payout release, and adjustments by confirmation code into one booking record with net amount. Accounting engine receives pre-grouped records.
- VRBO stable ID: VRBO-specific identifier (use whatever column in VRBO exports is most stable — reservation ID if available, not confirmation code)
- Mercury bank transactions: Platform-native transaction ID as stable key (deduplication by ID)

### Import feedback & visibility
- Success response: Counts + list of what changed — summary (e.g., "38 new, 4 updated, 0 skipped") plus which confirmation codes were inserted vs updated
- Import history: Persistent `ImportRun` database table — timestamp, source platform, filename, inserted/updated/skipped counts — queryable via API for Phase 7 dashboard
- Booking list minimum fields: platform, confirmation_code, guest_name, check_in_date, check_out_date, net_amount, property_slug

### Claude's Discretion
- Exact API endpoint design (path, HTTP method, request format)
- Specific column names in Airbnb/VRBO/Mercury CSV schemas (researcher will inspect actual files)
- Internal normalizer architecture (whether adapters return raw dicts or typed models)
- Mercury transaction deduplication key (to be confirmed from actual Mercury CSV format)
- VRBO stable reservation identifier column name (to be confirmed from actual VRBO export)

</decisions>

<specifics>
## Specific Ideas

- Operator should be able to see "data was last refreshed" from import history — the ImportRun table supports this
- RVshare manual entry is Phase 2's only non-CSV path; treat it as a simple JSON POST endpoint for now, no UI needed
- Airbnb CSV quirks (apostrophe-separated amounts, non-ISO dates) are known and should be handled silently — they are not errors

</specifics>

<deferred>
## Deferred Ideas

- RVshare manual entry admin form UI — Phase 7 dashboard
- Import trigger via watched folder (auto-process on file drop) — possible future enhancement, not needed for v1
- Per-booking status view in the UI — Phase 7 dashboard

</deferred>

---

*Phase: 02-data-ingestion*
*Context gathered: 2026-02-27*

# Phase 10: Data Import UI - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Frontend interface for CSV uploads (Airbnb, VRBO, Mercury) and RVshare manual booking entry, plus import history view. All backend API endpoints exist from Phase 2 — this phase wraps them in a user-friendly UI within the existing React + shadcn/ui dashboard from Phase 7. Lives inside the existing Actions tab in AppShell.

</domain>

<decisions>
## Implementation Decisions

### Upload experience
- Single drop zone for all platforms — user selects file first, then picks platform (Airbnb/VRBO/Mercury) from a dropdown before submitting
- Compact card-style drop zone — not oversized; upload icon + text, fits within the Actions tab layout
- Lives inside the existing Actions tab (not a new tab) — import is an action alongside pending resort forms and messages
- Progress bar shown during upload — not just a spinner

### RVshare manual entry form
- Section below the CSV upload area, always visible (not modal or separate tab)
- "Add RVshare Booking" button expands the form inline via accordion/toggle — collapsed by default to keep page clean
- Property pre-selected from AppShell header selector — can be changed on the form if needed
- After successful submit: show "Booking added" inline success message, then collapse the form back to button state
- Validate on blur (field exit) — immediate per-field feedback as user tabs through

### Import results & errors
- Success: show detailed summary (record count, new vs skipped, platform, property breakdown) plus scrollable list of individual imported records
- Errors (wrong format, missing columns): replace the drop zone with an error state showing details + "Try again" button to reset
- All-or-nothing import — if any record fails, reject the entire file; user fixes CSV and re-uploads
- Results persist until user explicitly dismisses via "Upload another" or X button — no auto-dismiss

### Import history
- Collapsible accordion section below the upload area — collapsed by default, expand to see past imports
- Detailed columns: timestamp, platform, original filename, record count, success/error status, property
- No filtering — reverse-chronological list is sufficient for this scale of operation
- Show last 10 imports by default with "Show more" link for older entries

### Claude's Discretion
- Exact layout spacing and component sizing within Actions tab
- Drop zone hover/drag-active visual states
- Platform dropdown vs radio button for platform selection
- Date picker component choice for RVshare form
- Record list display format in success results (table vs card list)
- "Show more" pagination implementation for import history

</decisions>

<specifics>
## Specific Ideas

- Import UI should feel like a natural extension of the Actions tab — not a separate "module" bolted on
- The compact card-style drop zone should not dominate the page; other action items (resort forms, messages) remain visible
- RVshare form should be minimal — just required fields, nothing intimidating for a non-technical user

</specifics>

<deferred>
## Deferred Ideas

- Investigate RVshare Stripe integration for transaction history import — RVshare appears to use Stripe; may enable automated import instead of manual entry in a future phase

</deferred>

---

*Phase: 10-data-import-ui*
*Context gathered: 2026-02-28*

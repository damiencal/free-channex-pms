# Phase 5: Resort PDF Compliance - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Automated resort booking notification — when a booking is imported, the system fills the Sun Outdoors/Sun Retreats PDF registration form with guest and property details, emails it (with the platform booking confirmation attached) to the resort contact, tracks submission status through to resort confirmation, and flags any approaching deadlines. Manual booking entry, booking ingestion, and dashboard display are handled by other phases.

</domain>

<decisions>
## Implementation Decisions

### Submission trigger & workflow
- Auto-submit on booking import — PDF filled and emailed immediately with no manual step
- Count-based preview mode — first N submissions require manual approval to verify correctness, then system switches to full auto-submit
- Preview-to-auto transition controlled by a count threshold (Claude's discretion on exact implementation)
- Missing data handling: resort only requires Guest Name, dates of stay, lot number, number of guests, and host info at the top — guest phone/email are always "N/A"
- Lot number mapping: Jay → 110, Minnie → 170 (from config)

### Email content & delivery
- Subject line format: "Booking Form - {Guest Name} - Lot {number} - {dates}" (e.g., "Booking Form - John Smith - Lot 110 - Mar 5-8")
- Email body template: "Hi CHANGE_ME, please find the attached booking form for the upcoming stay. The booking confirmation is also enclosed. Thanks, Thomas"
- Recipient name (CHANGE_ME) and email address from config — not hardcoded
- Two attachments per email: filled PDF form + platform booking confirmation
- Booking confirmations are file-based — saved to a `confirmations/` directory (via n8n or mail rule), matched to bookings by confirmation code in the filename (e.g., `HMAB1234.pdf`)

### Confirmation & status lifecycle
- Three statuses: pending → submitted → confirmed
- "Confirmed" triggered via n8n webhook — n8n detects the Campspot automated confirmation email (from do-not-reply@campspot.com, subject contains "Reservation Confirmation") and calls the system's API to mark the submission as confirmed
- CHANGE_ME also replies manually, but the Campspot email is the automated trigger
- On email send failure: retry silently (multiple attempts), only surface if all retries exhausted

### Deadline & urgency behavior
- 3-day window: form must be submitted at least 3 days before guest check-in
- No last-minute booking edge case — listings enforce minimum 3-day advance booking, matching the resort requirement
- Daily urgency check — once per day, flag any pending submissions where check-in is within 3 days
- Urgent submissions flagged both in the API (for dashboard visibility) AND via email alert to the operator

### Claude's Discretion
- Exact count for preview-to-auto threshold
- Email retry strategy (count, backoff timing)
- Confirmation filename matching logic details
- Daily check scheduling time

</decisions>

<specifics>
## Specific Ideas

- Email body tone is casual/friendly — "Hi CHANGE_ME" not "Dear Resort Management"
- The resort contact (CHANGE_ME) and their email should be config-driven so it can change without code changes
- Campspot confirmation emails come from do-not-reply@campspot.com with "Reservation Confirmation" in the subject — this is what n8n should match on
- Two separate acknowledgements exist: CHANGE_ME's manual reply + Campspot automated email. Only the Campspot email triggers auto-confirmation via webhook.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-resort-pdf-compliance*
*Context gathered: 2026-02-27*

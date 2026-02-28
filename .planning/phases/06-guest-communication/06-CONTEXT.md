# Phase 6: Guest Communication - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Automated guest messaging for bookings across all platforms. Two message types: welcome (on booking) and pre-arrival (2 days before check-in). Airbnb uses native scheduled messaging; VRBO and RVshare are semi-automated (system prepares text, operator sends manually). All content driven by config-editable Jinja2 templates.

</domain>

<decisions>
## Implementation Decisions

### Message content & tone
- Professional & welcoming tone — polished but warm, not overly casual
- Welcome message: thank guest for booking + set expectations that arrival details come closer to check-in
- Pre-arrival message: lock code + check-in time + address + property-specific instructions (resort check-in, parking, wifi) + local tips (restaurants, grocery, emergency contacts)
- Same content structure across platforms with minor platform-specific tweaks (e.g., reference Airbnb app for Airbnb guests, different contact method for VRBO)

### Scheduling & timing
- Welcome message: configured via Airbnb's native scheduled messaging — system tracks status but Airbnb sends automatically
- Pre-arrival message: sent 2 days before check-in
- Pre-arrival send time: morning, 9-10am
- No late-booking edge case — all listings require minimum 3-day advance booking, so pre-arrival window is always available
- For VRBO/RVshare: system prepares message at the same timing, emails operator to send manually

### VRBO/RVshare operator workflow
- Same semi-automated flow for both VRBO and RVshare
- Notification: both email AND dashboard pending action (dashboard in Phase 7)
- Email contains: complete message text ready to copy + guest name, reservation ID, check-in date for VRBO/RVshare lookup
- Operator marks message as sent via button/endpoint — explicit confirmation required, no auto-marking
- Message stays as pending until operator confirms

### Template variables & customization
- Templates live in templates/ directory (alongside existing Jinja2 templates): templates/messages/welcome.j2, templates/messages/pre_arrival.j2
- Shared templates across all properties — per-property data comes from config variables
- Variables include: guest_name, check_in_date, check_out_date, property_name, lock_code, wifi_password, check_in_time, check_out_time, address, parking_instructions, resort_rules, plus arbitrary custom key-value pairs per property
- Hot reload: templates re-read from disk on each message preparation — edits take effect immediately without restart

### Claude's Discretion
- Exact template file structure within templates/messages/
- How custom key-value pairs are stored in property config schema
- Platform-specific template variations (inline conditionals vs separate partials)
- Email notification subject line and formatting for operator alerts
- Communication log schema design

</decisions>

<specifics>
## Specific Ideas

- Airbnb welcome message handled entirely by Airbnb's native scheduled messaging feature — system configures/tracks but doesn't send
- VRBO notification email should make it trivially easy to copy-paste the message into VRBO — full text ready to go
- Pre-arrival info should be comprehensive enough that guests don't need to message the host asking basic questions

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-guest-communication*
*Context gathered: 2026-02-27*

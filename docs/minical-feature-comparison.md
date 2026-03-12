# miniCal vs Roost — Feature Comparison Checklist

> **Purpose**: Line-by-line feature parity checklist so a coding agent can replicate miniCal's capabilities inside Roost.
> Each row shows: the feature, whether miniCal has it, whether Roost has it, and what work remains.

**Legend**
| Symbol | Meaning |
|--------|---------|
| ✅ | Fully implemented |
| 🔶 | Partially implemented / different approach |
| ❌ | Not implemented |
| N/A | Not applicable to this project's domain |

---

## 1. Calendar & Booking Management

| #   | Feature                                           | miniCal | Roost | Gap / Notes                                                                                                 |
| --- | ------------------------------------------------- | ------- | ----- | ----------------------------------------------------------------------------------------------------------- |
| 1.1 | Interactive calendar view (month/week/day)        | ✅      | 🔶    | Roost has month calendar + timeline. Missing week/day views, room-row layout.                               |
| 1.2 | Drag-and-drop booking move (re-assign room/dates) | ✅      | ❌    | Roost calendar is read-only display. Need DnD interaction layer.                                            |
| 1.3 | Booking block resize (extend/shorten stay)        | ✅      | ❌    | Requires calendar interactivity.                                                                            |
| 1.4 | Real-time occupancy display on calendar           | ✅      | 🔶    | Roost calculates occupancy but shows it on dashboard charts, not overlaid on calendar.                      |
| 1.5 | Room-wise calendar rows                           | ✅      | ❌    | miniCal shows one row per room; Roost shows per-property timeline. Need room-level if managing hotel rooms. |
| 1.6 | Room-type grouped view                            | ✅      | ❌    | miniCal groups calendar rows by room type.                                                                  |
| 1.7 | Color-coded booking states                        | ✅      | 🔶    | Roost colors by platform (Airbnb=red, VRBO=blue). miniCal colors by state (in-house, reservation, etc.).    |
| 1.8 | Multi-week/extended range view                    | ✅      | ❌    | miniCal has configurable range. Roost shows single month.                                                   |

---

## 2. Booking Creation & Lifecycle

| #    | Feature                                                             | miniCal | Roost | Gap / Notes                                                                                                      |
| ---- | ------------------------------------------------------------------- | ------- | ----- | ---------------------------------------------------------------------------------------------------------------- |
| 2.1  | Manual booking creation                                             | ✅      | ✅    | Both support direct/manual bookings.                                                                             |
| 2.2  | Booking form with custom fields                                     | ✅      | ❌    | miniCal allows admin-defined custom booking fields. Roost has fixed schema.                                      |
| 2.3  | Booking state machine (Reservation → In-house → Checkout → No-show) | ✅      | 🔶    | Roost tracks `reconciliation_status` (unmatched/matched/confirmed/disputed) but no hotel-style lifecycle states. |
| 2.4  | Check-in / check-out workflow                                       | ✅      | ❌    | miniCal has explicit check-in/check-out actions. Roost derives status from dates.                                |
| 2.5  | Group/linked bookings                                               | ✅      | ❌    | miniCal links multiple bookings. Roost has no group concept.                                                     |
| 2.6  | Booking notes (internal)                                            | ✅      | ✅    | Both support notes on bookings.                                                                                  |
| 2.7  | Guest count (adults + children)                                     | ✅      | ❌    | miniCal tracks adult/child count. Roost only stores guest name.                                                  |
| 2.8  | Booking source tracking                                             | ✅      | ✅    | miniCal: custom sources. Roost: platform field (Airbnb, VRBO, etc.).                                             |
| 2.9  | Booking search & filter                                             | ✅      | ✅    | Both have filtering. Roost filters: platform, property, date range. miniCal: guest, date, status, source.        |
| 2.10 | Booking modification history / audit log                            | ✅      | 🔶    | miniCal logs all changes. Roost stores `raw_platform_data` for imports but no change log.                        |
| 2.11 | Overbooking protection                                              | ✅      | ❌    | miniCal prevents double-booking same room. Roost has no room-level allocation.                                   |
| 2.12 | Overbooking override (allow with flag)                              | ✅      | N/A   | Requires room allocation first.                                                                                  |
| 2.13 | Booking balance tracking                                            | ✅      | 🔶    | miniCal tracks per-booking balance. Roost tracks net payout only; no folio/balance concept.                      |
| 2.14 | Registration card printing                                          | ✅      | ❌    | miniCal generates guest registration cards.                                                                      |
| 2.15 | Booking confirmation emails                                         | ✅      | 🔶    | miniCal auto-sends. Roost has triggered message templates but primarily for operator copy-paste.                 |

---

## 3. Room & Inventory Management

| #    | Feature                                         | miniCal | Roost | Gap / Notes                                                                                             |
| ---- | ----------------------------------------------- | ------- | ----- | ------------------------------------------------------------------------------------------------------- |
| 3.1  | Room master setup (individual rooms)            | ✅      | ❌    | miniCal manages individual rooms. Roost manages properties (entire units), not rooms within a property. |
| 3.2  | Room type definitions                           | ✅      | ❌    | miniCal: SNG, DBL, SUITE, etc. Roost has no room types.                                                 |
| 3.3  | Room naming & identifiers                       | ✅      | N/A   | Roost uses property slugs, not room numbers.                                                            |
| 3.4  | Floor / building / location hierarchy           | ✅      | ❌    | miniCal supports floors + buildings.                                                                    |
| 3.5  | Room status (clean / dirty / maintenance / OOO) | ✅      | 🔶    | Roost has cleaning tasks with status, but no room-state tracking.                                       |
| 3.6  | Housekeeping status updates                     | ✅      | 🔶    | Roost tracks task status (pending/in_progress/completed). miniCal has room-level dirty/clean.           |
| 3.7  | Out-of-order rooms                              | ✅      | ❌    | miniCal blocks rooms from sale.                                                                         |
| 3.8  | Availability calendar (visual)                  | ✅      | 🔶    | Roost has Channex calendar integration; no native availability grid.                                    |
| 3.9  | Bulk availability open/close                    | ✅      | 🔶    | Via Channex API only. No native UI.                                                                     |
| 3.10 | Max occupancy / capacity rules                  | ✅      | ❌    | Per room type in miniCal.                                                                               |
| 3.11 | Minimum stay requirements                       | ✅      | 🔶    | Channex availability update supports min_stay. No native rule storage.                                  |
| 3.12 | Closeout dates / stop-sell                      | ✅      | 🔶    | Via Channex only.                                                                                       |
| 3.13 | Channel-specific availability                   | ✅      | 🔶    | Via Channex.                                                                                            |
| 3.14 | Online/offline room toggle                      | ✅      | ❌    | miniCal controls which rooms appear in booking engine.                                                  |

---

## 4. Rate & Pricing Management

| #    | Feature                                        | miniCal | Roost | Gap / Notes                                                                    |
| ---- | ---------------------------------------------- | ------- | ----- | ------------------------------------------------------------------------------ |
| 4.1  | Rate plan definitions (multiple per room type) | ✅      | ❌    | miniCal has flexible rate plans. Roost stores only net payout from platform.   |
| 4.2  | Dynamic / date-based pricing                   | ✅      | ❌    | miniCal sets daily rates. Roost doesn't manage pricing—platforms handle it.    |
| 4.3  | Seasonal pricing                               | ✅      | ❌    |                                                                                |
| 4.4  | Occupancy-based pricing                        | ✅      | ❌    |                                                                                |
| 4.5  | Per-adult / per-child pricing                  | ✅      | ❌    |                                                                                |
| 4.6  | Rate plan hierarchy (parent/child)             | ✅      | ❌    |                                                                                |
| 4.7  | Daily rate override                            | ✅      | ❌    |                                                                                |
| 4.8  | Channel rate sync (push to OTAs)               | ✅      | 🔶    | Roost can update rates via Channex API, but no native rate management UI.      |
| 4.9  | Currency support                               | ✅      | ❌    | miniCal supports multi-currency. Roost is USD-only.                            |
| 4.10 | Commission rate per channel                    | ✅      | 🔶    | Roost reconstructs fees from Airbnb split model; not configurable per-channel. |

---

## 5. Guest & Customer Management

| #    | Feature                                     | miniCal | Roost | Gap / Notes                                                                                          |
| ---- | ------------------------------------------- | ------- | ----- | ---------------------------------------------------------------------------------------------------- |
| 5.1  | Guest profile database                      | ✅      | ❌    | miniCal has full CRM. Roost stores guest name/email/phone per booking only—no unified guest profile. |
| 5.2  | Customer types (individual, corporate, VIP) | ✅      | ❌    |                                                                                                      |
| 5.3  | Customer search (name, email, phone)        | ✅      | 🔶    | Roost searches bookings by guest name; no dedicated guest search.                                    |
| 5.4  | Guest stay history                          | ✅      | 🔶    | Can query bookings by guest name, but no linked profile.                                             |
| 5.5  | Guest balance / credit tracking             | ✅      | ❌    |                                                                                                      |
| 5.6  | Custom customer fields                      | ✅      | ❌    | miniCal supports admin-defined fields.                                                               |
| 5.7  | Returning guest auto-fill                   | ✅      | ❌    | miniCal auto-populates known guests.                                                                 |
| 5.8  | Guest preferences storage                   | ✅      | ❌    |                                                                                                      |
| 5.9  | Customer activity/interaction log           | ✅      | ❌    |                                                                                                      |
| 5.10 | Booked-by vs guest tracking                 | ✅      | ❌    | miniCal separates who booked from who stays.                                                         |

---

## 6. Payment & Invoice Management

| #    | Feature                                      | miniCal | Roost | Gap / Notes                                                                            |
| ---- | -------------------------------------------- | ------- | ----- | -------------------------------------------------------------------------------------- |
| 6.1  | Payment gateway integration                  | ✅      | ❌    | miniCal integrates payment processors. Roost receives payouts from platforms post-hoc. |
| 6.2  | Multiple payment methods (cash, card, check) | ✅      | ❌    |                                                                                        |
| 6.3  | Payment capture / authorization              | ✅      | ❌    |                                                                                        |
| 6.4  | Token-based secure payment storage           | ✅      | ❌    |                                                                                        |
| 6.5  | Invoice generation per booking               | ✅      | ❌    | miniCal auto-creates invoices. Roost uses journal entries, not invoices.               |
| 6.6  | Master/consolidated invoices                 | ✅      | ❌    |                                                                                        |
| 6.7  | Invoice numbering (sequential)               | ✅      | ❌    |                                                                                        |
| 6.8  | Partial payments                             | ✅      | ❌    |                                                                                        |
| 6.9  | Refund processing                            | ✅      | ❌    |                                                                                        |
| 6.10 | Guest-facing invoice view (shareable link)   | ✅      | ❌    | miniCal generates hash-based public invoice links.                                     |
| 6.11 | Room charges / folio                         | ✅      | ❌    | miniCal maintains a per-stay folio.                                                    |
| 6.12 | Extra charges (parking, minibar, etc.)       | ✅      | ❌    |                                                                                        |
| 6.13 | Service charges                              | ✅      | ❌    |                                                                                        |
| 6.14 | Charge type definitions                      | ✅      | ❌    |                                                                                        |

---

## 7. Tax Management

| #   | Feature                              | miniCal | Roost | Gap / Notes                                                          |
| --- | ------------------------------------ | ------- | ----- | -------------------------------------------------------------------- |
| 7.1 | Tax type definitions                 | ✅      | ❌    | miniCal defines tax categories. Roost doesn't manage taxes directly. |
| 7.2 | Tax rate configuration               | ✅      | ❌    |                                                                      |
| 7.3 | Tax brackets (tiered rates)          | ✅      | ❌    |                                                                      |
| 7.4 | Inclusive / exclusive tax handling   | ✅      | ❌    |                                                                      |
| 7.5 | Flat-rate taxes                      | ✅      | ❌    |                                                                      |
| 7.6 | Automatic tax calculation on charges | ✅      | ❌    |                                                                      |
| 7.7 | Tax-to-charge association            | ✅      | ❌    |                                                                      |

---

## 8. Extra Services & Add-ons

| #   | Feature                   | miniCal | Roost | Gap / Notes                                           |
| --- | ------------------------- | ------- | ----- | ----------------------------------------------------- |
| 8.1 | Add-on/extra definitions  | ✅      | ❌    | miniCal manages add-ons like breakfast, spa, parking. |
| 8.2 | Extra pricing             | ✅      | ❌    |                                                       |
| 8.3 | Add extras to bookings    | ✅      | ❌    |                                                       |
| 8.4 | Extra quantity management | ✅      | ❌    |                                                       |
| 8.5 | Extra variants            | ✅      | ❌    |                                                       |

---

## 9. Financial & Accounting

| #    | Feature                           | miniCal | Roost | Gap / Notes                                                                     |
| ---- | --------------------------------- | ------- | ----- | ------------------------------------------------------------------------------- |
| 9.1  | Chart of accounts                 | ❌      | ✅    | Roost has 20+ seeded accounts (assets, liabilities, equity, revenue, expenses). |
| 9.2  | Double-entry journal entries      | ❌      | ✅    | Roost enforces balanced debits = credits. miniCal has flat payment records.     |
| 9.3  | Revenue recognition               | ❌      | ✅    | Roost auto-creates journal entries on import.                                   |
| 9.4  | Expense management (categorized)  | ❌      | ✅    | 12 Schedule E-aligned categories.                                               |
| 9.5  | Bulk expense CSV import           | ❌      | ✅    |                                                                                 |
| 9.6  | Loan payment tracking (P&I split) | ❌      | ✅    |                                                                                 |
| 9.7  | Bank reconciliation               | ❌      | ✅    | Auto-match + manual confirm/reject.                                             |
| 9.8  | P&L report                        | 🔶      | ✅    | miniCal has ledger reports. Roost has full P&L with platform breakdown.         |
| 9.9  | Balance sheet                     | ❌      | ✅    |                                                                                 |
| 9.10 | Income statement                  | ❌      | ✅    |                                                                                 |
| 9.11 | Schedule E (tax) report           | ❌      | 🔶    | Stub in Roost.                                                                  |
| 9.12 | Account balances query            | ❌      | ✅    |                                                                                 |
| 9.13 | Expense attribution (per-owner)   | ❌      | ✅    | Roost tracks Jay / Minnie / Shared attribution.                                 |
| 9.14 | Daily/monthly ledger reports      | ✅      | ❌    | miniCal has traditional hotel ledger reports.                                   |
| 9.15 | Payment reports                   | ✅      | 🔶    | Roost has journal entry queries; no dedicated payment report view.              |
| 9.16 | Night audit process               | ✅      | ❌    | miniCal has formal night audit.                                                 |

---

## 10. Channel Management & OTA Integration

| #     | Feature                             | miniCal | Roost | Gap / Notes                                                            |
| ----- | ----------------------------------- | ------- | ----- | ---------------------------------------------------------------------- |
| 10.1  | Channel manager integration         | ✅      | ✅    | Both integrate via Channex.io.                                         |
| 10.2  | Availability sync / push            | ✅      | ✅    |                                                                        |
| 10.3  | Rate sync / push                    | ✅      | ✅    |                                                                        |
| 10.4  | Booking pull from channels          | ✅      | ✅    |                                                                        |
| 10.5  | Property mapping (local ↔ channel)  | ✅      | ✅    |                                                                        |
| 10.6  | Webhook-based booking receipt       | 🔶      | ✅    | Roost has full webhook handler with event dispatch.                    |
| 10.7  | Scheduled reservation sync          | 🔶      | ✅    | Roost: APScheduler every 15 min.                                       |
| 10.8  | Message sync via channel manager    | ❌      | ✅    | Roost syncs Channex messages every 30 min.                             |
| 10.9  | Review sync via channel manager     | ❌      | ✅    | Roost syncs reviews every 60 min.                                      |
| 10.10 | Review response via channel manager | ❌      | ✅    |                                                                        |
| 10.11 | Multiple OTA credential storage     | ✅      | 🔶    | miniCal stores per-channel credentials. Roost uses single Channex key. |

---

## 11. Data Ingestion & Import

| #    | Feature                         | miniCal | Roost | Gap / Notes                                        |
| ---- | ------------------------------- | ------- | ----- | -------------------------------------------------- |
| 11.1 | Airbnb CSV import               | ❌      | ✅    | Roost parses Airbnb transaction history.           |
| 11.2 | VRBO CSV import                 | ❌      | ✅    |                                                    |
| 11.3 | Expedia CSV import              | ❌      | ✅    |                                                    |
| 11.4 | RVshare manual entry            | ❌      | ✅    |                                                    |
| 11.5 | Bank statement import (Mercury) | ❌      | ✅    |                                                    |
| 11.6 | Import history tracking         | ❌      | ✅    | Counts of inserted/updated/skipped.                |
| 11.7 | Import idempotency (dedup)      | ❌      | ✅    | Unique constraint prevents re-import.              |
| 11.8 | Raw file archiving              | ❌      | ✅    | Original CSV saved for audit.                      |
| 11.9 | Database migration/seeding      | ✅      | ✅    | miniCal: SQL seed file. Roost: Alembic migrations. |

---

## 12. Reporting & Analytics

| #     | Feature                               | miniCal | Roost | Gap / Notes                                                      |
| ----- | ------------------------------------- | ------- | ----- | ---------------------------------------------------------------- |
| 12.1  | Daily ledger report                   | ✅      | ❌    |                                                                  |
| 12.2  | Monthly ledger report                 | ✅      | ❌    |                                                                  |
| 12.3  | MTD / YTD financial summary           | ✅      | ✅    | Roost dashboard has YTD revenue/expenses with YoY.               |
| 12.4  | Occupancy rate report                 | ✅      | ✅    | Both calculate occupancy %.                                      |
| 12.5  | Revenue by customer segment           | ✅      | 🔶    | miniCal: by customer type. Roost: by platform (Airbnb/VRBO/etc). |
| 12.6  | Employee action report                | ✅      | ❌    | miniCal tracks staff activity.                                   |
| 12.7  | Booking change log                    | ✅      | ❌    |                                                                  |
| 12.8  | Night audit logs                      | ✅      | ❌    |                                                                  |
| 12.9  | Housekeeping report                   | ✅      | 🔶    | Roost has task list with status; no formal housekeeping report.  |
| 12.10 | P&L report (multi-period)             | 🔶      | ✅    | Roost: month, quarter, year, YTD periods.                        |
| 12.11 | Balance sheet                         | ❌      | ✅    |                                                                  |
| 12.12 | Income statement (monthly drill-down) | ❌      | ✅    |                                                                  |
| 12.13 | Booking trend charts (12-month)       | ❌      | ✅    | Platform-colored line chart.                                     |
| 12.14 | YoY comparison (% change)             | ❌      | ✅    | Dashboard stat cards.                                            |

---

## 13. Communication & Guest Messaging

| #     | Feature                                   | miniCal | Roost | Gap / Notes                                                                               |
| ----- | ----------------------------------------- | ------- | ----- | ----------------------------------------------------------------------------------------- |
| 13.1  | Email template system                     | ✅      | ✅    | miniCal: email templates. Roost: Jinja2 message templates with triggers.                  |
| 13.2  | Booking confirmation email                | ✅      | 🔶    | Roost has template triggers but mainly for operator relay, not direct-to-guest auto-send. |
| 13.3  | Welcome messages                          | ❌      | ✅    | Roost: auto-prepared on VRBO/RVshare import.                                              |
| 13.4  | Pre-arrival messages (scheduled)          | ❌      | ✅    | APScheduler fires 2 days before check-in.                                                 |
| 13.5  | Triggered message templates (event-based) | ❌      | ✅    | booking_confirmed, check_in, check_out, review_request triggers.                          |
| 13.6  | Multi-channel delivery (Channex + email)  | ❌      | ✅    |                                                                                           |
| 13.7  | Template variable injection               | ❌      | ✅    | guest_name, property_name, wifi_password, lock_code, etc.                                 |
| 13.8  | Communication log tracking                | ❌      | ✅    | Per-booking message lifecycle.                                                            |
| 13.9  | Operator notification emails              | ❌      | ✅    | Emails with rendered message for copy-paste send.                                         |
| 13.10 | Direct guest email from system            | ✅      | ❌    | miniCal sends directly to guest. Roost notifies operator who sends manually.              |
| 13.11 | Invoice email to guest                    | ✅      | ❌    |                                                                                           |
| 13.12 | Email send logging                        | ✅      | ✅    |                                                                                           |

---

## 14. Unified Inbox & AI

| #    | Feature                             | miniCal | Roost | Gap / Notes                                     |
| ---- | ----------------------------------- | ------- | ----- | ----------------------------------------------- |
| 14.1 | Conversation threading (by booking) | ❌      | ✅    | Channex messages grouped by booking.            |
| 14.2 | Unified inbox across properties     | ❌      | ✅    |                                                 |
| 14.3 | Unread count / thread metrics       | ❌      | ✅    |                                                 |
| 14.4 | Reply to guest from inbox           | ❌      | ✅    | Sends via Channex API.                          |
| 14.5 | AI reply suggestions (LLM)          | ❌      | ✅    | Two-phase Ollama pipeline: SQL gen → narrative. |
| 14.6 | Natural language data query         | ❌      | ✅    | `POST /api/query/ask` with SSE streaming.       |

---

## 15. Task & Housekeeping Management

| #    | Feature                      | miniCal | Roost | Gap / Notes                                           |
| ---- | ---------------------------- | ------- | ----- | ----------------------------------------------------- |
| 15.1 | Housekeeping room status     | ✅      | ❌    | miniCal: room-level clean/dirty/maintenance.          |
| 15.2 | Cleaning task auto-creation  | ❌      | ✅    | Roost creates task on booking import (checkout date). |
| 15.3 | Task assignment to staff     | ❌      | ✅    | By name or email.                                     |
| 15.4 | Task status workflow         | ❌      | ✅    | pending → in_progress → completed / skipped.          |
| 15.5 | Task email notification      | ❌      | ✅    | SMTP notification on assignment.                      |
| 15.6 | Manual task creation         | ❌      | ✅    |                                                       |
| 15.7 | Room status quick-update     | ✅      | ❌    | miniCal has quick toggle on calendar.                 |
| 15.8 | Task date/property filtering | ❌      | ✅    |                                                       |

---

## 16. Online Booking Engine / Widget

| #     | Feature                      | miniCal | Roost | Gap / Notes                                                                                 |
| ----- | ---------------------------- | ------- | ----- | ------------------------------------------------------------------------------------------- |
| 16.1  | Public booking form          | ✅      | 🔶    | miniCal: full booking engine. Roost: inquiry widget only (no payment/confirmation flow).    |
| 16.2  | Real-time availability check | ✅      | 🔶    | Roost `GET /api/widget/{slug}/availability` checks bookings; miniCal checks room inventory. |
| 16.3  | Rate display to guest        | ✅      | ❌    | miniCal shows pricing. Roost widget has no rate display.                                    |
| 16.4  | Room type selection          | ✅      | ❌    |                                                                                             |
| 16.5  | Guest count input            | ✅      | ❌    |                                                                                             |
| 16.6  | Date picker (check-in/out)   | ✅      | 🔶    | Widget captures dates in inquiry.                                                           |
| 16.7  | Booking confirmation page    | ✅      | ❌    | miniCal shows confirmation after booking.                                                   |
| 16.8  | Custom form fields           | ✅      | ❌    |                                                                                             |
| 16.9  | Property info endpoint       | ❌      | ✅    | `GET /api/widget/{slug}/info` with guidebook sections.                                      |
| 16.10 | Inquiry reference generation | ❌      | ✅    | INQ-XXXXXXXX unique references.                                                             |

---

## 17. Compliance & Automation

| #    | Feature                                 | miniCal | Roost | Gap / Notes                            |
| ---- | --------------------------------------- | ------- | ----- | -------------------------------------- |
| 17.1 | PDF form auto-fill                      | ❌      | ✅    | pypdf-based resort form filling.       |
| 17.2 | Auto-submission to resort               | ❌      | ✅    | Threshold-based auto-submit.           |
| 17.3 | Submission status tracking              | ❌      | ✅    | pending → submitted → confirmed.       |
| 17.4 | Urgency flagging (approaching check-in) | ❌      | ✅    | Daily cron at 08:00 UTC.               |
| 17.5 | Manual approval workflow                | ❌      | ✅    | Operator approves pending submissions. |
| 17.6 | Batch processing                        | ❌      | ✅    | Process all pending at once.           |

---

## 18. Guidebook & Public Content

| #    | Feature                             | miniCal | Roost | Gap / Notes                                                        |
| ---- | ----------------------------------- | ------- | ----- | ------------------------------------------------------------------ |
| 18.1 | Digital guest guidebook             | ❌      | ✅    | Per-property, with sections (title, body, icon, order).            |
| 18.2 | Public guidebook URL (no auth)      | ❌      | ✅    | `/public/guide/{slug}` renders HTML.                               |
| 18.3 | Guidebook publish toggle            | ❌      | ✅    |                                                                    |
| 18.4 | Property slideshow / gallery images | ✅      | ❌    | miniCal manages image galleries.                                   |
| 18.5 | Property feature list / amenities   | ✅      | 🔶    | Roost has guidebook sections; miniCal has structured amenity list. |

---

## 19. Owner Portal

| #    | Feature                              | miniCal | Roost | Gap / Notes                                      |
| ---- | ------------------------------------ | ------- | ----- | ------------------------------------------------ |
| 19.1 | Owner portal (token-based, no login) | ❌      | ✅    | Opaque token grants read-only access.            |
| 19.2 | Owner revenue summary (12 months)    | ❌      | ✅    | Total revenue, booking count, nights, occupancy. |
| 19.3 | Owner booking list                   | ❌      | ✅    | Guest name, dates, amount per booking.           |
| 19.4 | Platform revenue breakdown           | ❌      | ✅    | Revenue by Airbnb/VRBO/etc.                      |
| 19.5 | Token CRUD (admin creates/revokes)   | ❌      | ✅    |                                                  |

---

## 20. User & Permission Management

| #    | Feature                            | miniCal | Roost | Gap / Notes                                                                      |
| ---- | ---------------------------------- | ------- | ----- | -------------------------------------------------------------------------------- |
| 20.1 | User registration / creation       | ✅      | ✅    |                                                                                  |
| 20.2 | Role-based access control          | ✅      | ✅    | miniCal: admin/manager/staff. Roost: admin/manager/housekeeper/owner/accountant. |
| 20.3 | Granular feature-level permissions | ✅      | ❌    | miniCal has per-feature toggles. Roost has role-based only.                      |
| 20.4 | Property-level access control      | ✅      | ❌    | miniCal restricts users to specific properties.                                  |
| 20.5 | User activity / action logs        | ✅      | ❌    | miniCal: employee action tracking.                                               |
| 20.6 | Login / session management         | ✅      | ✅    | miniCal: session-based. Roost: JWT (7-day).                                      |
| 20.7 | Password management                | ✅      | ✅    | Both hash passwords.                                                             |
| 20.8 | User deactivation (soft delete)    | ❌      | ✅    | Roost: `is_active` flag.                                                         |

---

## 21. Multi-Property Management

| #    | Feature                                        | miniCal | Roost | Gap / Notes                                                |
| ---- | ---------------------------------------------- | ------- | ----- | ---------------------------------------------------------- |
| 21.1 | Multiple property support                      | ✅      | ✅    | Both support multi-property.                               |
| 21.2 | Property switching UI                          | ✅      | ✅    | Roost: property selector in header. miniCal: company list. |
| 21.3 | Cross-property reporting                       | ✅      | ✅    | Roost: combined or per-property P&L mode.                  |
| 21.4 | Property branding (logo, images)               | ✅      | ❌    | miniCal manages logos/slideshows.                          |
| 21.5 | Property information (name, address, timezone) | ✅      | ✅    | Roost stores in config YAML per property.                  |
| 21.6 | Property tags / categorization                 | ✅      | ❌    |                                                            |

---

## 22. Settings & Configuration

| #     | Feature                            | miniCal | Roost | Gap / Notes                                                                    |
| ----- | ---------------------------------- | ------- | ----- | ------------------------------------------------------------------------------ |
| 22.1  | Hotel/property profile settings UI | ✅      | ❌    | miniCal has full settings UI. Roost uses config YAML files (no in-app editor). |
| 22.2  | Timezone configuration             | ✅      | ✅    |                                                                                |
| 22.3  | Currency configuration             | ✅      | ❌    | miniCal supports multi-currency.                                               |
| 22.4  | Booking source setup               | ✅      | ❌    | miniCal: admin-defined sources. Roost: hardcoded platforms.                    |
| 22.5  | Charge type setup                  | ✅      | ❌    | miniCal: define charge types with GL codes.                                    |
| 22.6  | Payment method setup               | ✅      | ❌    |                                                                                |
| 22.7  | Payment gateway configuration      | ✅      | ❌    |                                                                                |
| 22.8  | Tax configuration                  | ✅      | ❌    |                                                                                |
| 22.9  | Extension / plugin marketplace     | ✅      | ❌    | miniCal has installable extensions.                                            |
| 22.10 | In-app settings edit               | ✅      | ❌    | Roost requires YAML file edits.                                                |

---

## 23. API & Integration

| #     | Feature                   | miniCal | Roost | Gap / Notes                                                 |
| ----- | ------------------------- | ------- | ----- | ----------------------------------------------------------- |
| 23.1  | REST API (JSON)           | ✅      | ✅    | Both have full REST APIs.                                   |
| 23.2  | API authentication        | ✅      | ✅    | miniCal: API key. Roost: JWT Bearer token.                  |
| 23.3  | Booking CRUD API          | ✅      | ✅    |                                                             |
| 23.4  | Customer/guest API        | ✅      | ❌    | miniCal has dedicated customer API.                         |
| 23.5  | Room type / inventory API | ✅      | ❌    |                                                             |
| 23.6  | Rate plan API             | ✅      | ❌    |                                                             |
| 23.7  | Company/property info API | ✅      | ✅    | Roost: dashboard + widget endpoints.                        |
| 23.8  | Webhook receiving         | 🔶      | ✅    | Roost: Channex webhooks. miniCal: Channex integration.      |
| 23.9  | API versioning (v1, v2)   | ✅      | ❌    | miniCal has v1 and v2 API. Roost has unversioned endpoints. |
| 23.10 | SSE streaming endpoints   | ❌      | ✅    | AI query uses Server-Sent Events.                           |

---

## 24. Language & Internationalization

| #    | Feature                     | miniCal | Roost | Gap / Notes                                |
| ---- | --------------------------- | ------- | ----- | ------------------------------------------ |
| 24.1 | Multi-language support      | ✅      | ❌    | miniCal has full i18n with translation UI. |
| 24.2 | Language switching per user | ✅      | ❌    |                                            |
| 24.3 | Translation management UI   | ✅      | ❌    |                                            |
| 24.4 | Batch translation           | ✅      | ❌    |                                            |

---

## 25. Partners & White Label

| #    | Feature                  | miniCal | Roost | Gap / Notes                             |
| ---- | ------------------------ | ------- | ----- | --------------------------------------- |
| 25.1 | Partner management       | ✅      | ❌    | miniCal has reseller/partner structure. |
| 25.2 | White-label multi-tenant | ✅      | ❌    |                                         |
| 25.3 | Partner invitations      | ✅      | ❌    |                                         |

---

## 26. Night Audit & Daily Operations

| #    | Feature                     | miniCal | Roost | Gap / Notes                                                                       |
| ---- | --------------------------- | ------- | ----- | --------------------------------------------------------------------------------- |
| 26.1 | Night audit process         | ✅      | ❌    | miniCal: formal end-of-day with selling date advance.                             |
| 26.2 | Selling date management     | ✅      | ❌    | miniCal tracks business date separately from calendar date.                       |
| 26.3 | Audit trail / activity logs | ✅      | 🔶    | Roost: communication logs + import history. miniCal: comprehensive activity logs. |

---

## 27. Background Jobs & Automation

| #    | Feature                                                            | miniCal | Roost | Gap / Notes                      |
| ---- | ------------------------------------------------------------------ | ------- | ----- | -------------------------------- |
| 27.1 | Scheduled compliance checks                                        | ❌      | ✅    | Daily urgency cron.              |
| 27.2 | Pre-arrival message scheduling                                     | ❌      | ✅    | DateTrigger jobs.                |
| 27.3 | Periodic channel sync (reservations)                               | ❌      | ✅    | Every 15 min.                    |
| 27.4 | Periodic message sync                                              | ❌      | ✅    | Every 30 min.                    |
| 27.5 | Periodic review sync                                               | ❌      | ✅    | Every 60 min.                    |
| 27.6 | Background task processing (import → submit → recognize → message) | ❌      | ✅    | FastAPI BackgroundTask pipeline. |

---

## Summary: Feature Count

| Category              | miniCal Only | Roost Only | Both Have | Total Features |
| --------------------- | ------------ | ---------- | --------- | -------------- |
| Calendar & Booking UI | 6            | 0          | 2         | 8              |
| Booking Lifecycle     | 8            | 0          | 7         | 15             |
| Room & Inventory      | 11           | 0          | 3         | 14             |
| Rate & Pricing        | 9            | 0          | 1         | 10             |
| Guest/Customer CRM    | 9            | 0          | 1         | 10             |
| Payment & Invoice     | 14           | 0          | 0         | 14             |
| Tax Management        | 7            | 0          | 0         | 7              |
| Extras & Add-ons      | 5            | 0          | 0         | 5              |
| Accounting            | 2            | 11         | 1         | 14             |
| Channel Management    | 1            | 5          | 5         | 11             |
| Data Ingestion        | 0            | 8          | 1         | 9              |
| Reporting             | 5            | 4          | 3         | 12             |
| Communication         | 3            | 8          | 1         | 12             |
| Inbox & AI            | 0            | 6          | 0         | 6              |
| Task Management       | 2            | 5          | 1         | 8              |
| Booking Engine/Widget | 5            | 2          | 3         | 10             |
| Compliance            | 0            | 6          | 0         | 6              |
| Guidebook             | 2            | 3          | 0         | 5              |
| Owner Portal          | 0            | 5          | 0         | 5              |
| User Management       | 3            | 1          | 4         | 8              |
| Multi-Property        | 2            | 0          | 4         | 6              |
| Settings & Config     | 9            | 0          | 1         | 10             |
| API                   | 4            | 1          | 4         | 9              |
| i18n                  | 4            | 0          | 0         | 4              |
| Partners              | 3            | 0          | 0         | 3              |
| Night Audit           | 3            | 0          | 0         | 3              |
| Background Jobs       | 0            | 6          | 0         | 6              |
| **TOTAL**             | **~117**     | **~71**    | **~42**   | **~230**       |

---

## Priority Replication Roadmap

### Phase 1 — Core Hotel PMS (Highest Impact)

These are miniCal features that Roost lacks and are essential for a hotel/PMS:

1. **Room entity model** (3.1–3.4) — Add rooms within properties, room types, floor/building
2. **Room status tracking** (3.5–3.7) — Clean/dirty/maintenance/OOO states
3. **Booking state machine** (2.3–2.4) — Reservation → Check-in → In-house → Check-out
4. **Guest profile CRM** (5.1–5.10) — Unified guest database, search, history, auto-fill
5. **Interactive calendar** (1.2–1.3, 1.5) — Drag-drop, resize, room-row layout
6. **Rate management** (4.1–4.7) — Rate plans, dynamic pricing, seasonal/occupancy-based

### Phase 2 — Financial Operations

7. **Invoice system** (6.5–6.10) — Per-booking invoices, sequential numbering, guest-facing links
8. **Payment processing** (6.1–6.4) — Gateway integration, multiple methods, tokenization
9. **Folio & charges** (6.11–6.14) — Room charges, extras, service charges
10. **Tax engine** (7.1–7.7) — Tax types, rates, brackets, auto-calculation
11. **Night audit** (26.1–26.2) — End-of-day process, selling date

### Phase 3 — Booking Engine & Guest Experience

12. **Full booking engine** (16.1–16.8) — Public booking with rates, availability, confirmation
13. **Extras management** (8.1–8.5) — Add-ons, pricing, attached to bookings
14. **Guest count tracking** (2.7) — Adults + children per booking
15. **Custom fields** (2.2, 5.6) — Admin-defined booking and customer fields

### Phase 4 — Operations & Administration

16. **Granular permissions** (20.3–20.4) — Feature-level + property-level access
17. **Activity audit log** (20.5, 2.10, 26.3) — Staff actions, booking changes, login logs
18. **Settings UI** (22.1–22.10) — In-app configuration editor
19. **Property branding** (21.4, 18.4) — Logo, gallery, slideshow management

### Phase 5 — Expansion

20. **Multi-currency** (4.9, 22.3) — Currency support
21. **i18n** (24.1–24.4) — Multi-language with translation management
22. **Partner / white-label** (25.1–25.3) — Reseller structure
23. **API versioning** (23.9) — v1/v2 API structure
24. **Extension marketplace** (22.9) — Plugin system

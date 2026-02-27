# VRBO Payments Report CSV Notes

## Source

**Synthetic — headers MEDIUM confidence (from official VRBO help documentation)**

No real VRBO Payments Report CSV export was available at the time this fixture was created (2026-02-27).
The headers are taken from the official VRBO help article at https://help.vrbo.com/articles/How-do-I-read-my-payments-report,
which lists all 29 columns explicitly.

## Column Headers Used

```
RefID, Payout ID, Reservation ID, Check In/Check Out, Number of Nights,
Source, Subscription Model, Payment Date, Disbursement Date, Payment Type,
Property ID, Guest Name, Payment Method, Taxable Revenue, Non-Taxable Revenue,
Guest Payment, Your Revenue, Payable To You, Tax, Service Fee, Currency,
Commission, VAT on Commission, Payment Processing Fee, Deposit Amount,
Stay Tax We Remit, Stay Tax You Remit, Refundable Deposit, Payout
```

Total: 29 columns (matches VRBO documentation exactly)

## Key Findings

- **Reservation ID:** Format "HA-XXXXXXXX" — used as stable booking identifier (confirmed from VRBO docs)
- **Property ID:** Numeric ID (e.g., "87654321") — maps to VRBO's internal property identifier
- **Check In/Check Out:** Single column with date range "MM/DD/YYYY - MM/DD/YYYY" (assumed format, must verify)
- **Payable To You:** Net payout to property owner after all fees
- **Multi-row payouts:** Same Reservation ID appears on multiple rows for different payment types (e.g., Rental Payment + Pet Fee, Rental Payment + Cleaning Fee)

## What Must Be Verified

Before this adapter ships to production, export a real VRBO Payments Report and confirm:

1. **Exact column header names** — MEDIUM confidence from docs; may differ in actual export
2. **Check In/Check Out format** — assumed "MM/DD/YYYY - MM/DD/YYYY"; actual separator may differ
3. **Reservation ID format** — assumed "HA-XXXXXXXX"; confirm prefix and zero-padding
4. **Property ID format** — confirm whether it is numeric or alphanumeric
5. **Payable To You format** — confirm no currency symbols or special characters in actual export
6. **Multi-row grouping behavior** — confirm same Reservation ID appears across multiple rows

## How to Get a Real Export

1. Log in to the VRBO owner dashboard
2. Navigate to Payments > Payments Report
3. Set date range and click "Download CSV"
4. Replace this file with the real export (redact guest PII before committing)

## Update Protocol

When a real export is obtained:
1. Replace this file with real data (with PII redacted: replace guest names with "Guest A", "Guest B", etc.)
2. Update constants in `app/ingestion/adapters/vrbo.py` if headers differ
3. Update this notes file: change "Source" to "Real export" and record verification date

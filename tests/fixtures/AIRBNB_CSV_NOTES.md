# Airbnb Transaction History CSV Notes

## Source

**Synthetic — headers UNVERIFIED**

No real Airbnb Transaction History CSV export was available at the time this fixture was created (2026-02-27).
The headers and data are based on community forum posts, third-party tool integrations, and research notes
in `.planning/phases/02-data-ingestion/02-RESEARCH.md`.

## Column Headers Used

```
Date, Type, Confirmation Code, Listing, Guest, Details, Reference, Currency,
Amount, Paid Out, Host Fee, Cleaning Fee
```

## Key Findings

- **Date format:** MM/DD/YYYY (US format, non-ISO)
- **Amount format:** Apostrophe-prefixed (e.g., `'$180.00`), confirmed Airbnb quirk
- **Negative amounts:** Apostrophe + minus inside quotes (e.g., `'-$15.50`)
- **Multi-row events:** Multiple rows per Confirmation Code (Reservation, Payout, Host Fee, Adjustment)
- **Guest field:** Only present on Reservation rows; blank on Payout/Fee rows
- **Multi-property:** Two listings present (Jay's Beach House, Minnie's Tiny House)

## What Must Be Verified

Before this adapter ships to production, export a real Airbnb Transaction History CSV and confirm:

1. **Exact column header names** — especially "Guest" (may be "Guest Name"), "Listing" (may be "Listing Title")
2. **Date format** — MM/DD/YYYY vs M/D/YY vs other
3. **Amount format** — whether apostrophe prefix is always present or only in some exports
4. **Negative amounts** — exact format for fees and adjustments
5. **All row types** — complete set of "Type" field values

## How to Get a Real Export

1. Log in to Airbnb host dashboard
2. Navigate to Earnings → Transaction History
3. Set date range and click "Download CSV"
4. Replace this file with the real export (redact guest PII before committing)

## Update Protocol

When a real export is obtained:
1. Replace this file with real data (with PII redacted: replace guest names with "Guest A", "Guest B", etc.)
2. Update constants in `app/ingestion/adapters/airbnb.py` if headers differ
3. Update this notes file: change "Source" to "Real export" and record verification date

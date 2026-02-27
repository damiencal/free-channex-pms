# Mercury Bank CSV Notes

## Source

**VERIFIED — confirmed against real Mercury bank transaction CSV export (2026-02-27)**

Export: Beachcomber RV Retreats LLC, Mercury Checking xx0170, transactions to 2026-01-30.

## Column Headers (Verified)

```
Date (UTC), Description, Amount, Status, Source Account, Bank Description, Reference,
Note, Last Four Digits, Name On Card, Mercury Category, Category, GL Code, Timestamp,
Original Currency, Check Number, Tags, Cardholder Email, Tracking ID
```

**Required headers** (what the adapter validates):
```
Date (UTC), Description, Amount, Tracking ID
```

## Key Findings

- **Date format:** `MM-DD-YYYY` with dashes (e.g., `01-29-2026`) — NOT slashes
- **Column name:** `Date (UTC)` — NOT just `Date`
- **Native transaction ID:** `Tracking ID` column present — stable bank-assigned ID
  (e.g., `111000027183610`). Composite hash dedup is no longer needed.
- **Amount convention:** All values are positive in this export; sign not determined from
  Amount column alone. `Status` column shows "Sent" for all observed rows (both incoming
  ACH deposits and outgoing transfers). Phase 3 accounting engine handles debit/credit classification.
- **No currency symbols or commas** in Amount column — plain decimal values.

## Transaction ID Strategy

**Native `Tracking ID` column** — bank-assigned, stable across re-exports.
The adapter prefixes with `"mercury-"` to avoid collisions with other platform IDs.
Example: `"mercury-111000027183610"`

## Amount Convention Note

Observed: Airbnb payout deposits (incoming) and bank transfers (outgoing) both show as
positive amounts with `Status: Sent`. Until a debit transaction appears for comparison,
treat all amounts as positive and let the accounting engine (Phase 3) classify direction
from the `Description` or `Bank Description` columns.

# Airbnb Transaction History CSV Notes

## Source

**VERIFIED — confirmed against real Airbnb exports (2026-02-27)**

Two real CSV exports were inspected:
- `airbnb_.csv` — Transaction History (completed stays + payouts)
- `airbnb_pending.csv` — Pending stays (future/upcoming reservations only)

## Column Headers (Verified)

**Transaction History format** (completed stays):
```
Date, Arriving by date, Type, Confirmation code, Booking date, Start date, End date,
Nights, Guest, Listing, Details, Reference code, Currency, Amount, Paid out,
Service fee, Fast pay fee, Cleaning fee, Gross earnings, Occupancy taxes, Earnings year
```

**Pending stays format** (future reservations):
```
Date, Type, Confirmation code, Booking date, Start date, End date, Nights, Guest,
Listing, Details, Reference code, Currency, Amount, Service fee, Cleaning fee,
Gross earnings, Occupancy taxes, Earnings year
```

**Minimum required headers** (present in both formats — what the adapter validates):
```
Date, Type, Confirmation code, Listing, Amount
```

## Key Findings

- **Date format:** MM/DD/YYYY (e.g., `01/28/2026`) — confirmed
- **Amount format:** Plain decimal (e.g., `998.13`) — no apostrophe prefix in real exports
  (apostrophe handling kept in adapter for safety; harmless if absent)
- **Case matters:** `Confirmation code` (lowercase 'c'), `Start date` (lowercase 'd'), `End date` (lowercase 'd')
- **Payout rows:** Have empty `Confirmation code`, `Guest`, `Start date`, `End date`, `Amount`.
  These are skipped automatically by the adapter (empty confirmation code check).
- **Net amount:** `Amount` column on Reservation rows is the net host payout (after Airbnb fee).
  `Gross earnings` is the full booking amount before fees.
- **Listing names confirmed:**
  - Jay: `"Jay 2BR RV near Sanibel Island & Fort Myers Beach"`
  - Minnie: `"Minnie RV near Sanibel Island and Fort Myers Beach"`

## Row Types Observed

| Type | Has Confirmation code | Has Amount | Notes |
|------|----------------------|------------|-------|
| Reservation | Yes | Yes (net amount) | Primary booking row |
| Payout | No | No (`Paid out` column has value) | Skipped by adapter |

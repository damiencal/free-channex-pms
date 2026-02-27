# Mercury Bank CSV Notes

## Source

**Synthetic — UNVERIFIED, LOW confidence**

No real Mercury bank CSV export was found on disk during plan 02-05 execution (searched
~/Downloads and common locations). The sample CSV uses a best-guess format based on
research notes in 02-RESEARCH.md (Mercury generic CSV section).

**Before deploying the Mercury adapter to production, export a real Mercury transaction CSV
and verify the column names match REQUIRED_HEADERS in app/ingestion/adapters/mercury.py.**

## Export Path in Mercury

Mercury dashboard > Accounts > [Account Name] > Transactions > Export (CSV button,
top-right of the transaction list). Download the generic CSV (not QuickBooks or NetSuite
format, which use different column names).

## Column Headers (assumed)

```
Date, Description, Amount, Running Balance, Category, Account, Bank Name
```

These match the "Mercury generic CSV likely columns" from 02-RESEARCH.md (LOW confidence).

The adapter's `REQUIRED_HEADERS` frozenset only requires `Date`, `Description`, and `Amount`
(the three fields needed to produce a BankTransactionRecord). Additional columns such as
`Running Balance`, `Category`, `Account`, and `Bank Name` are ignored.

## Transaction ID / Deduplication Strategy

**Strategy: Composite key (Date + Amount + Description hash)**

A native transaction ID column was **not observed** in the assumed Mercury generic CSV
format. Mercury's QuickBooks and NetSuite CSV formats may include an ID column, but the
generic export does not appear to.

The composite key is generated as:
```
"mercury-" + sha256(f"{date}|{amount}|{description}").hexdigest()[:16]
```

This key is stable across re-imports as long as the date, amount, and description do not
change. If Mercury ever updates a transaction's description (rare), the composite key will
change and the old record will be orphaned.

**To switch to native ID if available:**
1. Confirm the column name in the real export (e.g., "Transaction ID" or "ID")
2. Set `COL_TRANSACTION_ID` in mercury.py constants section
3. Update `_generate_transaction_id()` to read from that column directly

## Date Format

Assumed: `MM/DD/YYYY` (US format, e.g., `01/15/2025`)

The adapter tries multiple formats: `%m/%d/%Y`, `%-m/%-d/%Y`, then ISO `%Y-%m-%d`.

## Amount Convention

Positive values = credits (money coming in).
Negative values = debits (money going out).
No currency symbols or commas in the assumed format.

If the real Mercury export includes `$` symbols or commas (e.g., `$1,234.56`), the adapter
strips them before parsing (see `_parse_amount()` in mercury.py).

## Verification Checklist

When a real Mercury CSV is obtained, verify:

- [ ] Column headers match REQUIRED_HEADERS = {"Date", "Description", "Amount"}
- [ ] Date format matches expected format (MM/DD/YYYY)
- [ ] Amount column: positive = credit, negative = debit (no $ or commas?)
- [ ] Is there a native transaction ID column? If yes, update COL_TRANSACTION_ID constant
- [ ] Are there any rows with null/empty amounts or dates?
- [ ] Does Running Balance column exist (optional, ignored by adapter)?

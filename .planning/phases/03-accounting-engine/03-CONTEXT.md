# Phase 3: Accounting Engine - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Record every booking and bank transaction as double-entry journal entries, with platform payouts reconciled against Mercury bank deposits. Track categorized expenses and loan payments. Reporting and dashboard views of this data are Phase 4 and Phase 7 concerns — this phase builds the ledger engine and its API.

</domain>

<decisions>
## Implementation Decisions

### Chart of Accounts

- **Revenue**: Single "Rental Income" account — not split per platform; platform breakdown lives in the booking records
- **Fee model**: Gross revenue + platform fee expense — record full booking amount as Rental Income, platform fee (e.g., 15.5% Airbnb host-only fee) as a separate "Platform Fees" expense line
- **Discounts**: Promotional discounts tracked as a contra-revenue account ("Promotional Discounts") so gross and net revenue are both visible; data availability in CSV imports to be confirmed during research
- **Loans**: Loan liability accounts required — one or more loans exist; payments split into principal reduction and interest expense (Schedule E line: Non-mortgage interest for RV/working capital loans)

### Revenue Recognition

- **Timing**: At payout release — revenue recognized when the platform pays out (Airbnb payout typically occurs on check-in day)
- **Airbnb multi-row events**: Deferred-then-recognized pattern — booking creation row creates an Unearned Revenue liability entry; payout row converts it to recognized Rental Income
- **Cancellation reversals**: Reversal journal entries — post offsetting debit/credit to undo original entry; both entries remain visible in history for audit trail
- **Adjustments**: Per-event journal entries — each adjustment row (credit, clawback, correction) produces its own journal entry against the original booking

### Reconciliation Matching Rules

- **Match criteria**: Exact amount + date window — payout and bank deposit must be the same dollar amount and the deposit must fall within 7 days of the payout date
- **Ambiguous matches**: Flag as "needs review" — when multiple payouts could match one deposit (same amount, same window), neither is auto-matched; operator confirms
- **Unmatched deposits**: Leave in unreconciled queue — bank deposits with no matching platform payout remain in the queue until manually categorized (covers Zelle, direct payments, non-rental income)

### Expense Categories

Full list of required Schedule E-aligned categories:
- Repairs & maintenance
- Supplies (consumables, toiletries, linens)
- Utilities (electric, water, internet)
- Non-mortgage interest (RV loans and working capital loans)
- Owner-reimbursable expenses (owner paid business expense personally — creates liability that clears when owner is repaid)
- Advertising
- Travel & transportation
- Professional services
- Legal
- Insurance
- Resort lot rental fees
- Cleaning service fees

### Expense Attribution & Entry

- **Property attribution**: Each expense entry specifies Jay, Minnie, or Shared — shared expenses are not auto-split; reports show per-property and combined views
- **Entry methods**: Both single-entry (POST endpoint per expense) and bulk CSV import — sufficient for manual API use and spreadsheet migration

### Claude's Discretion

- Exact account numbering scheme (e.g., 1000s for assets, 4000s for revenue, 5000s for expenses)
- Internal bookkeeping of the Unearned Revenue → Rental Income conversion mechanics
- Idempotency key structure for journal entries
- Bulk CSV import column schema (researcher to define based on expense fields)

</decisions>

<specifics>
## Specific Ideas

- Discount tracking is motivated by marketing analysis: want to see how much platform discounts reduced potential revenue and whether they drove bookings worth the discount
- Blocker to verify before coding fee attribution: Airbnb changed fee model in October 2025 to host-only fee at 15.5% — must confirm which model applies to this account before wiring the fee calculation into revenue recognition logic

</specifics>

<deferred>
## Deferred Ideas

- **Projected revenue from future bookings** — user wants to see forward-looking revenue based on confirmed future reservations; this is a read query against the bookings table, not a ledger concern; defer to Phase 4 reports or Phase 7 dashboard
- **Mortgage interest tracking** — user's loans are non-mortgage (RV/working capital); standard mortgage interest (Schedule E line 12) not currently needed but account scaffold could be added later

</deferred>

---

*Phase: 03-accounting-engine*
*Context gathered: 2026-02-27*

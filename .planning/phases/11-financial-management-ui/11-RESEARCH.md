# Phase 11: Financial Management UI - Research

**Researched:** 2026-03-01
**Domain:** React/shadcn/ui frontend extending existing dashboard; bank transaction categorization table; expense/loan entry form; split-panel reconciliation workflow
**Confidence:** HIGH — all findings verified against actual project source files and installed node_modules

---

## Summary

Phase 11 is a pure frontend phase that adds a new "Finance" top-level tab to the existing dashboard. All backend APIs already exist from Phases 3-4. The work is exclusively UI: wiring the existing accounting endpoints to interactive components. No new npm packages are needed — the full component toolkit (shadcn/ui, TanStack Query, Zustand, Radix primitives) is installed and in use.

The standard stack is already established: React 19, Vite 7, shadcn/ui with Tailwind v4, TanStack Query v5, Zustand v5, react-router-dom v7. Eleven shadcn/ui components are already installed (`tabs`, `badge`, `card`, `button`, `select`, `skeleton`, `tooltip`, `alert`, `separator`, `input`, `label`). The `Checkbox` and `ScrollArea` primitives are available from the installed `radix-ui` monorepo package — no npm install needed.

Three significant API gaps were found that the planner must address as early tasks:
1. The unreconciled queue endpoint (`GET /api/accounting/reconciliation/unreconciled`) does not return auto-matched items pending confirmation. Auto-matched bookings/deposits transition to `status="matched"` but the endpoint only queries for `status="unmatched"`. A backend fix or a new endpoint is required so the UI can show suggested matches for approval.
2. The "needs_review" deposits in the unreconciled queue do not include their candidate bookings (the algorithm computes candidates at runtime but doesn't persist them). The UI will need to derive candidates client-side from the `unmatched_payouts` list by matching amount.
3. The Finance tab badge requires a count of uncategorized transactions + auto-matched-but-unconfirmed items. Neither count is available from a single fast endpoint. A new `GET /api/accounting/finance-badge` endpoint or an extension of an existing one is needed.

**Primary recommendation:** Add Finance tab to AppShell first (trivial — one line change to `VALID_TABS` and one `TabsTrigger`), then build sub-tabs in order: Transactions (most self-contained), Expenses & Loans (form), Reconciliation (most complex). Fix API gaps in the same task as the component that needs them.

---

## Standard Stack

### Core (All Already Installed — Zero New npm Packages)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| React | ^19.2.0 | UI framework | In use |
| Vite | ^7.3.1 | Build tool | In use |
| shadcn/ui components | (CLI) | Table, form, badge primitives | Partially in use; need `checkbox.tsx` wrapper |
| Tailwind CSS v4 | ^4.2.1 | Styling | In use |
| TypeScript | ~5.9.3 | Type safety | In use |
| @tanstack/react-query | ^5.90.21 | Server state + mutations | In use |
| zustand | ^5.0.11 | Global property selector | In use |
| react-router-dom | ^7.13.1 | Tab URL sync | In use |
| radix-ui | ^1.4.3 | UI primitives | In use; exports Checkbox, ScrollArea |
| lucide-react | ^0.575.0 | Icons | In use |

### New UI Component Wrappers Needed (No New npm Packages)

| Component | Source Primitive | File to Create | Why Needed |
|-----------|-----------------|----------------|------------|
| `checkbox.tsx` | `import { Checkbox } from "radix-ui"` | `src/components/ui/checkbox.tsx` | Row selection in transaction table |
| `scroll-area.tsx` | `import { ScrollArea } from "radix-ui"` | `src/components/ui/scroll-area.tsx` | Scrollable panels in reconciliation |

Both primitives are verified present in `frontend/node_modules/radix-ui/dist/index.d.ts`.

**Installation:** None required.

---

## Backend APIs Available

All endpoints are under `/api/accounting/` and use `apiFetch` (the `/api` prefix is handled by `apiFetch()`).

### Transaction Categorization

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /api/accounting/bank-transactions` | GET | List transactions; supports `categorized` ("true"/"false"/"all"), `start_date`, `end_date`, `limit`, `offset` |
| `PATCH /api/accounting/bank-transactions/{id}/category` | PATCH | Single transaction categorization (auto-save pattern) |
| `PATCH /api/accounting/bank-transactions/categorize` | PATCH | Bulk categorize (for multi-select toolbar) |

**Request body for single categorization:**
```typescript
// PATCH /api/accounting/bank-transactions/{id}/category
interface SingleCategoryRequest {
  category: string        // one of ALL_CATEGORIES
  property_id?: number    // required for expense categories
  attribution?: string    // "jay" | "minnie" | "shared" — required for expense categories
}
// Returns: BankTransactionResponse
```

**BankTransactionResponse shape:**
```typescript
interface BankTransactionResponse {
  id: number
  transaction_id: string
  date: string        // ISO date
  description: string | null
  amount: string      // Decimal as string e.g. "123.45"
  reconciliation_status: string
  category: string | null
  journal_entry_id: number | null
}
```

**Category values (from source code — verified):**
```typescript
// Expense categories (require attribution + property_id):
const EXPENSE_CATEGORIES = [
  "repairs_maintenance", "supplies", "utilities",
  "non_mortgage_interest", "owner_reimbursable", "advertising",
  "travel_transportation", "professional_services", "legal",
  "insurance", "resort_lot_rental", "cleaning_service",
]

// Non-expense categories (no attribution needed):
const NON_EXPENSE_CATEGORIES = [
  "owner_deposit", "loan_payment", "transfer", "personal",
]

const ALL_CATEGORIES = [...EXPENSE_CATEGORIES, ...NON_EXPENSE_CATEGORIES]
```

**CRITICAL: Category assignment UX complexity.** Assigning an expense category requires `attribution` (jay/minnie/shared) and optionally `property_id`. The auto-save dropdown pattern works for non-expense categories but must show a secondary prompt (attribution selector) for expense categories before saving. This is the main UX complexity in the Transactions sub-tab.

### Expense & Loan Entry

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /api/accounting/expenses` | POST (201) | Record single expense |
| `GET /api/accounting/loans` | GET | List loans with current balances |
| `POST /api/accounting/loans/payments` | POST (201) | Record loan payment with P&I split |

**ExpenseRequest body:**
```typescript
interface ExpenseRequest {
  expense_date: string    // ISO date
  amount: string          // Decimal
  category: string        // EXPENSE_CATEGORIES only
  description: string
  attribution: string     // "jay" | "minnie" | "shared"
  property_id?: number    // optional — required per context decision
  vendor?: string         // optional
}
```

**LoanPaymentRequest body:**
```typescript
interface LoanPaymentRequest {
  loan_id: number
  principal: string       // Decimal
  interest: string        // Decimal
  payment_date: string    // ISO date
  payment_ref: string     // e.g., "2026-01" (user-supplied month reference)
}
```

**LoanResponse shape (for dropdown population):**
```typescript
interface LoanResponse {
  id: number
  name: string              // e.g., "Mortgage - Jay"
  account_id: number
  original_balance: string  // Decimal as string
  interest_rate: string     // Decimal as string
  start_date: string        // ISO date
  current_balance: string   // Decimal as string — computed dynamically
}
```

**Loan payment returns idempotent skip:** If same `payment_ref` was already recorded for a loan, the endpoint returns `{"status": "skipped", "journal_entry_id": null}`. The UI should handle both "recorded" and "skipped" in the success state.

### Reconciliation

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /api/accounting/reconciliation/unreconciled` | GET | Unreconciled queue (see gap below) |
| `POST /api/accounting/reconciliation/run` | POST | Trigger batch reconciliation |
| `POST /api/accounting/reconciliation/confirm` | POST | Confirm a match |
| `POST /api/accounting/reconciliation/reject/{match_id}` | POST | Reject a match |

**UnreconciledResponse shape:**
```typescript
interface UnreconciledResponse {
  unmatched_payouts: Array<{
    id: number
    platform: string
    guest_name: string
    check_in_date: string | null
    net_amount: string
  }>
  unmatched_deposits: Array<{
    id: number
    date: string | null
    amount: string
    description: string | null
  }>
  needs_review: Array<{
    id: number
    date: string | null
    amount: string
    description: string | null
  }>
}
```

**MatchConfirmRequest body:**
```typescript
interface MatchConfirmRequest {
  booking_id: number
  bank_transaction_id: number
  confirmed_by?: string   // default "operator"
}
```

---

## API Gaps (Backend Work Required)

### Gap 1: Auto-Matched Items Not Exposed for Confirmation (CRITICAL)

**Problem:** When `POST /api/accounting/reconciliation/run` runs, auto-matched bookings/deposits have their `reconciliation_status` set to `"matched"` (not `"unmatched"`). The `GET /api/accounting/reconciliation/unreconciled` endpoint queries `WHERE reconciliation_status = "unmatched"` — it does NOT return auto-matched items.

**What the context requires:** "All suggested matches require user approval — nothing is reconciled until the user clicks Confirm."

**Gap:** Auto-matched items are in a `"matched"` limbo state that isn't visible to the user. The UI cannot show them for confirmation.

**Fix required:** Extend `GET /api/accounting/reconciliation/unreconciled` to also return auto-matched `ReconciliationMatch` records (those with `status="matched"`, not yet `"confirmed"`). Add a new key `"pending_confirmation"` to the response with both sides (booking + deposit data) so the UI can display them.

**Suggested endpoint change:**
```python
# Add to get_unreconciled():
pending_matches = (
    db.query(ReconciliationMatch, Booking, BankTransaction)
    .join(Booking, Booking.id == ReconciliationMatch.booking_id)
    .join(BankTransaction, BankTransaction.id == ReconciliationMatch.bank_transaction_id)
    .filter(ReconciliationMatch.status == "matched")  # auto-matched, awaiting confirmation
    .all()
)
```

### Gap 2: Needs-Review Candidates Not Persisted

**Problem:** "Needs review" deposits have `reconciliation_status="needs_review"` but no associated candidate bookings stored. The reconciliation algorithm computed candidates in memory but didn't persist which bookings were candidates for each ambiguous deposit.

**What the context requires:** "'Needs review' deposits show candidate list; user picks the correct booking and confirms."

**Fix required (two options):**
1. **Backend option (preferred):** Add a `reconciliation_candidates` table or JSON field to store which booking_ids were candidates for each needs_review deposit when `run_reconciliation()` runs.
2. **Frontend option (simpler, good enough):** When showing a "needs_review" deposit in the UI, display all `unmatched_payouts` with the same amount as candidate options. The operator picks the right booking. This works because the algorithm flags "needs review" precisely when multiple bookings match the same amount — so filtering `unmatched_payouts` by matching `net_amount` to the deposit's `amount` will reproduce the candidate list client-side.

**Recommendation:** Use the frontend option (client-side filtering) — it requires no backend change, and the algorithm's "multiple candidates" condition means the candidates are always visible in `unmatched_payouts`.

### Gap 3: Finance Tab Badge Count

**Problem:** The Finance tab badge needs "combined count of uncategorized transactions + unreconciled items." No single endpoint provides this count efficiently. The bank-transactions endpoint doesn't return total counts (only paginated items).

**Fix required:** Add `GET /api/accounting/finance-summary` endpoint (or extend an existing endpoint) that returns:
```python
{
  "uncategorized_count": int,   # BankTransaction WHERE category IS NULL
  "unreconciled_count": int,    # pending_confirmation + needs_review + unmatched_payouts
}
```

This is a lightweight aggregation query (two COUNT() queries). The finance badge in AppShell should call this endpoint the same way it calls `/api/dashboard/actions` for the Actions badge.

---

## Architecture Patterns

### Recommended Project Structure

```
src/components/
├── finance/                          # NEW — all Finance tab components
│   ├── FinanceTab.tsx                # NEW — top-level Finance tab (sub-tabs container)
│   ├── TransactionsTab.tsx           # NEW — transaction categorization table
│   ├── ExpensesLoansTab.tsx          # NEW — expense/loan entry form
│   ├── ReconciliationTab.tsx         # NEW — split-panel reconciliation
│   ├── TransactionRow.tsx            # NEW — single row in transaction table
│   ├── CategorySelect.tsx            # NEW — category dropdown + attribution prompt
│   ├── BulkActionToolbar.tsx         # NEW — appears above table when rows selected
│   ├── TransactionFilters.tsx        # NEW — category/date range/amount filters
│   ├── ExpenseLoanForm.tsx           # NEW — togglable expense vs loan form
│   ├── ReconciliationPanel.tsx       # NEW — left or right panel (payouts / deposits)
│   └── MatchCandidateList.tsx        # NEW — booking candidate list for needs_review
│
└── ui/
    ├── checkbox.tsx                  # NEW — Radix Checkbox wrapper (no npm install)
    └── scroll-area.tsx               # NEW — Radix ScrollArea wrapper (no npm install)

src/hooks/
├── useTransactions.ts                # NEW — GET /api/accounting/bank-transactions
├── useExpenses.ts                    # NEW — POST /api/accounting/expenses
├── useLoans.ts                       # NEW — GET /api/accounting/loans
├── useLoanPayment.ts                 # NEW — POST /api/accounting/loans/payments
├── useReconciliation.ts              # NEW — GET + POST reconciliation endpoints
└── useFinanceSummary.ts              # NEW — GET /api/accounting/finance-summary (badge)

src/api/
└── finance.ts                        # NEW — all finance-related apiFetch wrappers
```

### Pattern 1: Finance Tab as Top-Level Tab with Sub-tabs

**What:** `AppShell.tsx` currently handles top-level tabs as `VALID_TABS`. Add "finance" to this list. The `FinanceTab.tsx` component renders its own `Tabs` instance with sub-tabs (transactions, expenses-loans, reconciliation).

**Sub-tab URL sync:** Use a second search param key (e.g., `?tab=finance&ftab=transactions`) for Finance sub-tab deep linking. This follows the same `useSearchParams` pattern from Phase 7.

```typescript
// src/components/layout/AppShell.tsx — modifications
type TabValue = 'home' | 'calendar' | 'reports' | 'actions' | 'query' | 'finance'
const VALID_TABS: TabValue[] = ['home', 'calendar', 'reports', 'actions', 'query', 'finance']

// In TabsList — add Finance trigger with badge
<TabsTrigger value="finance" className="gap-2">
  Finance
  {financeBadgeCount > 0 && (
    <Badge variant="destructive" className="h-5 min-w-5 text-xs px-1.5">
      {financeBadgeCount}
    </Badge>
  )}
</TabsTrigger>

// In TabsContent
<TabsContent value="finance">
  <FinanceTab />
</TabsContent>
```

**Finance badge count:** Query `GET /api/accounting/finance-summary` in AppShell alongside the existing `actions` query. The `finance-summary` endpoint (new backend) returns `{ uncategorized_count, unreconciled_count }`. Sum them for the badge. Use `selectedPropertyId` in the query key so it refetches on property change.

### Pattern 2: Transaction Table with Auto-Save Category

**What:** Dense table of bank transactions. Each row has a category `Select` dropdown. Picking a category immediately fires a PATCH to the backend. Brief visual confirmation (checkmark flash using `useState` with `setTimeout` reset).

**Complexity:** For expense categories, picking from the dropdown must first show an inline attribution prompt (jay/minnie/shared) before saving. Use a two-step selection: first pick appears as a "popover" or inline row-expand asking for attribution, then saves on attribution confirmation.

```typescript
// Transaction row category select — handles two-step flow for expense categories
function CategorySelect({ txn, onSaved }: { txn: BankTransactionResponse; onSaved: () => void }) {
  const [pendingCategory, setPendingCategory] = useState<string | null>(null)
  const [attribution, setAttribution] = useState<string | null>(null)
  const mutation = useMutation({
    mutationFn: (body: SingleCategoryRequest) =>
      apiFetch<BankTransactionResponse>(`/accounting/bank-transactions/${txn.id}/category`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      onSaved()
      void queryClient.invalidateQueries({ queryKey: ['finance', 'transactions'] })
      void queryClient.invalidateQueries({ queryKey: ['finance', 'summary'] })
    },
  })

  function handleCategorySelect(category: string) {
    if (EXPENSE_CATEGORIES.includes(category)) {
      setPendingCategory(category)  // show attribution prompt, don't save yet
    } else {
      mutation.mutate({ category })
    }
  }

  function handleAttributionConfirm() {
    if (pendingCategory && attribution) {
      mutation.mutate({ category: pendingCategory, attribution })
    }
  }
  // ...
}
```

### Pattern 3: Multi-Select with Bulk Toolbar

**What:** Each row has a Radix `Checkbox` controlled by a `Set<number>` in parent state (transaction IDs). When any are selected, a toolbar appears above the table. The toolbar has Select-All, Clear, and "Assign Category" (which opens a Select for bulk assignment).

**State model:**
```typescript
const [selected, setSelected] = useState<Set<number>>(new Set())
const allIds = transactions.map(t => t.id)
const isAllSelected = allIds.length > 0 && allIds.every(id => selected.has(id))

function toggleRow(id: number) {
  setSelected(prev => {
    const next = new Set(prev)
    next.has(id) ? next.delete(id) : next.add(id)
    return next
  })
}

function toggleAll() {
  setSelected(isAllSelected ? new Set() : new Set(allIds))
}
```

**Bulk PATCH:** Uses `PATCH /api/accounting/bank-transactions/categorize` with `assignments` array. Expense categories in bulk require attribution — the toolbar's "Assign Category" flow should show an attribution prompt for expense categories before firing.

### Pattern 4: Transaction Filter Bar

**What:** Filter row above the table. Uses existing shadcn/ui `Select` (for category filter), existing `Input` (for amount range), and existing `Input type="date"` (for date range). All filters are client-query-key driven — changing a filter updates the `useQuery` params, causing TanStack Query to refetch.

**Filter state in hook:**
```typescript
interface TransactionFilters {
  category: string | 'all' | 'uncategorized'   // 'uncategorized' maps to categorized=false
  startDate: string | null
  endDate: string | null
  minAmount: string | null
  maxAmount: string | null
}
```

**Note:** The backend `GET /api/accounting/bank-transactions` does NOT support `min_amount`/`max_amount` query params. Amount range filtering must be done client-side on the fetched page, or a backend param must be added. Given potentially large data volumes, adding backend `min_amount`/`max_amount` params is the correct fix.

### Pattern 5: Expense/Loan Toggle Form

**What:** A single form with a toggle (`expense` / `loan payment`). When toggled, fields change. Use `useState` for the toggle, render different field sets conditionally.

```typescript
type FormType = 'expense' | 'loan_payment'

// Expense fields: expense_date, amount, category (EXPENSE_CATEGORIES only), description,
//                 attribution (jay/minnie/shared), property_id (required per CONTEXT.md), vendor
// Loan payment fields: loan_id (Select from useLoans()), principal, interest,
//                      payment_date, payment_ref
```

**Loan dropdown label format:** Per context: "Mortgage - Jay - $X remaining" — fetch loans from `GET /api/accounting/loans`, which returns `name` and `current_balance`. Display as `${loan.name} - $${formatCurrency(loan.current_balance)} remaining`.

**After submit:** Inline success message + form reset. The success message stays visible until user acts (not auto-dismissed). This supports batch entry sessions.

**Idempotent skip handling:** Loan payment `POST` can return `{"status": "skipped", ...}`. Show this as a distinct "Already recorded" message (yellow/warning) rather than full success.

### Pattern 6: Split-Panel Reconciliation

**What:** Two side-by-side panels. Left: platform payouts (unmatched bookings + auto-matched awaiting confirmation). Right: bank deposits (unmatched + needs_review + auto-matched awaiting confirmation). Suggested matches are visually connected.

**Visual connection between panels:** Use SVG connecting lines or a CSS `position: absolute` approach. The simplest reliable approach: highlight both sides with matching background colors when hovered or when a suggested match pair exists. Full SVG connector lines are complex — use color-coded matching (e.g., auto-matched pairs both highlighted in amber, operator selects and both get confirmed).

**Reconciliation states:**
- `unmatched_payouts` — bookings with no match yet → left panel, uncolored
- `pending_confirmation` — auto-matched pairs (NEW endpoint data) → both panels, amber highlight
- `needs_review` deposits → right panel, orange/warning highlight; shows candidate list when expanded
- `unmatched_deposits` — deposits with no candidate → right panel, uncolored

**Mobile layout:** Stack panels vertically. A toggle button ("View Payouts" / "View Deposits") to switch between panels. The context acknowledges mobile is at Claude's discretion — vertical stacking is correct.

### Pattern 7: TanStack Query Keys for Finance

Use a `['finance', ...]` namespace for all finance queries to enable broad invalidation:

```typescript
// Query keys
['finance', 'transactions', selectedPropertyId, filters]     // bank transactions list
['finance', 'loans']                                          // loans list (no property filter)
['finance', 'reconciliation', selectedPropertyId]             // unreconciled queue
['finance', 'summary', selectedPropertyId]                    // badge counts

// After any mutation that changes counts:
void queryClient.invalidateQueries({ queryKey: ['finance'] })  // invalidates all finance queries
```

### Anti-Patterns to Avoid

- **Don't use `useEffect` for data fetching.** Use TanStack Query `useQuery` and `useMutation` throughout.
- **Don't auto-save category immediately for expense categories.** Expense categories require attribution — show the attribution prompt first, save only when attribution is confirmed.
- **Don't nest Tooltip inside Popover.** If showing row tooltips on transaction descriptions, don't wrap them in Popover triggers — use separate components (Radix Tooltip + Popover conflict on click).
- **Don't hardcode property attribution as "all properties."** The expense form requires explicit attribution (jay/minnie/shared) — "All Properties" in the property selector doesn't remove this requirement.
- **Don't skip the `['finance', 'summary']` invalidation after categorization.** The Finance badge count depends on uncategorized count — every categorization must invalidate the summary query.
- **Don't forget `apiFetch` prepends `/api/`.** All accounting endpoints are at `/api/accounting/...`. Pass `/accounting/...` to `apiFetch()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Checkbox in table rows | Custom input[type=checkbox] | `radix-ui` Checkbox (already installed) | Radix handles indeterminate state, keyboard nav, accessibility |
| Scrollable reconciliation panels | CSS overflow:scroll | `radix-ui` ScrollArea (already installed) | Custom scrollbars, overflow handling, keyboard scrolling |
| Category dropdown | Custom `<select>` | Existing `Select` component | Already installed, accessible, styled |
| Loading skeletons | Custom shimmer divs | Existing `Skeleton` component | Already used in project |
| Error handling | Custom error div | Existing `ErrorAlert` component | Already in `src/components/shared/` |
| Empty states | Custom message | Existing `EmptyState` component | Already in `src/components/shared/` |
| Form field labels | Custom label div | Existing `Label` component | Already in `src/components/ui/` |
| Text inputs (amount, description) | Bare `<input>` | Existing `Input` component | Already in `src/components/ui/` |
| Inline mutation state | Custom loading flag | TanStack `useMutation` `.isPending` / `.isSuccess` | Already established pattern in project |

**Key insight:** Every primitive needed exists. The complexity in this phase is in the interaction design (two-step category save, split-panel matching, multi-select toolbar), not in tooling.

---

## Common Pitfalls

### Pitfall 1: Expense Category Attribution Not Required by UI

**What goes wrong:** User picks an expense category (e.g., "repairs_maintenance") and the PATCH fires immediately. Backend returns HTTP 422: "attribution is required for expense categories."
**Why it happens:** The auto-save-on-select pattern works for non-expense categories but fails silently for expense categories if attribution isn't captured first.
**How to avoid:** Before firing the PATCH, check `EXPENSE_CATEGORIES.includes(category)`. If true, show an inline attribution prompt (a row-level dropdown or popover for jay/minnie/shared) and delay the save until attribution is selected.
**Warning signs:** 422 errors in browser dev tools on categorization attempts with expense categories.

### Pitfall 2: Auto-Matched Items Invisible Until Backend Gap Fixed

**What goes wrong:** After running reconciliation, the operator sees an empty "Suggested Matches" panel because the current `unreconciled` endpoint doesn't return auto-matched items.
**Why it happens:** `GET /api/accounting/reconciliation/unreconciled` queries `WHERE reconciliation_status = "unmatched"` — auto-matched items have `status="matched"`, not `"unmatched"`.
**How to avoid:** Fix the backend endpoint first (add `pending_confirmation` key). Build the reconciliation UI to consume this new data shape. Do not attempt to build the reconciliation UI without fixing this gap first.
**Warning signs:** Running reconciliation returns auto_matched=N but the reconciliation panel shows nothing to confirm.

### Pitfall 3: Finance Badge Query Missing Property Filter

**What goes wrong:** Finance badge count doesn't update when property selector changes.
**Why it happens:** The `['finance', 'summary', selectedPropertyId]` query key omits `selectedPropertyId`, so TanStack Query reuses cached data.
**How to avoid:** Include `selectedPropertyId` in the query key for the finance-summary endpoint. The backend endpoint must accept `property_id` as a query param.
**Warning signs:** Badge shows same count regardless of selected property.

### Pitfall 4: Reconciliation Candidate Matching Logic Error

**What goes wrong:** The "needs_review" deposit shows no candidates, or shows wrong candidates.
**Why it happens:** Client-side candidate derivation matches only on `amount` equality. But the algorithm used a 7-day date window too. A deposit with the same amount as multiple unmatched bookings but different dates may show incorrect candidates.
**How to avoid:** Client-side candidate matching should filter `unmatched_payouts` by:
1. `parseFloat(payout.net_amount) === parseFloat(deposit.amount)` (amount equality)
2. `Math.abs(daysDiff(deposit.date, payout.check_in_date)) <= 7` (7-day window)
This reproduces the server algorithm's logic exactly.
**Warning signs:** "Needs review" items show 0 candidates even though unmatched payouts exist with the same amount.

### Pitfall 5: Property Selector "All Properties" New Behavior

**What goes wrong:** Finance queries work with a single property but fail with `property_id=null` because the backend doesn't support "All Properties" for certain endpoints.
**Why it happens:** The context notes "All Properties" is new behavior for the Finance tab. Most existing API endpoints accept `property_id` as optional (null = all), so this should work — but the `GET /api/accounting/bank-transactions` endpoint lacks a `property_id` filter entirely.
**How to avoid:** Add `property_id` filter to `GET /api/accounting/bank-transactions` in the backend so Finance tab transactions respect the property selector. Verify the `GET /api/accounting/reconciliation/unreconciled` endpoint also accepts `property_id` (currently it does NOT have this param).
**Warning signs:** Property selector changes don't filter Finance tab data; all properties' data always shown.

### Pitfall 6: Tailwind v4 `@apply` with Design Tokens

**What goes wrong:** Custom CSS using `@apply border-border` fails to compile.
**Why it happens:** Established prior decision [07-01] — Tailwind v4 `@apply` with CSS variable tokens fails. Use `hsl(var(--border))` directly.
**How to avoid:** Don't use `@apply` with design token class names in custom CSS. Use inline Tailwind utilities in JSX or direct CSS variable references in `@layer base` rules.

### Pitfall 7: Transaction List Pagination vs Total Count

**What goes wrong:** "Load more" pagination requires knowing total count, but `GET /api/accounting/bank-transactions` returns only items, not total count.
**Why it happens:** The endpoint has `limit` and `offset` params but no `total` in the response.
**How to avoid:** Use **cursor-style "load more"** (if the current page returned `limit` items, show "Load more" button) rather than a page indicator that requires total count. Alternatively, add a `total` count to the backend response. For the initial implementation, "load more" is sufficient and matches the context's "pagination vs infinite scroll at Claude's discretion" note.

### Pitfall 8: Reconciliation SVG Connector Lines

**What goes wrong:** Attempting to draw SVG lines between matched pairs in two DOM columns produces lines in wrong positions after scroll or resize.
**Why it happens:** SVG absolute positions calculated at render time become stale when the panels scroll or resize.
**How to avoid:** Use **color-coded highlighting** instead of SVG connector lines. Both the payout and deposit in a matched pair share the same highlight color (amber for pending_confirmation). On hover of either side, add a CSS ring to its counterpart (via shared state). This is both more maintainable and works correctly with scroll/resize.

---

## Code Examples

### Checkbox Component (new, from installed primitive)

```typescript
// Source: @radix-ui/react-checkbox type declarations in node_modules
// src/components/ui/checkbox.tsx
"use client"

import * as React from "react"
import { Checkbox as CheckboxPrimitive } from "radix-ui"
import { CheckIcon } from "lucide-react"
import { cn } from "@/lib/utils"

function Checkbox({
  className,
  ...props
}: React.ComponentProps<typeof CheckboxPrimitive.Root>) {
  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      className={cn(
        "peer border-input dark:bg-input/30 data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground dark:data-[state=checked]:bg-primary data-[state=checked]:border-primary focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive size-4 shrink-0 rounded-[4px] border shadow-xs transition-shadow outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator
        data-slot="checkbox-indicator"
        className="flex items-center justify-center text-current transition-none"
      >
        <CheckIcon className="size-3.5" />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  )
}

export { Checkbox }
```

### Auto-Save Category with Attribution Prompt

```typescript
// Source: project patterns + TanStack Query v5 useMutation
// The two-step save for expense categories
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { apiFetch } from '@/api/client'
import { EXPENSE_CATEGORIES, ALL_CATEGORIES } from '@/lib/categories'

const ATTRIBUTION_OPTIONS = ['jay', 'minnie', 'shared'] as const

function CategoryCell({ txn }: { txn: BankTransactionResponse }) {
  const queryClient = useQueryClient()
  const [pendingCategory, setPendingCategory] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const mutation = useMutation({
    mutationFn: (body: SingleCategoryRequest) =>
      apiFetch<BankTransactionResponse>(`/accounting/bank-transactions/${txn.id}/category`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      setSaved(true)
      setTimeout(() => setSaved(false), 1500)
      void queryClient.invalidateQueries({ queryKey: ['finance', 'transactions'] })
      void queryClient.invalidateQueries({ queryKey: ['finance', 'summary'] })
      setPendingCategory(null)
    },
  })

  function handleCategoryChange(category: string) {
    if (EXPENSE_CATEGORIES.includes(category)) {
      setPendingCategory(category)  // wait for attribution
    } else {
      mutation.mutate({ category })
    }
  }

  if (pendingCategory) {
    return (
      <div className="flex items-center gap-1">
        <span className="text-xs text-muted-foreground">{pendingCategory} — for:</span>
        <Select onValueChange={(attr) => mutation.mutate({ category: pendingCategory, attribution: attr })}>
          <SelectTrigger className="h-7 text-xs w-24">
            <SelectValue placeholder="Who?" />
          </SelectTrigger>
          <SelectContent>
            {ATTRIBUTION_OPTIONS.map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1">
      <Select defaultValue={txn.category ?? undefined} onValueChange={handleCategoryChange}>
        <SelectTrigger className="h-7 text-xs w-36">
          <SelectValue placeholder="Uncategorized" />
        </SelectTrigger>
        <SelectContent>
          {ALL_CATEGORIES.map(cat => (
            <SelectItem key={cat} value={cat}>
              {cat.replace(/_/g, ' ')}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {saved && <span className="text-green-600 text-xs">Saved</span>}
      {mutation.isPending && <span className="text-muted-foreground text-xs">Saving...</span>}
    </div>
  )
}
```

### Expense/Loan Form Type Toggle

```typescript
// Source: project patterns — useState toggle with conditional field rendering
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { apiFetch } from '@/api/client'

type FormType = 'expense' | 'loan_payment'

export function ExpenseLoanForm() {
  const [type, setType] = useState<FormType>('expense')
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: loans = [] } = useQuery<LoanResponse[]>({
    queryKey: ['finance', 'loans'],
    queryFn: () => apiFetch<LoanResponse[]>('/accounting/loans'),
    staleTime: 5 * 60 * 1000,
  })

  const expenseMutation = useMutation({
    mutationFn: (body: ExpenseRequest) =>
      apiFetch<ExpenseResponse>('/accounting/expenses', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      setSuccessMsg('Expense recorded')
      void queryClient.invalidateQueries({ queryKey: ['finance'] })
      // reset form fields here
    },
  })

  const loanMutation = useMutation({
    mutationFn: (body: LoanPaymentRequest) =>
      apiFetch<{ status: string }>('/accounting/loans/payments', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      if (data.status === 'skipped') {
        setSuccessMsg('Already recorded (duplicate payment_ref)')
      } else {
        setSuccessMsg('Payment recorded')
      }
      void queryClient.invalidateQueries({ queryKey: ['finance', 'loans'] })
      // reset form
    },
  })

  return (
    <div className="space-y-4">
      {/* Toggle */}
      <div className="flex gap-2">
        <Button
          variant={type === 'expense' ? 'default' : 'outline'}
          size="sm"
          onClick={() => { setType('expense'); setSuccessMsg(null) }}
        >
          Expense
        </Button>
        <Button
          variant={type === 'loan_payment' ? 'default' : 'outline'}
          size="sm"
          onClick={() => { setType('loan_payment'); setSuccessMsg(null) }}
        >
          Loan Payment
        </Button>
      </div>

      {successMsg && (
        <p className="text-sm text-green-600 dark:text-green-400">{successMsg}</p>
      )}

      {type === 'expense' ? (
        /* Expense fields */
        <form onSubmit={/* handleExpenseSubmit */() => {}}>
          {/* expense_date, amount, category, description, attribution, property_id, vendor */}
        </form>
      ) : (
        /* Loan payment fields */
        <form onSubmit={/* handleLoanSubmit */() => {}}>
          <div className="space-y-2">
            <Label>Loan</Label>
            <Select name="loan_id">
              <SelectTrigger>
                <SelectValue placeholder="Select loan..." />
              </SelectTrigger>
              <SelectContent>
                {loans.map(loan => (
                  <SelectItem key={loan.id} value={String(loan.id)}>
                    {loan.name} — ${Number(loan.current_balance).toLocaleString('en-US', { minimumFractionDigits: 2 })} remaining
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {/* principal, interest, payment_date, payment_ref */}
        </form>
      )}
    </div>
  )
}
```

### Finance Badge Query in AppShell

```typescript
// Source: project pattern from existing actions badge in AppShell.tsx
// Add alongside the existing actionsData query

interface FinanceSummaryResponse {
  uncategorized_count: number
  unreconciled_count: number
}

// In AppShell:
const { data: financeSummary } = useQuery<FinanceSummaryResponse>({
  queryKey: ['finance', 'summary', selectedPropertyId],
  queryFn: () => {
    const params = selectedPropertyId !== null ? `?property_id=${selectedPropertyId}` : ''
    return apiFetch<FinanceSummaryResponse>(`/accounting/finance-summary${params}`)
  },
  staleTime: 2 * 60 * 1000,  // 2 minutes — financial state changes with user actions
})

const financeBadgeCount = (financeSummary?.uncategorized_count ?? 0)
  + (financeSummary?.unreconciled_count ?? 0)
```

### Needs-Review Candidate Derivation (Client-Side)

```typescript
// Reproduce the server's candidate logic client-side:
// Filter unmatched_payouts to find candidates for a needs_review deposit.
// Uses same criteria as reconciliation algorithm: exact amount + 7-day window.
function getCandidatesForDeposit(
  deposit: { id: number; date: string; amount: string },
  unmatchedPayouts: Array<{ id: number; net_amount: string; check_in_date: string; guest_name: string; platform: string }>
) {
  const depositDate = new Date(deposit.date)
  const depositAmount = parseFloat(deposit.amount)
  return unmatchedPayouts.filter(payout => {
    const payoutAmount = parseFloat(payout.net_amount)
    const payoutDate = new Date(payout.check_in_date)
    const daysDiff = Math.abs((depositDate.getTime() - payoutDate.getTime()) / (1000 * 60 * 60 * 24))
    return payoutAmount === depositAmount && daysDiff <= 7
  })
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Individual `@radix-ui/*` imports | `import { X } from "radix-ui"` monorepo | radix-ui v1.x (2024) | Use `import { Checkbox, ScrollArea } from "radix-ui"` |
| Tailwind v3 config JS | Tailwind v4 CSS `@import "tailwindcss"` | 2025 | No `tailwind.config.js`; CSS-only config |
| `React.forwardRef` in components | `React.ComponentProps<typeof Primitive.Root>` | Jan 2026 | shadcn component wrappers use ComponentProps pattern |
| `react-router-dom` as separate import | `react-router` v7 merges package | 2025 | Project uses `react-router-dom` v7.13.1 (still valid) |

---

## Open Questions

1. **Backend: `GET /api/accounting/bank-transactions` missing `property_id` filter**
   - What we know: The endpoint has no `property_id` param. The Finance tab's property selector is supposed to filter transactions.
   - What's unclear: Was this intentional (all transactions belong to a property via categorization) or an oversight?
   - Recommendation: Add `property_id` filter to the bank-transactions list endpoint. Without it, the Finance tab cannot filter transactions by property.

2. **Backend: `GET /api/accounting/reconciliation/unreconciled` missing `property_id` filter**
   - What we know: The endpoint has no `property_id` param.
   - What's unclear: Whether the context's "All Properties" reconciliation view is the default and property filtering is secondary.
   - Recommendation: Add optional `property_id` to the reconciliation endpoint. For now, "All Properties" is the default (matches context — cross-property reconciliation is a common workflow).

3. **Pagination strategy for transaction list**
   - What we know: Context says "pagination vs infinite scroll at Claude's discretion." The endpoint supports `limit`/`offset`. No total count returned. Typical operator data volume: unknown.
   - What's unclear: How many transactions a typical operator has (hundreds vs thousands).
   - Recommendation: Start with server-side pagination with a "Load More" button (client fetches page 1=limit 50; button appends page 2, etc.). Avoid full pagination controls since total count is unavailable without a backend change. This is simple and works regardless of data volume.

4. **SVG connector lines vs color-coded matching**
   - What we know: Context says "suggested matches highlighted with lines/colors between them." SVG lines between DOM elements are fragile with scroll.
   - What's unclear: How important the actual line drawing is vs color-only matching.
   - Recommendation: Implement color-coded matching only (amber highlight on both sides of a suggested match). Document this as a deliberate tradeoff. If SVG lines are later required, that's a separate enhancement.

5. **Property attribution on expense form: required vs optional**
   - What we know: Context says "property attribution is a required field on expenses." The `ExpenseRequest` schema has `property_id` as optional (`int | None`) but `attribution` (jay/minnie/shared) as required. A property_id of `null` is valid for `attribution="shared"`.
   - What's unclear: Should the form show a property dropdown (id) AND a separate attribution dropdown (jay/minnie/shared), or just attribution?
   - Recommendation: Show both fields. `attribution` maps to the accounting logic (jay/minnie/shared as string labels), while `property_id` (int FK) is the database property reference. For expenses attributed to a specific property (jay or minnie), the `property_id` should be set to that property's ID. For "shared", `property_id` can be null. Pre-populate `property_id` from the global property selector if a single property is selected.

---

## Sources

### Primary (HIGH confidence)

- `/Users/tunderhill/development/airbnb-tools/app/api/accounting.py` — All accounting API endpoints, request/response schemas, category validation rules
- `/Users/tunderhill/development/airbnb-tools/app/api/dashboard.py` — Dashboard API patterns, badge count pattern
- `/Users/tunderhill/development/airbnb-tools/app/accounting/reconciliation.py` — Reconciliation algorithm, match status values, candidate logic
- `/Users/tunderhill/development/airbnb-tools/app/accounting/expenses.py` — EXPENSE_CATEGORIES list
- `/Users/tunderhill/development/airbnb-tools/app/accounting/reports.py` — NON_EXPENSE_CATEGORIES, ALL_CATEGORIES
- `/Users/tunderhill/development/airbnb-tools/app/models/reconciliation.py` — ReconciliationMatch model, status values
- `/Users/tunderhill/development/airbnb-tools/app/models/bank_transaction.py` — BankTransaction model fields
- `/Users/tunderhill/development/airbnb-tools/frontend/src/components/layout/AppShell.tsx` — Existing tab structure, badge pattern
- `/Users/tunderhill/development/airbnb-tools/frontend/src/components/layout/Header.tsx` — Property selector pattern
- `/Users/tunderhill/development/airbnb-tools/frontend/src/store/usePropertyStore.ts` — Zustand store shape (selectedPropertyId: number | null)
- `/Users/tunderhill/development/airbnb-tools/frontend/src/api/client.ts` — apiFetch behavior (prepends /api)
- `/Users/tunderhill/development/airbnb-tools/frontend/src/hooks/useFinancials.ts` — Query hook pattern for this project
- `/Users/tunderhill/development/airbnb-tools/frontend/package.json` — Exact installed package versions
- `/Users/tunderhill/development/airbnb-tools/frontend/node_modules/radix-ui/dist/index.d.ts` — Checkbox, ScrollArea exports confirmed
- Phase 7 RESEARCH.md — shadcn/ui, Tailwind v4, TanStack Query v5 patterns (verified 2026-02-28)
- Phase 10 RESEARCH.md — Radix-ui monorepo import pattern, TanStack mutation pattern

### Secondary (MEDIUM confidence)

- MDN Web Docs — Checkbox indeterminate state behavior (standard DOM API)

### Tertiary (LOW confidence)

- None — all critical findings verified against source files.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against package.json and installed node_modules
- API shapes: HIGH — verified against actual backend source files
- Architecture patterns: HIGH — derived from existing project component patterns
- API gaps: HIGH — identified from source code inspection; gaps are facts, not speculation
- Reconciliation UI complexity: MEDIUM — design approach is sound but split-panel implementation requires iteration

**Research date:** 2026-03-01
**Valid until:** 2026-03-31 (30 days — all libraries locked in package.json; only risk is if backend API changes)

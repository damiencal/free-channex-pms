# Phase 13: Integration Bugfixes & Cleanup - Research

**Researched:** 2026-03-02
**Domain:** TypeScript interface mismatches, Python category validation, Python docstrings, TypeScript suppressions
**Confidence:** HIGH

## Summary

This phase is a targeted cleanup of four well-understood, already-diagnosed items from the v1 milestone audit. There is no new architecture to design, no new libraries to evaluate, and no ambiguity about what to change. All four items are surgical edits to existing files where the root cause is already confirmed by reading the source.

The two integration bugs (blank property labels, 422 on income categories) are frontend-only mismatches against a stable, unchanged backend. The two tech debt items (stale docstring, `@ts-expect-error` suppressions) are documentation and type-annotation corrections with no behavioral changes.

**Primary recommendation:** Make four focused file edits. No new dependencies. No refactoring outside the identified lines. Verify each fix matches the stated success criterion.

---

## Standard Stack

No new libraries are needed. All fixes use the existing project stack.

### Existing Stack in Play

| Layer | Technology | Version Source |
|-------|------------|----------------|
| Frontend components | React + TypeScript | Already installed |
| UI primitives | shadcn/ui Select, SelectItem | Already installed |
| Backend validation | FastAPI + Pydantic | Already installed |
| Category constants | `CategorySelect.tsx`, `reports.py` | Already in codebase |
| Type definitions | TypeScript interfaces (inline in components) | Already in codebase |

**Installation:** No new packages required.

---

## Architecture Patterns

### Pattern 1: TypeScript Interface — Match the API Contract

The frontend `Property` interface in `RVshareEntryForm.tsx` declares a field that does not exist in the API response. The fix is to update the interface to match the actual backend contract.

**Backend contract** (`/api/dashboard/properties` endpoint in `app/api/dashboard.py`, line 57-64):
```python
return [
    {
        "id": p.id,
        "slug": p.slug,
        "display_name": p.display_name,  # the real field name
    }
    for p in properties
]
```

**Current (broken) frontend interface** (`RVshareEntryForm.tsx`, lines 17-21):
```typescript
interface Property {
  id: number
  slug: string
  name: string   // BUG: API returns display_name, not name
}
```

**Fixed interface:**
```typescript
interface Property {
  id: number
  slug: string
  display_name: string   // matches API response exactly
}
```

**Current (broken) SelectItem render** (`RVshareEntryForm.tsx`, line 328):
```typescript
<SelectItem key={p.slug} value={p.slug}>
  {p.name}  {/* BUG: p.name is undefined — renders blank */}
</SelectItem>
```

**Fixed SelectItem render:**
```typescript
<SelectItem key={p.slug} value={p.slug}>
  {p.display_name}  {/* matches interface field */}
</SelectItem>
```

### Pattern 2: Category Alignment — Remove Income Categories from Frontend

The backend `ALL_CATEGORIES` (in `app/accounting/reports.py`, line 33) is defined as:
```python
ALL_CATEGORIES = EXPENSE_CATEGORIES + NON_EXPENSE_CATEGORIES
```

It does NOT include income categories. The validation check in `categorize_single_transaction` (line 1094) and `categorize_bulk_transactions` (line 1019) both read:
```python
if body.category not in ALL_CATEGORIES:
    raise HTTPException(status_code=422, ...)
```

This means any of `['rental_income', 'cleaning_fee', 'service_fee', 'other_income']` will trigger a 422.

**The correct fix is to remove `INCOME_CATEGORIES` from frontend `ALL_CATEGORIES`.** The frontend `ALL_CATEGORIES` is exported from `CategorySelect.tsx` and consumed only by:
- `CategorySelect.tsx` itself (renders the Income group in the dropdown)
- `BulkActionToolbar.tsx` imports only `EXPENSE_CATEGORIES` and `NON_EXPENSE_CATEGORIES` (lines 15-18) — it does NOT import `ALL_CATEGORIES` or `INCOME_CATEGORIES`

**Scope of change in CategorySelect.tsx:**
1. Remove the `INCOME_CATEGORIES` constant export (lines 33-38)
2. Remove the `INCOME_CATEGORIES` from the `ALL_CATEGORIES` definition (line 47)
3. Remove the Income `SelectGroup` from the dropdown render (lines 151-158)
4. Keep `EXPENSE_CATEGORIES`, `NON_EXPENSE_CATEGORIES`, `ALL_CATEGORIES`, `formatCategoryName` exports unchanged

**Why remove rather than add income categories to the backend:** Decision [04-01] locked `NON_EXPENSE_CATEGORIES = [owner_deposit, loan_payment, transfer, personal]`. Income categories like `rental_income` and `cleaning_fee` describe booking revenue — not bank transaction categorization. Bank transactions categorized as income don't map to a defined journal entry workflow in the current system.

### Pattern 3: Python Docstring Correction

The `recognize_booking_revenue` function in `app/accounting/revenue.py` has a stale docstring. The function is called automatically via a `BackgroundTask` after CSV import (wired in Phase 9). The current docstring at lines 152-154 says the opposite:

```python
"""Create revenue recognition journal entries for a booking.

OPERATOR-TRIGGERED. Must be called explicitly from an API endpoint — this
function is never invoked automatically during CSV import.
```

The module-level docstring at lines 1-6 also states:
```
Revenue recognition is OPERATOR-TRIGGERED via API — it is NOT called automatically
on booking import.
```

Both the function docstring and the module docstring need updating to reflect that revenue recognition is now invoked automatically as a BackgroundTask after CSV import (Phase 9 fix).

### Pattern 4: Remove @ts-expect-error Suppressions via Interface Extension

`IncomeStatementTab.tsx` has two `@ts-expect-error` suppressions at lines 289 and 313. Both occur when pushing a "subtotal" row object onto arrays typed as `MonthlyTableRow[]`:

```typescript
revenueRows.push({
  label: 'Total Revenue',
  values: revMonthlyTotals,
  total: monthlyData.totals.revenue.total,
  // @ts-expect-error isSubtotal not in base type but MonthlyTable handles it
  isSubtotal: true,
})
```

`MonthlyTableRow` in `MonthlyTable.tsx` (lines 6-12) **already declares `isSubtotal?: boolean`** as an optional field:

```typescript
interface MonthlyTableRow {
  label: string
  values: Record<string, string>
  total: string
  isSubtotal?: boolean   // already present!
  isGrandTotal?: boolean
}
```

The comment in the suppression is wrong — `isSubtotal` IS in the interface. The suppressions are unnecessary. The fix is to simply remove both `// @ts-expect-error` comment lines. TypeScript will accept `isSubtotal: true` without a suppression because the interface already allows it.

**Root cause:** The suppressions were added defensively during Phase 12 implementation and were never needed.

---

## Don't Hand-Roll

These fixes do not benefit from new abstractions. Keep them minimal.

| Temptation | Avoid | Reason |
|------------|-------|--------|
| Centralizing Property type across components | Creating a shared `types/property.ts` | This phase closes a single bug; cross-cutting type refactor is out of scope |
| Backend income category support | Adding income categories to backend ALL_CATEGORIES | Requires journal entry workflow design — out of scope |
| Shared category validation between frontend and backend | Code-generating category lists | Out of scope; the fix is just removing the frontend-only income categories |

---

## Common Pitfalls

### Pitfall 1: Fixing Only One Location in RVshareEntryForm

**What goes wrong:** Changing the interface but not the render, or vice versa.
**Why it happens:** There are two places: the `Property` interface (line 20) and the `{p.name}` render (line 328).
**How to avoid:** Change both `name: string` in the interface AND `{p.name}` in the SelectItem in the same edit.
**Warning signs:** TypeScript error on `{p.name}` after changing the interface, if only the interface was changed.

### Pitfall 2: Removing INCOME_CATEGORIES Breaks BulkActionToolbar

**What goes wrong:** `BulkActionToolbar.tsx` imports from `CategorySelect.tsx`.
**Why it won't happen here:** BulkActionToolbar imports only `EXPENSE_CATEGORIES` and `NON_EXPENSE_CATEGORIES` (confirmed at line 15-18 of BulkActionToolbar.tsx). It does NOT import `INCOME_CATEGORIES` or `ALL_CATEGORIES`. Removing `INCOME_CATEGORIES` will not affect the bulk toolbar.
**Warning signs:** TypeScript import error in BulkActionToolbar if the wrong export is deleted.

### Pitfall 3: Incorrect Docstring Replacement Creates New Misinformation

**What goes wrong:** Replacing "OPERATOR-TRIGGERED" with vague or partially-accurate text.
**How to avoid:** The updated docstring should state that `recognize_booking_revenue` is called both (a) automatically as a BackgroundTask after CSV import, and (b) explicitly via the operator-triggered API endpoint. Both call paths exist.

### Pitfall 4: Removing @ts-expect-error Lines Exposes a Different Type Error

**What goes wrong:** If `MonthlyTableRow` did NOT have `isSubtotal`, removing `@ts-expect-error` would create a compile error.
**Why it won't happen here:** `MonthlyTable.tsx` interface confirms `isSubtotal?: boolean` is declared (line 10). The suppressions were never needed.
**Verification:** After removing the two comment lines, TypeScript build must pass without new errors.

---

## Code Examples

### Fix 1: RVshareEntryForm Property Interface and Render

**Source:** Direct inspection of `frontend/src/components/actions/RVshareEntryForm.tsx` and `app/api/dashboard.py`

```typescript
// BEFORE (line 17-21)
interface Property {
  id: number
  slug: string
  name: string   // wrong — API returns display_name
}

// AFTER
interface Property {
  id: number
  slug: string
  display_name: string
}

// BEFORE (line 327-329)
<SelectItem key={p.slug} value={p.slug}>
  {p.name}
</SelectItem>

// AFTER
<SelectItem key={p.slug} value={p.slug}>
  {p.display_name}
</SelectItem>
```

### Fix 2: CategorySelect Remove INCOME_CATEGORIES

**Source:** Direct inspection of `frontend/src/components/finance/CategorySelect.tsx`

```typescript
// REMOVE lines 33-38:
export const INCOME_CATEGORIES = [
  'rental_income',
  'cleaning_fee',
  'service_fee',
  'other_income',
]

// CHANGE line 47:
// BEFORE:
export const ALL_CATEGORIES = [...EXPENSE_CATEGORIES, ...INCOME_CATEGORIES, ...NON_EXPENSE_CATEGORIES]
// AFTER:
export const ALL_CATEGORIES = [...EXPENSE_CATEGORIES, ...NON_EXPENSE_CATEGORIES]

// REMOVE lines 151-158 (the Income SelectGroup):
<SelectGroup>
  <SelectLabel>Income</SelectLabel>
  {INCOME_CATEGORIES.map((cat) => (
    <SelectItem key={cat} value={cat}>
      {formatCategoryName(cat)}
    </SelectItem>
  ))}
</SelectGroup>
```

### Fix 3: revenue.py Docstring Correction

**Source:** Direct inspection of `app/accounting/revenue.py` lines 1-9 and 152-154

```python
# Module-level docstring (lines 1-6): update the first paragraph:
# BEFORE:
"""Revenue recognition is OPERATOR-TRIGGERED via API — it is NOT called automatically
on booking import. The operator reviews imported bookings and then explicitly triggers
recognition (batch or per-booking) through the API.

# AFTER (suggested):
"""Revenue recognition runs automatically as a BackgroundTask after each CSV import
(wired by Phase 9). It can also be triggered explicitly via the API operator endpoints
(POST /api/accounting/revenue/recognize and /recognize-all).

# Function docstring (lines 152-154): update the "OPERATOR-TRIGGERED" paragraph:
# BEFORE:
OPERATOR-TRIGGERED. Must be called explicitly from an API endpoint — this
function is never invoked automatically during CSV import.

# AFTER (suggested):
Called automatically as a BackgroundTask after CSV import, and also available
via the operator-triggered API endpoints. Safe to call multiple times (idempotent).
```

### Fix 4: IncomeStatementTab Remove @ts-expect-error

**Source:** Direct inspection of `frontend/src/components/reports/IncomeStatementTab.tsx` lines 289 and 313

```typescript
// BEFORE (line 288-291):
revenueRows.push({
  label: 'Total Revenue',
  values: revMonthlyTotals,
  total: monthlyData.totals.revenue.total,
  // @ts-expect-error isSubtotal not in base type but MonthlyTable handles it
  isSubtotal: true,
})

// AFTER: just remove the @ts-expect-error comment line
revenueRows.push({
  label: 'Total Revenue',
  values: revMonthlyTotals,
  total: monthlyData.totals.revenue.total,
  isSubtotal: true,
})

// Same treatment at line 312-316 for expenseRows.push(...)
```

---

## State of the Art

No new libraries or patterns. All fixes apply the same patterns already used in the codebase.

| Item | Before Fix | After Fix |
|------|-----------|-----------|
| Property dropdown labels | Blank (p.name undefined) | Shows display_name from API |
| Income category selection | 422 from backend | Removed from dropdown entirely |
| revenue.py module docstring | "OPERATOR-TRIGGERED...never invoked automatically" | Reflects BackgroundTask auto-invocation |
| @ts-expect-error suppressions | 2 suppressions in IncomeStatementTab | 0 suppressions — interface already supports prop |

---

## Open Questions

None. All four items are fully understood from source inspection. No ambiguity about approach.

---

## Sources

### Primary (HIGH confidence)

All findings are from direct source inspection of the project codebase:

- `frontend/src/components/actions/RVshareEntryForm.tsx` — Property interface lines 17-21, SelectItem render line 328
- `app/api/dashboard.py` — `/properties` endpoint lines 46-64 confirms `display_name` is the returned field
- `frontend/src/components/finance/CategorySelect.tsx` — INCOME_CATEGORIES lines 33-38, ALL_CATEGORIES line 47, Income SelectGroup lines 151-158
- `frontend/src/components/finance/BulkActionToolbar.tsx` — import lines 14-18 confirms it does NOT import INCOME_CATEGORIES or ALL_CATEGORIES
- `app/accounting/reports.py` — ALL_CATEGORIES line 33 confirms income categories are absent from backend
- `app/api/accounting.py` — category validation logic lines 1094-1098 and 1019-1024 confirms 422 on invalid category
- `app/accounting/revenue.py` — stale docstring lines 1-6 (module) and 152-154 (function)
- `frontend/src/components/reports/IncomeStatementTab.tsx` — @ts-expect-error lines 289 and 313
- `frontend/src/components/reports/MonthlyTable.tsx` — MonthlyTableRow interface lines 6-12 confirms `isSubtotal?: boolean` is already declared

---

## Metadata

**Confidence breakdown:**
- Bug 1 (RVshareEntryForm property labels): HIGH — root cause confirmed by reading interface and API response
- Bug 2 (income category 422): HIGH — root cause confirmed by reading both frontend ALL_CATEGORIES and backend ALL_CATEGORIES
- Tech debt 1 (revenue.py docstring): HIGH — stale text confirmed by reading both the docstring and the Phase 9 BackgroundTask wiring
- Tech debt 2 (@ts-expect-error): HIGH — suppressions confirmed unnecessary by reading MonthlyTableRow interface

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable codebase — these files are not under active development)

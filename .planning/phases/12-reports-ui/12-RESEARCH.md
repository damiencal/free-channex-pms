# Phase 12: Reports UI - Research

**Researched:** 2026-03-02
**Domain:** React/shadcn/ui financial report viewers; manual-fetch pattern; collapsible card sections; print CSS; date filter controls; monthly breakdown tables
**Confidence:** HIGH — all findings verified against actual project source files and installed packages

---

## Summary

Phase 12 is a pure frontend phase that replaces the placeholder `ReportsTab.tsx` with three interactive report viewers (P&L, Balance Sheet, Income Statement). All three backend report APIs already exist from Phase 4 (`/api/reports/pl`, `/api/reports/balance-sheet`, `/api/reports/income-statement`). Zero new npm packages are needed — the full component toolkit is already installed.

The key architectural decision is the **manual-fetch pattern**: reports only load when the user clicks "Generate", not on filter change. TanStack Query v5 supports this via `enabled: false` plus a trigger state variable. The query function fires only when `enabled` transitions to `true`, and the button re-fetches by updating the trigger. This prevents unnecessary requests during multi-filter adjustment.

The sub-tab structure (P&L | Balance Sheet | Income Statement) follows the exact same pattern as FinanceTab's sub-tabs (Transactions | Expenses & Loans | Reconciliation), using URL search params synced via `useSearchParams`. Collapsible sections use `Collapsible`/`CollapsibleTrigger`/`CollapsibleContent` from `src/components/ui/collapsible.tsx` — already installed via radix-ui. Print CSS is handled with Tailwind's `print:` variant utility prefix, added to `index.css` where layout control (hiding header/tabs) is needed.

**Primary recommendation:** Build reports in order of complexity — Balance Sheet first (simplest: one date, one totals view), then P&L (preset + custom date, percentage column, monthly sub-view), then Income Statement (same date pattern as P&L, monthly sub-view). Add a `src/api/reports.ts` with typed fetch functions and a `src/hooks/useReports.ts` with the manual-fetch hooks. Reuse existing `shared/EmptyState`, `shared/ErrorAlert`, and `ui/collapsible` — no new shared components needed.

---

## Standard Stack

### Core (All Already Installed — Zero New npm Packages)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| React | ^19.2.0 | UI framework | In use |
| Vite | ^7.3.1 | Build tool | In use |
| shadcn/ui components | (installed) | Card, Tabs, Collapsible, Button, Select | All present |
| Tailwind CSS v4 | ^4.2.1 | Styling + print: variant | In use |
| TypeScript | ~5.9.3 | Type safety | In use |
| @tanstack/react-query | ^5.90.21 | Manual-fetch pattern + caching | In use |
| zustand | ^5.0.11 | Global property selector (`usePropertyStore`) | In use |
| react-router-dom | ^7.13.1 | Sub-tab URL sync (`useSearchParams`) | In use |
| radix-ui | ^1.4.3 | Collapsible primitive (already wrapped) | In use |
| lucide-react | ^0.575.0 | ChevronDown/ChevronUp for collapse indicators | In use |

### UI Components Already Available (No Creation Needed)

| Component | Location | Usage in Phase 12 |
|-----------|----------|-------------------|
| `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` | `ui/tabs.tsx` | Sub-tab navigation (P&L / Balance Sheet / Income Statement) |
| `Card`, `CardHeader`, `CardTitle`, `CardContent` | `ui/card.tsx` | Report section cards |
| `Collapsible`, `CollapsibleTrigger`, `CollapsibleContent` | `ui/collapsible.tsx` | Collapsible report sections |
| `Button` | `ui/button.tsx` | Generate button, preset date buttons |
| `Select`, `SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue` | `ui/select.tsx` | Custom date input dropdowns (year/month) |
| `Skeleton` | `ui/skeleton.tsx` | Loading state placeholders |
| `EmptyState` | `shared/EmptyState.tsx` | "No report data for this period" |
| `ErrorAlert` | `shared/ErrorAlert.tsx` | API error display with retry |
| `Input` | `ui/input.tsx` | Custom date range inputs |

**Installation:** None required.

---

## Backend APIs — Verified Shapes

All endpoints are under `/api/reports/`. The `apiFetch` wrapper in `src/api/client.ts` prepends `/api` automatically so fetch calls use `/reports/...`.

### P&L: `GET /api/reports/pl`

**Query parameters:**
- Period (first match wins): `start_date` + `end_date`, OR `month` + `year`, OR `quarter` + `year`, OR `year`, OR `ytd=true`
- `breakdown`: `"combined"` (default) or `"property"`

**Combined response shape:**
```typescript
interface PLResponse {
  period: { start_date: string; end_date: string }
  breakdown: "combined"
  revenue: {
    by_platform: {
      [platform: string]: {  // e.g. "airbnb", "vrbo", "rvshare"
        months: Array<{ month: string; amount: string }>  // "2026-01"
        subtotal: string
      }
    }
    total: string
  }
  expenses: {
    by_category: { [category: string]: string }  // category name -> amount string
    total: string
  }
  net_income: string  // all Decimal as string e.g. "12345.67"
}
```

**Property breakdown response shape:**
```typescript
interface PLPropertyResponse {
  period: { start_date: string; end_date: string }
  breakdown: "property"
  properties: {
    [propertyName: string]: {
      property_id: number
      revenue: { by_platform: ...; total: string }
      expenses: { by_category: ...; total: string }
      net_income: string
    }
  }
  combined: {
    revenue: { by_platform: ...; total: string }
    expenses: { by_category: ...; total: string }
    net_income: string
  }
}
```

**IMPORTANT:** The `breakdown` parameter on `GET /api/reports/pl` maps to the property selector in the header. When "Combined" (null propertyId), send `breakdown=combined`. When a specific property is selected, the current API returns `breakdown=property` with all properties. The UI for property-specific P&L should use `breakdown=property` and display only the named property's data plus the combined totals — this matches the existing property selector pattern.

**CAVEAT:** The P&L `breakdown=property` response provides per-property sections keyed by `display_name` (a string), not by `property_id`. The frontend cannot directly match `selectedPropertyId` (a number) to the response without an additional lookup. This means either: (a) always use `breakdown=combined` and ignore the per-property breakdown in Phase 12 (simplest), or (b) also call `/api/dashboard/properties` to get the name-to-id mapping. **Recommendation: use `breakdown=combined` for Phase 12 and note property breakdown as a future enhancement — the filter context says to use the global property selector with a "Combined" option, which maps naturally to `breakdown=combined`.**

### Balance Sheet: `GET /api/reports/balance-sheet`

**Query parameters:**
- `as_of` (required): ISO date string — point-in-time snapshot

**Response shape:**
```typescript
interface BalanceSheetResponse {
  as_of: string  // ISO date
  assets: {
    accounts: Array<{ number?: string; name: string; balance: string }>
    total: string
  }
  liabilities: {
    accounts: Array<{ number?: string; name: string; balance: string }>
    total: string
  }
  equity: {
    accounts: Array<{ name: string; balance: string }>  // includes Retained Earnings (no number)
    total: string
  }
  total_liabilities_and_equity: string
}
```

**Key note:** Balance sheet is always combined (no per-property breakdown). The `as_of` date is computed from the preset selection (e.g., "This Month" → last day of current month, "Last Year" → Dec 31 of last year). The period presets must translate to a single point-in-time date.

### Income Statement: `GET /api/reports/income-statement`

**Query parameters:**
- Period (same as P&L): `start_date` + `end_date`, OR `month` + `year`, OR `quarter` + `year`, OR `year`, OR `ytd=true`
- `breakdown`: `"totals"` (default) or `"monthly"`

**Totals response shape:**
```typescript
interface IncomeStatementTotalsResponse {
  period: { start_date: string; end_date: string }
  breakdown: "totals"
  revenue: {
    by_account: { [accountName: string]: string }
    total: string
  }
  expenses: {
    by_account: { [accountName: string]: string }
    total: string
  }
  net_income: string
}
```

**Monthly response shape:**
```typescript
interface IncomeStatementMonthlyResponse {
  period: { start_date: string; end_date: string }
  breakdown: "monthly"
  months: Array<{
    month: string  // "2026-01"
    revenue: { by_account: { [name: string]: string }; total: string }
    expenses: { by_account: { [name: string]: string }; total: string }
    net_income: string
  }>
  totals: {
    revenue: { by_account: { [name: string]: string }; total: string }
    expenses: { by_account: { [name: string]: string }; total: string }
    net_income: string
  }
}
```

---

## Architecture Patterns

### Recommended File Structure

```
src/
├── api/
│   ├── client.ts          # (existing)
│   ├── finance.ts         # (existing)
│   └── reports.ts         # NEW: fetchPL, fetchBalanceSheet, fetchIncomeStatement + types
├── hooks/
│   └── useReports.ts      # NEW: usePL, useBalanceSheet, useIncomeStatement (manual-fetch hooks)
└── components/
    └── reports/
        ├── ReportsTab.tsx          # REPLACE: sub-tab shell (P&L | Balance Sheet | Income Statement)
        ├── PLTab.tsx               # NEW: P&L report viewer
        ├── BalanceSheetTab.tsx     # NEW: Balance Sheet viewer
        ├── IncomeStatementTab.tsx  # NEW: Income Statement viewer
        ├── ReportFilters.tsx       # NEW: shared preset + custom date controls + Generate button
        ├── ReportSection.tsx       # NEW: collapsible section card (reusable across all 3 reports)
        └── MonthlyTable.tsx        # NEW: horizontal-scroll monthly breakdown table
```

### Pattern 1: Sub-Tab Navigation (URL-synced)

Match the FinanceTab pattern exactly — `useSearchParams` with a `rtab` param (use `rtab` to distinguish from `ftab`):

```typescript
// Source: verified from src/components/finance/FinanceTab.tsx
import { useSearchParams } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'

type ReportsSubTab = 'pl' | 'balance-sheet' | 'income-statement'
const VALID_SUBTABS: ReportsSubTab[] = ['pl', 'balance-sheet', 'income-statement']

function isValidSubTab(value: string | null): value is ReportsSubTab {
  return VALID_SUBTABS.includes(value as ReportsSubTab)
}

export function ReportsTab() {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawSubTab = searchParams.get('rtab')
  const activeSubTab: ReportsSubTab = isValidSubTab(rawSubTab) ? rawSubTab : 'pl'

  function handleSubTabChange(value: string) {
    const newParams = new URLSearchParams(searchParams)
    if (value === 'pl') {
      newParams.delete('rtab')
    } else {
      newParams.set('rtab', value)
    }
    setSearchParams(newParams)
  }

  return (
    <div className="space-y-4">
      <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
        <div className="overflow-x-auto">
          <TabsList>
            <TabsTrigger value="pl">P&amp;L</TabsTrigger>
            <TabsTrigger value="balance-sheet">Balance Sheet</TabsTrigger>
            <TabsTrigger value="income-statement">Income Statement</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="pl"><PLTab /></TabsContent>
        <TabsContent value="balance-sheet"><BalanceSheetTab /></TabsContent>
        <TabsContent value="income-statement"><IncomeStatementTab /></TabsContent>
      </Tabs>
    </div>
  )
}
```

### Pattern 2: Manual-Fetch Query (Generate Button)

TanStack Query v5's canonical pattern for user-triggered fetches: use a `params` state that starts as `null` and is set when the user clicks Generate. Set `enabled: params !== null`. The query key includes the params object so changing params on a subsequent Generate triggers a fresh fetch.

```typescript
// Source: TanStack Query v5 docs (https://tanstack.com/query/v5/docs/framework/react/guides/disabling-queries)
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchPL, type PLParams } from '@/api/reports'

export function usePL() {
  const [params, setParams] = useState<PLParams | null>(null)

  const query = useQuery({
    queryKey: ['reports', 'pl', params],
    queryFn: () => fetchPL(params!),
    enabled: params !== null,
    staleTime: 5 * 60 * 1000,
  })

  return { ...query, generate: setParams }
}
```

In the component:
```typescript
const { data, isFetching, isError, generate } = usePL()

function handleGenerate() {
  generate({ start_date: '2026-01-01', end_date: '2026-12-31', breakdown: 'combined' })
}

// Button state
<Button onClick={handleGenerate} disabled={isFetching}>
  {isFetching ? 'Generating...' : 'Generate'}
</Button>
```

**Why `isFetching` not `isLoading`:** `isLoading` is true only when there is no cached data. `isFetching` is true during any active network request — use this to disable the button during all fetches including re-generates with new params.

### Pattern 3: Collapsible Section Cards

Use the already-installed `Collapsible` primitive. Sections are expanded by default (`defaultOpen`):

```typescript
// Source: verified from src/components/ui/collapsible.tsx (radix-ui primitive)
import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

interface ReportSectionProps {
  title: string
  total: string
  children: React.ReactNode
}

export function ReportSection({ title, total, children }: ReportSectionProps) {
  const [open, setOpen] = useState(true)

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card>
        <CardHeader className="pb-2">
          <CollapsibleTrigger asChild>
            <button className="flex w-full items-center justify-between">
              <CardTitle className="text-base">{title}</CardTitle>
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold tabular-nums">{total}</span>
                {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </div>
            </button>
          </CollapsibleTrigger>
        </CardHeader>
        <CollapsibleContent>
          <CardContent>{children}</CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  )
}
```

### Pattern 4: Preset Date Buttons

Preset buttons are a row of outlined Button variants. The active preset gets a filled/primary variant. Custom date range uses two `Input` fields (start/end date, type="date"). The presets compute start/end dates client-side.

```typescript
// Preset computation (client-side, no library needed)
function getPresetDates(preset: string): { start: string; end: string } | { as_of: string } {
  const today = new Date()
  const year = today.getFullYear()
  const month = today.getMonth() + 1  // 1-indexed

  switch (preset) {
    case 'this-month': {
      const lastDay = new Date(year, month, 0).getDate()
      return { start: `${year}-${String(month).padStart(2,'0')}-01`,
               end:   `${year}-${String(month).padStart(2,'0')}-${lastDay}` }
    }
    case 'this-quarter': {
      const q = Math.ceil(month / 3)
      const qStart = (q - 1) * 3 + 1
      const qEnd = q * 3
      const lastDay = new Date(year, qEnd, 0).getDate()
      return { start: `${year}-${String(qStart).padStart(2,'0')}-01`,
               end:   `${year}-${String(qEnd).padStart(2,'0')}-${lastDay}` }
    }
    case 'ytd':
      return { start: `${year}-01-01`, end: today.toISOString().split('T')[0] }
    case 'last-year':
      return { start: `${year-1}-01-01`, end: `${year-1}-12-31` }
    default:
      return { start: '', end: '' }
  }
}
```

### Pattern 5: Number Formatting (Claude's Discretion — Recommended Approach)

**Recommendation for non-accountant readability:** Use red text with parentheses for negative values, no special formatting for positive. This is the standard non-accountant financial style (used in personal finance apps). Zero values display as "—" (em-dash).

```typescript
function formatAmount(value: string): { display: string; isNegative: boolean; isZero: boolean } {
  const num = parseFloat(value)
  if (isNaN(num) || num === 0) return { display: '—', isNegative: false, isZero: true }
  const formatted = Math.abs(num).toLocaleString('en-US', { style: 'currency', currency: 'USD' })
  return {
    display: num < 0 ? `(${formatted})` : formatted,
    isNegative: num < 0,
    isZero: false,
  }
}

// Usage in JSX:
function AmountCell({ value }: { value: string }) {
  const { display, isNegative } = formatAmount(value)
  return (
    <td className={`text-right tabular-nums ${isNegative ? 'text-red-600 dark:text-red-400' : ''}`}>
      {display}
    </td>
  )
}
```

**P&L percentage column:** `(lineAmount / revenueTotal * 100).toFixed(1) + '%'`. Show "—" if revenue total is zero.

### Pattern 6: Monthly Table Layout (Claude's Discretion — Recommended Approach)

**Recommendation:** Horizontal scroll with pinned first column (line item labels). This is better than limiting months because the user selected the date range intentionally. Use `overflow-x-auto` on the wrapper and `sticky left-0 bg-card` on the label column.

```typescript
// Monthly table pattern — horizontal scroll with sticky label column
<div className="overflow-x-auto print:overflow-visible">
  <table className="w-full min-w-max text-sm">
    <thead>
      <tr>
        <th className="sticky left-0 bg-card px-3 py-2 text-left font-medium min-w-[180px]">
          Account
        </th>
        {months.map(m => (
          <th key={m} className="px-3 py-2 text-right font-medium whitespace-nowrap">
            {formatMonthLabel(m)}  {/* "Jan 2026" */}
          </th>
        ))}
        <th className="px-3 py-2 text-right font-medium whitespace-nowrap">Total</th>
      </tr>
    </thead>
    <tbody>
      {/* rows */}
    </tbody>
  </table>
</div>
```

### Pattern 7: Print CSS

Tailwind v4 has a built-in `print:` variant. The strategy is:
1. Add `print:hidden` to the `Header` and `TabsList` elements via class names (or wrap in a `print:hidden` div).
2. Add `@media print` rules in `index.css` for layout normalization (remove padding, ensure full width).

Since `Header.tsx` and `AppShell.tsx` are shared components, the cleanest approach is to wrap the header and main tab bar in divs with `print:hidden` inside those files rather than adding global print rules. Only the active report content should appear on print.

```css
/* Add to index.css @layer utilities or directly in @layer base */
@media print {
  .report-print-target {
    padding: 0;
    margin: 0;
  }
}
```

Or purely with Tailwind utility classes (no CSS changes needed):
```tsx
// In AppShell.tsx — add print:hidden to the header and tabs list wrappers
<Header className="print:hidden" />   // (requires Header to accept className)
<div className="mb-6 overflow-x-auto print:hidden">
  <TabsList>...</TabsList>
</div>
```

**Note:** The `Header` component currently does not accept a `className` prop. Adding `print:hidden` will require either: (a) adding `className` prop to Header, or (b) wrapping the `<Header />` call in AppShell with `<div className="print:hidden"><Header /></div>`. Option (b) is non-invasive.

### Pattern 8: Balance Sheet Totals Sub-View

Balance sheet is point-in-time, so `as_of` maps to the end date of the selected preset. Mapping:
- "This Month" → last day of current month
- "This Quarter" → last day of current quarter
- "YTD" → today's date
- "Last Year" → Dec 31 of last year
- Custom → user-selected end date

The balance sheet only shows totals (no monthly drill-down). It still uses the `ReportSection` collapsible card pattern for Assets, Liabilities, Equity.

Section ordering recommendation (standard balance sheet order): Assets first, then Liabilities, then Equity, with a "Total Liabilities & Equity" row at the bottom matching `total_liabilities_and_equity`.

**Balance check:** Display a visual indicator if `assets.total !== total_liabilities_and_equity`. In a well-functioning accounting system this should always balance, but display it for transparency.

### Anti-Patterns to Avoid

- **Auto-fetch on filter change:** Do not set `enabled: true` based on filter state. This causes a request on every keystroke or dropdown change. Only fetch on Generate button click.
- **Parsing Decimal strings with `Number()`:** Use `parseFloat()` for display math, but never for financial storage. The backend sends strings precisely to avoid float precision loss.
- **Re-implementing Collapsible:** The `Collapsible` component from `ui/collapsible.tsx` already wraps radix-ui. Do not use a raw `useState` + `div` expand/collapse pattern.
- **Using `isLoading` to disable Generate button:** `isLoading` is false on re-fetches when cached data exists. Use `isFetching` to disable the button during all active fetches.
- **Monthly table without sticky labels:** Without `sticky left-0` on the label column, horizontal scrolling on mobile makes the table unreadable as label context scrolls out of view.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Collapsible sections | Custom `useState` + CSS height transition | `Collapsible` from `ui/collapsible.tsx` | Already installed, accessible, keyboard-navigable |
| Tab navigation | Custom tab state | `Tabs`/`TabsList`/`TabsTrigger` from `ui/tabs.tsx` | Already installed, URL-synced via `useSearchParams` |
| Currency formatting | Custom string formatter | `toLocaleString('en-US', { style: 'currency', currency: 'USD' })` | Native, handles locale edge cases |
| Loading skeletons | Custom shimmer divs | `Skeleton` from `ui/skeleton.tsx` + animate-pulse divs | Already installed, consistent style |
| Error handling | Custom error UI | `ErrorAlert` from `shared/ErrorAlert.tsx` | Already installed, consistent retry pattern |
| Empty state | Custom "no data" UI | `EmptyState` from `shared/EmptyState.tsx` | Already installed |
| Date math (last day of month) | Custom calendar math | `new Date(year, month, 0).getDate()` | Native JS, no library needed |

**Key insight:** Every infrastructure problem in this phase is already solved by existing components. The work is purely composition — wiring the API responses into the established UI patterns.

---

## Common Pitfalls

### Pitfall 1: P&L `breakdown=property` vs property selector

**What goes wrong:** Developer uses `breakdown=property` when a property is selected in the header, receives all properties in the response, and must match by display_name string. This is fragile — display_name could change.

**Why it happens:** The property selector stores `selectedPropertyId` (number), but the P&L property breakdown keys by `display_name` (string). There is no `property_id` in the top-level keys of the `properties` object, only nested `property_id` values.

**How to avoid:** Use `breakdown=combined` for all Phase 12 P&L calls. The global property selector's "Combined" option maps to combined mode. Individual property breakdown is a future enhancement requiring a cross-reference lookup.

**Warning signs:** TypeScript error trying to use `selectedPropertyId` directly as a key into `response.properties`.

### Pitfall 2: Balance Sheet `as_of` Mapping for Presets

**What goes wrong:** Developer sends `start_date` + `end_date` to the balance sheet endpoint. The balance sheet API only accepts `as_of` (a single date), not a range.

**Why it happens:** P&L and Income Statement both accept start/end range. Balance Sheet is different — it's a snapshot.

**How to avoid:** In the filter component, compute `as_of` from the preset's end date, not the start date. The `ReportFilters` component needs a `mode` prop (`'range' | 'snapshot'`) that changes what it passes to the Generate handler.

**Warning signs:** HTTP 422 from the balance sheet endpoint saying `as_of` is required.

### Pitfall 3: Missing "Prompt Before Generate" State

**What goes wrong:** On first render, the report area is empty with no context. User doesn't know they need to click Generate.

**Why it happens:** The manual-fetch pattern starts with `data = undefined` and `params = null`. Nothing tells the user what to do.

**How to avoid:** Show a prompt state (distinct from EmptyState) when `params === null` (no generate has been clicked yet). This is different from the EmptyState (which shows when Generate was clicked but returned no data).

```typescript
if (params === null) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-2">
      <p className="text-sm text-muted-foreground">Select a date range and click Generate to view the report.</p>
    </div>
  )
}
```

### Pitfall 4: TanStack Query Cache Key Collision Between Reports

**What goes wrong:** All three reports use similar filter shapes. If query keys are not namespaced per-report, cached data from one report can bleed into another.

**Why it happens:** A query key like `['reports', params]` without the report type would collide.

**How to avoid:** Include the report type in the query key: `['reports', 'pl', params]`, `['reports', 'balance-sheet', params]`, `['reports', 'income-statement', params]`.

### Pitfall 5: `isFetching` True During Background Refetches

**What goes wrong:** The Generate button remains disabled when the user switches away and back to the tab, because TanStack Query triggers a background refetch on remount.

**Why it happens:** `isFetching` is true during all fetches, including background refetches that happen due to `staleTime` expiry.

**How to avoid:** Set `staleTime: 5 * 60 * 1000` (5 minutes) on report queries. Reports are not real-time data — 5 minutes stale is appropriate. This reduces background refetch frequency significantly.

### Pitfall 6: Print CSS Hiding Report Content

**What goes wrong:** Adding `print:hidden` to AppShell parent containers accidentally hides the active report content.

**Why it happens:** The tab content is inside the same `<main>` that contains the tabs navigation. Hiding the wrong level hides everything.

**How to avoid:** Apply `print:hidden` only to the `<Header />` wrapper and the `<div className="mb-6 overflow-x-auto">` that contains the `TabsList`. The `<TabsContent>` for the active report should NOT have print:hidden. The `TabsContent` for inactive tabs is already rendered as hidden by Radix (display:none), so they won't print anyway.

---

## Code Examples

### `src/api/reports.ts` — Fetch Functions

```typescript
// Source: verified pattern from src/api/finance.ts
import { apiFetch } from '@/api/client'

// ----- Types -----

export interface PLParams {
  start_date?: string
  end_date?: string
  month?: number
  quarter?: string
  year?: number
  ytd?: boolean
  breakdown?: 'combined' | 'property'
}

export interface BalanceSheetParams {
  as_of: string  // ISO date
}

export interface IncomeStatementParams {
  start_date?: string
  end_date?: string
  month?: number
  quarter?: string
  year?: number
  ytd?: boolean
  breakdown?: 'totals' | 'monthly'
}

// ----- Response Types -----

export interface PLCombinedResponse {
  period: { start_date: string; end_date: string }
  breakdown: 'combined'
  revenue: {
    by_platform: Record<string, { months: Array<{ month: string; amount: string }>; subtotal: string }>
    total: string
  }
  expenses: {
    by_category: Record<string, string>
    total: string
  }
  net_income: string
}

export interface BalanceSheetResponse {
  as_of: string
  assets: { accounts: Array<{ number?: string; name: string; balance: string }>; total: string }
  liabilities: { accounts: Array<{ number?: string; name: string; balance: string }>; total: string }
  equity: { accounts: Array<{ name: string; balance: string }>; total: string }
  total_liabilities_and_equity: string
}

export interface IncomeStatementTotalsResponse {
  period: { start_date: string; end_date: string }
  breakdown: 'totals'
  revenue: { by_account: Record<string, string>; total: string }
  expenses: { by_account: Record<string, string>; total: string }
  net_income: string
}

export interface IncomeStatementMonthlyResponse {
  period: { start_date: string; end_date: string }
  breakdown: 'monthly'
  months: Array<{
    month: string
    revenue: { by_account: Record<string, string>; total: string }
    expenses: { by_account: Record<string, string>; total: string }
    net_income: string
  }>
  totals: {
    revenue: { by_account: Record<string, string>; total: string }
    expenses: { by_account: Record<string, string>; total: string }
    net_income: string
  }
}

// ----- Fetch Functions -----

export function fetchPL(params: PLParams): Promise<PLCombinedResponse> {
  const qs = new URLSearchParams()
  if (params.start_date) qs.set('start_date', params.start_date)
  if (params.end_date) qs.set('end_date', params.end_date)
  if (params.month != null) qs.set('month', String(params.month))
  if (params.quarter) qs.set('quarter', params.quarter)
  if (params.year != null) qs.set('year', String(params.year))
  if (params.ytd) qs.set('ytd', 'true')
  qs.set('breakdown', params.breakdown ?? 'combined')
  return apiFetch<PLCombinedResponse>(`/reports/pl?${qs.toString()}`)
}

export function fetchBalanceSheet(params: BalanceSheetParams): Promise<BalanceSheetResponse> {
  return apiFetch<BalanceSheetResponse>(`/reports/balance-sheet?as_of=${params.as_of}`)
}

export function fetchIncomeStatement(params: IncomeStatementParams): Promise<IncomeStatementTotalsResponse | IncomeStatementMonthlyResponse> {
  const qs = new URLSearchParams()
  if (params.start_date) qs.set('start_date', params.start_date)
  if (params.end_date) qs.set('end_date', params.end_date)
  if (params.month != null) qs.set('month', String(params.month))
  if (params.quarter) qs.set('quarter', params.quarter)
  if (params.year != null) qs.set('year', String(params.year))
  if (params.ytd) qs.set('ytd', 'true')
  qs.set('breakdown', params.breakdown ?? 'totals')
  return apiFetch<IncomeStatementTotalsResponse | IncomeStatementMonthlyResponse>(`/reports/income-statement?${qs.toString()}`)
}
```

### `src/hooks/useReports.ts` — Manual-Fetch Hooks

```typescript
// Source: TanStack Query v5 manual-fetch pattern
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  fetchPL, fetchBalanceSheet, fetchIncomeStatement,
  type PLParams, type BalanceSheetParams, type IncomeStatementParams,
} from '@/api/reports'

export function usePL() {
  const [params, setParams] = useState<PLParams | null>(null)
  const query = useQuery({
    queryKey: ['reports', 'pl', params],
    queryFn: () => fetchPL(params!),
    enabled: params !== null,
    staleTime: 5 * 60 * 1000,
  })
  return { ...query, generate: setParams, hasGenerated: params !== null }
}

export function useBalanceSheet() {
  const [params, setParams] = useState<BalanceSheetParams | null>(null)
  const query = useQuery({
    queryKey: ['reports', 'balance-sheet', params],
    queryFn: () => fetchBalanceSheet(params!),
    enabled: params !== null,
    staleTime: 5 * 60 * 1000,
  })
  return { ...query, generate: setParams, hasGenerated: params !== null }
}

export function useIncomeStatement() {
  const [params, setParams] = useState<IncomeStatementParams | null>(null)
  const query = useQuery({
    queryKey: ['reports', 'income-statement', params],
    queryFn: () => fetchIncomeStatement(params!),
    enabled: params !== null,
    staleTime: 5 * 60 * 1000,
  })
  return { ...query, generate: setParams, hasGenerated: params !== null }
}
```

### Subtotal Row Shading Pattern

Per the context decision: subtotals get subtle tint, grand totals get darker tint. Use Tailwind background utilities:

```typescript
// Subtotal row (platform subtotal, section total)
<tr className="bg-muted/30 font-medium">
  <td>Subtotal</td>
  <td className="text-right tabular-nums">{formatCurrency(subtotal)}</td>
</tr>

// Grand total row (net income, total assets, etc.)
<tr className="bg-muted/60 font-semibold border-t-2">
  <td>Net Income</td>
  <td className="text-right tabular-nums">{formatCurrency(netIncome)}</td>
</tr>
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Eager fetch on mount | `enabled: params !== null` with Generate button | Prevents wasted requests during filter adjustment |
| `page-break-*` CSS properties | `break-before`, `break-after`, `break-inside` | Modern paged media support |
| Separate print stylesheet | Tailwind `print:` variant | Collocated print styles, no separate file |
| TanStack Query v4 `isInitialLoading` | v5 `isLoading` (same semantics as v4's `isInitialLoading`) | v5 renamed for clarity |

**Deprecated/outdated:**
- TanStack Query v4 `isInitialLoading`: renamed to `isLoading` in v5. This project uses v5. Use `isLoading` for "no data + fetching" and `isFetching` for "any active request."

---

## Open Questions

1. **P&L per-property display for Phase 12**
   - What we know: The `breakdown=property` API response keys by `display_name`, not `property_id`. The frontend store has `selectedPropertyId` (number).
   - What's unclear: Should Phase 12 show per-property P&L columns, or just "Combined" mode?
   - Recommendation: Implement `breakdown=combined` only. The context doc says to use the global property selector with a "Combined" option — this maps to combined mode. Per-property breakdown can be a Phase 13 enhancement if needed.

2. **Balance Sheet `as_of` for "This Quarter" and "This Month" presets**
   - What we know: The preset must resolve to a single date. "This Month" → last day of month. "This Quarter" → last day of quarter.
   - What's unclear: Should "YTD" map to today's date or end of current month?
   - Recommendation: Map "YTD" to today's date for balance sheet (most current snapshot). Document this choice in a code comment.

3. **Income Statement Monthly view account row structure**
   - What we know: The monthly response has `by_account` per month, but different months may have different account sets (accounts with zero activity in a month simply don't appear).
   - What's unclear: How should the table handle accounts that are missing from some months?
   - Recommendation: Collect all unique account names across all months first, then render each account as a row with "—" for months where it doesn't appear in `by_account`. This gives a consistent row structure.

---

## Sources

### Primary (HIGH confidence)

- Actual project source files — `src/api/reports.py`, `src/api/finance.ts`, `src/components/finance/FinanceTab.tsx`, `src/components/layout/AppShell.tsx`, `src/components/ui/collapsible.tsx`, `src/index.css`, `frontend/package.json` — verified 2026-03-02
- TanStack Query v5 docs (https://tanstack.com/query/v5/docs/framework/react/guides/disabling-queries) — manual-fetch pattern with `enabled: false`
- Tailwind CSS v4 responsive docs (https://tailwindcss.com/docs/responsive-design) — `print:` variant confirmed as built-in

### Secondary (MEDIUM confidence)

- WebSearch result: "Tailwind CSS v4 print media query @media print CSS 2026" — confirmed `print:` variant existence, cross-referenced with official docs
- WebSearch result: "TanStack Query v5 enabled: false lazy query generate button" — confirmed `enabled: false` + `refetch` pattern, cross-referenced with official docs

### Tertiary (LOW confidence)

- None — all critical findings verified against project source or official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against `package.json` and `node_modules`
- API shapes: HIGH — verified against actual Python source in `app/accounting/reports.py` and `app/api/reports.py`
- Architecture: HIGH — verified by reading existing Phase 11 patterns in `FinanceTab.tsx`, `AppShell.tsx`
- Manual-fetch pattern: HIGH — verified against TanStack Query v5 official docs
- Print CSS: HIGH — verified against Tailwind v4 official docs
- Pitfalls: HIGH — derived from direct code inspection, not speculation

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable stack, 30-day window)

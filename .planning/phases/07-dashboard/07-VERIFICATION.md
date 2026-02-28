---
phase: 07-dashboard
verified: 2026-02-28T23:37:37Z
status: gaps_found
score: 4/5 must-haves verified
gaps:
  - truth: "Pending actions are visible on the dashboard and dismissable when actioned"
    status: partial
    reason: "The 'Submit' button for resort forms calls a non-existent API path. The frontend ActionItem calls POST /api/compliance/submissions/{booking_id}/submit but the actual backend endpoint is POST /api/compliance/submit/{booking_id}. Resort form submissions will fail with 404 at runtime. VRBO message confirmation is wired correctly."
    artifacts:
      - path: "frontend/src/components/actions/ActionItem.tsx"
        issue: "Line 84: apiFetch call uses path /compliance/submissions/{booking_id}/submit — this path does not exist on the backend"
    missing:
      - "Correct the apiFetch path in ActionItem.tsx submitFormMutation from /compliance/submissions/${booking_id}/submit to /compliance/submit/${booking_id}"
---

# Phase 7: Dashboard Verification Report

**Phase Goal:** Users can see the operational state of the business at a glance — financials, occupancy, upcoming bookings, and pending actions — from a clean interface that non-technical users can navigate
**Verified:** 2026-02-28T23:37:37Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Dashboard home page shows YTD revenue, YTD expenses, and current-month profit for each property without any navigation | VERIFIED | HomeTab renders 3 StatCards wired to useMetrics() -> GET /api/dashboard/metrics. Backend returns ytd_revenue, ytd_expenses, current_month_profit from JournalLine aggregation. Property selector in Header filters all data. |
| 2 | User can see occupancy rate and a booking trend chart for each property covering the last 12 months | VERIFIED | BookingTrendChart fetches /api/dashboard/bookings with 12-month date range and stacks by platform (159 lines, substantive). OccupancyChart shows current occupancy rate per property as donut. Backend occupancy endpoint computes 12-month window. |
| 3 | A calendar view shows all upcoming and past bookings across both properties in a single view, color-coded by platform | VERIFIED | CalendarTab renders MonthCalendar (376 lines) with BookingBar components colored via getPlatformColorEntry(booking.platform). TimelineView (351 lines) provides Gantt view. Both wired to useBookings() -> GET /api/dashboard/bookings. BookingPopover shows platform dot with chart color. |
| 4 | Pending actions are visible on the dashboard and dismissable when actioned | PARTIAL | Actions visible: ActionsTab correctly fetches /api/dashboard/actions and renders sorted accordion list. VRBO message confirmation is correctly wired to POST /api/communication/confirm/{log_id}. Resort form "Submit" button is broken: ActionItem.tsx line 84 calls /api/compliance/submissions/{booking_id}/submit but the actual backend endpoint is /api/compliance/submit/{booking_id}. Resort form actions cannot be dismissed. |
| 5 | Kim can use the dashboard to check financial and booking status without requiring explanation of financial concepts | VERIFIED | StatCards include shadcn Tooltip on each title with plain-English explanations ("Total income from all bookings this year", "Total costs including rent, utilities, and maintenance this year", "Revenue minus expenses for this month"). Labels use plain terms (Revenue, Expenses, Profit) not accounting jargon. Dark mode, loading skeletons, and EmptyState components provide a polished non-technical experience. |

**Score:** 4/5 truths verified (1 partial due to broken API wiring)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/api/dashboard.py` | 5 GET endpoints for properties, metrics, bookings, occupancy, actions | VERIFIED | 566 lines. All 5 endpoints implemented with real DB queries, property filter, error handling. Registered in app/main.py line 141 before SPA mount. |
| `frontend/src/App.tsx` | QueryClientProvider + BrowserRouter wrapping AppShell | VERIFIED | 25 lines. QueryClient with retry:1, staleTime:5min. Wraps AppShell correctly. |
| `frontend/src/components/layout/AppShell.tsx` | 4-tab navigation, URL sync, Actions badge | VERIFIED | 95 lines. Tabs (Home/Calendar/Reports/Actions), useSearchParams URL sync, live actions badge count via TanStack Query cache sharing. |
| `frontend/src/components/layout/Header.tsx` | Property selector + dark mode toggle | VERIFIED | 82 lines. shadcn Select with /api/dashboard/properties, dark mode via document.documentElement class toggle, localStorage persistence. |
| `frontend/src/components/home/HomeTab.tsx` | Layout grid with 3 stat cards + 2 charts + actions preview | VERIFIED | 70 lines. Responsive 3-col grid for stat cards, 2/3 + 1/3 chart layout on lg, full-width ActionsPreview. |
| `frontend/src/components/home/StatCard.tsx` | Stat card with YoY comparison and tooltip | VERIFIED | 69 lines. shadcn Card, TrendingUp/Down icons, shadcn Tooltip with plain-language explanations, SkeletonCard on loading. |
| `frontend/src/components/home/BookingTrendChart.tsx` | Stacked bar chart 12 months by platform | VERIFIED | 159 lines. Recharts BarChart in ChartContainer, client-side aggregation of bookings by check_in month and platform, dynamic platform stacking. |
| `frontend/src/components/home/OccupancyChart.tsx` | Donut chart per property + legend | VERIFIED | 137 lines. Recharts PieChart with innerRadius, center avg text overlay, per-property legend with percentages. |
| `frontend/src/components/home/ActionsPreview.tsx` | Pending count card linking to Actions tab | VERIFIED | 74 lines. useActions() hook, type breakdown, clickable to Actions tab via setSearchParams. |
| `frontend/src/components/calendar/CalendarTab.tsx` | Month/timeline toggle, date navigation, loading/error states | VERIFIED | 152 lines. Month state, viewMode toggle, useBookings hook, CalendarSkeleton, ErrorAlert, EmptyState. |
| `frontend/src/components/calendar/MonthCalendar.tsx` | 7-col CSS Grid, booking bars, week splits, stacking | VERIFIED | 376 lines. splitIntoWeekSegments(), assignRowOffsets(), absolute-positioned BookingBar via BookingPopover. |
| `frontend/src/components/calendar/TimelineView.tsx` | Gantt grid, property rows, day columns | VERIFIED | 351 lines. CSS Grid 140px + repeat(N,1fr), height:0/overflow:visible bars, weekend shading, sticky label. |
| `frontend/src/components/calendar/BookingBar.tsx` | Platform-colored bar with selective rounded corners | VERIFIED | 73 lines. getPlatformColorEntry().light fill, selective border-radius, % left/width positioning. |
| `frontend/src/components/calendar/BookingPopover.tsx` | Click detail popover with platform dot | VERIFIED | 92 lines. shadcn Popover, getPlatformColorEntry().chart dot, guest name, dates, nights, payout, property. |
| `frontend/src/components/actions/ActionsTab.tsx` | Loading/error/empty states + ActionsList | VERIFIED | 47 lines. Skeleton rows, ErrorAlert, EmptyState, renders ActionsList. |
| `frontend/src/components/actions/ActionsList.tsx` | Accordion wrapper for action items | VERIFIED | 26 lines. shadcn Accordion type="single" collapsible. |
| `frontend/src/components/actions/ActionItem.tsx` | Expandable item with action buttons | PARTIAL | 234 lines. resort_form Submit button wired to wrong API path (line 84). vrbo_message Mark as Sent wired correctly. unreconciled shows informational text correctly. |
| `frontend/src/components/reports/ReportsTab.tsx` | Reports placeholder with API endpoints | VERIFIED | 57 lines. 3 cards listing P&L, Balance Sheet, Income Statement with endpoints. Intentional placeholder per plan spec. |
| `frontend/src/hooks/useFinancials.ts` | useMetrics() + useOccupancy() hooks | VERIFIED | 52 lines. Both hooks read selectedPropertyId from Zustand, include it in queryKey, staleTime 5min. |
| `frontend/src/hooks/useActions.ts` | useActions() with typed discriminated union | VERIFIED | 53 lines. ResortFormAction | VrboMessageAction | UnreconciledAction union type, same queryKey pattern. |
| `frontend/src/hooks/useBookings.ts` | useBookings(startDate, endDate) hook | VERIFIED | 36 lines. property filter in queryKey, date params forwarded to API. |
| `frontend/src/store/usePropertyStore.ts` | Zustand store with localStorage persistence | VERIFIED | 19 lines. create() with persist middleware, selectedPropertyId: number | null. |
| `frontend/src/lib/platformColors.ts` | Platform color map with light/dark/chart variants | VERIFIED | 58 lines. PLATFORM_COLORS for airbnb/vrbo/rvshare, getPlatformColorEntry(), RECHARTS_PLATFORM_COLORS. |
| `frontend/src/api/client.ts` | apiFetch<T> typed wrapper with /api prefix | VERIFIED | 36 lines. Prepends /api, JSON headers, error parsing from detail field. |
| `frontend/src/components/shared/EmptyState.tsx` | Reusable empty state text component | VERIFIED | 19 lines. Centered muted text, no icons per CONTEXT.md directive. |
| `Dockerfile` | Multi-stage Node build + Python stage | VERIFIED | 36 lines. Node:22-alpine frontend-build stage, npm ci + npm run build, COPY --from=frontend-build. |
| `app/main.py` | dashboard_router registered, SPAStaticFiles | VERIFIED | 147 lines. dashboard_router included line 141. SPAStaticFiles with os.path.isdir guard, CORSMiddleware. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `Header.tsx` | `GET /api/dashboard/properties` | TanStack Query + apiFetch | WIRED | Fetches property list to populate selector |
| `useFinancials.ts useMetrics()` | `GET /api/dashboard/metrics` | TanStack Query + apiFetch | WIRED | selectedPropertyId in queryKey triggers refetch |
| `useFinancials.ts useOccupancy()` | `GET /api/dashboard/occupancy` | TanStack Query + apiFetch | WIRED | selectedPropertyId in queryKey triggers refetch |
| `useActions.ts` | `GET /api/dashboard/actions` | TanStack Query + apiFetch | WIRED | Same queryKey as AppShell badge — shared cache |
| `BookingTrendChart.tsx` | `GET /api/dashboard/bookings` | useQuery + apiFetch | WIRED | 12-month date range, client-side aggregation by month+platform |
| `useBookings.ts` | `GET /api/dashboard/bookings` | TanStack Query + apiFetch | WIRED | start_date/end_date + property_id params forwarded |
| `AppShell.tsx` | `usePropertyStore.ts` | Zustand import | WIRED | selectedPropertyId used in badge query |
| `ActionItem.tsx` | `POST /api/communication/confirm/{log_id}` | useMutation + apiFetch | WIRED | vrbo_message "Mark as Sent" correctly calls confirm endpoint |
| `ActionItem.tsx` | `POST /api/compliance/submit/{booking_id}` | useMutation + apiFetch | NOT_WIRED | resort_form "Submit" calls wrong path: /compliance/submissions/{id}/submit instead of /compliance/submit/{id} |
| `app/main.py` | `app/api/dashboard.py` | include_router | WIRED | dashboard_router registered at line 141, before SPA mount |
| `Dockerfile frontend-build` | `frontend/dist` | npm run build | WIRED | COPY --from=frontend-build /frontend/dist ./frontend/dist |
| `app/main.py SPAStaticFiles` | `frontend/dist` | os.path.isdir guard + mount | WIRED | SPA fallback active when dist exists |

---

## Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| DASH-01: Dashboard home shows YTD financials per property | SATISFIED | Verified: HomeTab stat cards wired to live metrics endpoint |
| DASH-02: Occupancy rate and booking trend chart per property | SATISFIED | Verified: OccupancyChart (current rate per property) + BookingTrendChart (12-month stacked) both wired to backend |
| DASH-03: Calendar view of bookings color-coded by platform | SATISFIED | Verified: CalendarTab with MonthCalendar + TimelineView, bars use platform light colors, popovers use chart colors |
| DASH-07: Pending actions visible and dismissable | BLOCKED | resort_form dismiss (Submit button) calls wrong API path — returns 404. vrbo_message dismiss works. |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/reports/ReportsTab.tsx` | 52 | "Full report views coming soon" | Info | Expected — Reports tab is an intentional placeholder per plan spec. Phase 8 will add report UI. No impact on phase 7 goals. |
| `frontend/src/components/actions/ActionItem.tsx` | 84 | Wrong API path in mutationFn | Blocker | Resort form "Submit" button will 404 at runtime. Actions cannot be dismissed for resort_form type. |

---

## Human Verification Required

The following items cannot be verified programmatically and need human testing once the gap is closed:

### 1. Dark Mode Visual Consistency

**Test:** Toggle dark mode, navigate through all 4 tabs (Home, Calendar, Reports, Actions)
**Expected:** All components render with correct dark palette. Calendar booking bars, chart colors, and popover content all visible against dark background.
**Why human:** CSS rendering correctness requires visual inspection.

### 2. Mobile Responsiveness

**Test:** View dashboard on a mobile screen (or DevTools mobile viewport at 375px width)
**Expected:** Tabs scroll horizontally, stat cards stack to single column, charts scale down, calendar is usable.
**Why human:** Layout reflow requires visual verification.

### 3. Property Selector Filter Behavior

**Test:** Select a specific property in the header dropdown, observe stat cards and charts update.
**Expected:** All 3 stat cards, booking trend chart, occupancy chart, and actions preview refresh with data filtered to the selected property.
**Why human:** Data filtering requires a live backend with real data to verify correctly.

### 4. Calendar Booking Bar Rendering

**Test:** Navigate to the Calendar tab when bookings exist across multiple properties/platforms for the displayed month.
**Expected:** Booking bars are color-coded (Airbnb red/pink, VRBO blue, RVshare sky), stacked when overlapping, split at week boundaries. Click shows popover with guest details.
**Why human:** Requires real booking data and visual inspection.

---

## Gaps Summary

**1 gap blocking goal achievement.**

The resort form action dismiss is broken due to an API path mismatch in `frontend/src/components/actions/ActionItem.tsx` line 84. The frontend calls `POST /api/compliance/submissions/{booking_id}/submit` but the backend compliance router exposes `POST /api/compliance/submit/{booking_id}` (prefix `/compliance`, route `/submit/{booking_id}`). Clicking "Submit" on a resort form will produce a 404 error, leaving the action undismissable.

The fix is a one-line change: replace the apiFetch path from:
```
/compliance/submissions/${(item as { booking_id: number }).booking_id}/submit
```
with:
```
/compliance/submit/${(item as { booking_id: number }).booking_id}
```

VRBO message dismissal ("Mark as Sent") is correctly wired and unaffected.

All 4 ROADMAP success criteria are otherwise satisfied:
- YTD financials display on the Home tab without navigation (DASH-01)
- Occupancy and booking trend chart are live and property-filterable (DASH-02)
- Calendar view with platform color-coding works in both month and timeline views (DASH-03)
- Actions are visible on the dashboard — only the resort form "Submit" dismiss is broken (DASH-07 partial)

---

*Verified: 2026-02-28T23:37:37Z*
*Verifier: Claude (gsd-verifier)*

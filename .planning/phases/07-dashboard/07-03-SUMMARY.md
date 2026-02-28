---
phase: 07-dashboard
plan: 03
subsystem: ui
tags: [react, vite, shadcn, recharts, tanstack-query, zustand, react-router, typescript, tailwind]

# Dependency graph
requires:
  - phase: 07-dashboard/07-01
    provides: React 19 + Vite + shadcn/ui scaffold with installed chart/select/tabs/badge/tooltip components
  - phase: 07-dashboard/07-02
    provides: 5 dashboard API endpoints (properties, metrics, bookings, occupancy, actions)
provides:
  - App shell with Header (property selector + dark mode toggle), 4-tab navigation, URL ?tab= sync
  - Zustand store (usePropertyStore) with localStorage-persisted selectedPropertyId
  - Platform color map (Airbnb red, VRBO blue, RVshare sky) with Recharts-compatible fills
  - Home tab with 3 stat cards (YTD Revenue, YTD Expenses, Current Month Profit) with YoY comparison
  - BookingTrendChart: stacked Recharts BarChart by platform for last 12 months
  - OccupancyChart: Recharts PieChart donut with center average text and property legend
  - ActionsPreview: pending action count card with type breakdown, links to Actions tab
  - TanStack Query hooks (useMetrics, useOccupancy, useActions) with selectedPropertyId in query key
  - Shared SkeletonCard and ErrorAlert components
affects:
  - 07-dashboard/07-04 and beyond (Calendar, Reports, Actions tabs to be built on this shell)
  - Phase 08 (LLM query interface will share this shell)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Zustand store with zustand/middleware persist for cross-refresh state
    - TanStack Query staleTime 5 min for dashboard data (low change frequency)
    - selectedPropertyId in every query key — automatic refetch when property changes
    - URL search param (?tab=) synced with shadcn Tabs via react-router-dom useSearchParams
    - Dark mode via .dark class on document.documentElement with localStorage persistence
    - Recharts wrapped in shadcn ChartContainer for consistent CSS variable theming

key-files:
  created:
    - frontend/src/store/usePropertyStore.ts
    - frontend/src/lib/platformColors.ts
    - frontend/src/components/layout/Header.tsx
    - frontend/src/components/layout/AppShell.tsx
    - frontend/src/components/home/HomeTab.tsx
    - frontend/src/components/home/StatCard.tsx
    - frontend/src/components/home/BookingTrendChart.tsx
    - frontend/src/components/home/OccupancyChart.tsx
    - frontend/src/components/home/ActionsPreview.tsx
    - frontend/src/components/shared/SkeletonCard.tsx
    - frontend/src/components/shared/ErrorAlert.tsx
    - frontend/src/hooks/useFinancials.ts
    - frontend/src/hooks/useActions.ts
  modified:
    - frontend/src/App.tsx
    - frontend/src/main.tsx

key-decisions:
  - "selectedPropertyId in every TanStack Query key — property change triggers automatic refetch of all dashboard data without manual invalidation"
  - "BookingTrendChart fetches /api/dashboard/bookings with 12-month date range and aggregates client-side by check_in month and platform — avoids a new API endpoint"
  - "OccupancyChart center text rendered as an overlay div positioned over the donut hole — simpler than a Recharts customized label which requires SVG coordinate math"
  - "AppShell Actions badge uses the same TanStack Query cache entry as useActions hook (same queryKey) — no extra HTTP request for badge count"
  - "Dark mode toggles .dark on document.documentElement (shadcn standard) and persists to localStorage — default is light theme"

patterns-established:
  - "Dashboard hooks pattern: each hook reads selectedPropertyId from Zustand, builds query params, includes propertyId in queryKey"
  - "Chart pattern: shadcn ChartContainer wrapping Recharts for CSS variable color theming and consistent tooltip styling"

# Metrics
duration: 4min
completed: 2026-02-28
---

# Phase 07 Plan 03: Dashboard UI Shell and Home Tab Summary

**React 19 app shell with Header (property selector + dark mode), 4-tab navigation with URL sync, and Home tab featuring YTD stat cards, 12-month stacked booking trend bar chart, and property occupancy donut chart all wired to live API data.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-28T22:17:58Z
- **Completed:** 2026-02-28T22:21:36Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments
- Built complete app shell (Header, AppShell, 4-tab navigation) with URL search param sync and dark mode toggle persisting to localStorage
- Wired all 4 TanStack Query hooks to live dashboard API endpoints with selectedPropertyId in every query key for automatic refetch on property change
- Implemented Home tab with 3 stat cards (YoY comparison with trend icons), stacked bar chart (12 months by platform), donut chart (per-property occupancy with center average text), and actions preview card

## Task Commits

Each task was committed atomically:

1. **Task 1: App shell with header, tabs, property selector, and dark mode** - `25cd545` (feat)
2. **Task 2: Home tab with stat cards, booking trend chart, and occupancy chart** - `5f24a7f` (feat)

**Plan metadata:** (included in final docs commit)

## Files Created/Modified
- `frontend/src/store/usePropertyStore.ts` — Zustand store with localStorage-persisted selectedPropertyId
- `frontend/src/lib/platformColors.ts` — Platform color map (Airbnb/VRBO/RVshare) with Recharts chart fills
- `frontend/src/components/layout/Header.tsx` — Header with shadcn Select property selector and Sun/Moon dark mode toggle
- `frontend/src/components/layout/AppShell.tsx` — Header + shadcn Tabs (4 tabs), Actions badge, ?tab= URL sync, HomeTab rendering
- `frontend/src/components/home/HomeTab.tsx` — Responsive grid layout (stat cards, charts, actions preview)
- `frontend/src/components/home/StatCard.tsx` — shadcn Card with large value, YoY change indicator (green/red), shadcn Tooltip
- `frontend/src/components/home/BookingTrendChart.tsx` — Recharts BarChart stacked by platform, client-side aggregation from /api/dashboard/bookings
- `frontend/src/components/home/OccupancyChart.tsx` — Recharts PieChart donut with center avg text and property legend
- `frontend/src/components/home/ActionsPreview.tsx` — Pending action card with type breakdown, clickable to Actions tab
- `frontend/src/components/shared/SkeletonCard.tsx` — Animated skeleton matching stat card dimensions
- `frontend/src/components/shared/ErrorAlert.tsx` — shadcn Alert with retry button callback
- `frontend/src/hooks/useFinancials.ts` — useMetrics() and useOccupancy() with staleTime 5 min
- `frontend/src/hooks/useActions.ts` — useActions() with typed ActionItem union (resort_form | vrbo_message | unreconciled)
- `frontend/src/App.tsx` — Wrapped with QueryClientProvider + BrowserRouter, renders AppShell
- `frontend/src/main.tsx` — React 19 createRoot (unchanged, already correct)

## Decisions Made
- **selectedPropertyId in every query key:** Property change triggers automatic refetch of all dashboard data without manual cache invalidation — correct Zustand + TanStack Query integration
- **BookingTrendChart fetches /bookings (not a new endpoint):** The existing `/api/dashboard/bookings` endpoint with a 12-month date range returns enough data for client-side aggregation by check_in month and platform — avoids adding a new endpoint
- **OccupancyChart center text as overlay div:** Simpler than Recharts SVG label with coordinate math — positioned absolutely over the donut hole with CSS
- **AppShell Actions badge shares TanStack Query cache with useActions hook:** Both use the same queryKey `['dashboard', 'actions', selectedPropertyId]` — no extra HTTP request for badge count
- **Dark mode default is light:** localStorage key `rental-dashboard-dark-mode` defaults to `false`; the dark palette was already established in index.css from Plan 07-01

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- App shell complete — Calendar, Reports, and Actions tab content can be dropped in as TabsContent children
- All TanStack Query hooks established with correct property filtering pattern
- Platform colors and chart theme ready for reuse in future chart components
- No blockers for Plan 07-04

---
*Phase: 07-dashboard*
*Completed: 2026-02-28*

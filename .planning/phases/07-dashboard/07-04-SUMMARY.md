---
phase: 07-dashboard
plan: 04
subsystem: ui
tags: [react, tanstack-query, css-grid, calendar, gantt, popover, zustand]

# Dependency graph
requires:
  - phase: 07-01
    provides: Vite+React app shell, Tailwind v4, shadcn components
  - phase: 07-02
    provides: /api/dashboard/bookings endpoint with overlap-filter semantics
  - phase: 07-03
    provides: AppShell tab structure, usePropertyStore, platformColors, apiFetch, ErrorAlert

provides:
  - useBookings(startDate, endDate) TanStack Query hook for calendar data
  - MonthCalendar: 7-column CSS Grid with booking bars, week-boundary splitting, stacking, navigation
  - BookingBar: platform-colored bar with rounded corner semantics for multi-week spans
  - BookingPopover: shadcn Popover detail card (guest name, dates, nights, platform, amount, property)
  - TimelineView: Gantt-style grid with properties as rows, days as columns, booking blocks
  - CalendarTab: view toggle (month/timeline), month navigation, loading/error states

affects:
  - 07-05 (Actions tab — will follow same pattern for tab content)
  - Any future plan referencing calendar or booking visualization

# Tech tracking
tech-stack:
  added: []
  patterns:
    - CSS Grid with col-span-7 week rows and absolute-positioned booking bars (month view)
    - CSS Grid with 140px sticky property label + repeat(N, 1fr) day columns (timeline view)
    - height:0/overflow:visible overlay pattern for booking bars in grid rows
    - Week-boundary splitting: splitIntoWeekSegments() partitions at Sat→Sun before rendering
    - rowOffset stacking: assignRowOffsets() assigns lowest available row for overlapping bars
    - Booking occupancy: [checkIn, checkOut-1] night semantics (last night is day before checkout)
    - Parse ISO dates as local midnight via new Date(y, m-1, d) to avoid UTC shift

key-files:
  created:
    - frontend/src/hooks/useBookings.ts
    - frontend/src/components/calendar/BookingBar.tsx
    - frontend/src/components/calendar/BookingPopover.tsx
    - frontend/src/components/calendar/MonthCalendar.tsx
    - frontend/src/components/calendar/TimelineView.tsx
    - frontend/src/components/calendar/CalendarTab.tsx
  modified:
    - frontend/src/components/layout/AppShell.tsx

key-decisions:
  - "Booking occupancy is [checkIn, checkOut-1] — last occupied night is the day before checkout"
  - "ISO dates parsed as new Date(y, m-1, d) not new Date(isoStr) — avoids UTC midnight shift to prior day"
  - "BookingBar absolute-positioned within week row div, not as grid items — simpler column math"
  - "TimelineView uses height:0/overflow:visible overlay — bars don't affect CSS Grid row sizing"
  - "getPlatformColorEntry().light used for bar fill (not .chart) — pastel for calendar, chart-red for recharts"
  - "BookingPopover manages its own open state — shadcn Popover handles close-on-click-outside natively"
  - "Week-boundary split is flat (no rounding) on split side, rounded on booking start/end only"
  - "Property label column sticky on horizontal scroll in TimelineView via sticky left-0 z-10"

patterns-established:
  - "Calendar views: week-row container + absolute booking bars (not grid items for bars)"
  - "Timeline rows: label col sticky + day cells + height:0 overlay grid items for bars"
  - "Stack assignment: O(n²) greedy lowest-available-row — acceptable for ≤20 bookings/property/month"

# Metrics
duration: 5min
completed: 2026-02-28
---

# Phase 7 Plan 4: Calendar Tab Summary

**Interactive booking calendar with 7-column month grid (bars split at week boundaries, stacking overlaps) and Gantt timeline (properties as rows, days as columns) using shadcn Popover for click-to-view booking details**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-28T22:24:46Z
- **Completed:** 2026-02-28T22:29:57Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Month calendar grid with 7-column CSS Grid, booking bars spanning check-in to check-out (split at Sat→Sun boundaries), overlapping bar stacking, current-day highlight, and prev/next navigation
- BookingPopover (shadcn Popover, not Tooltip per RESEARCH.md) showing guest name, date range, night count, platform color dot, payout amount, and property name on click
- Gantt timeline view with properties as rows, days of month as columns, platform-colored blocks, weekend shading, sticky property labels, and horizontal scroll on mobile
- View toggle buttons (Month / Timeline) with shared booking data from useBookings hook
- Loading skeleton and error state with retry in CalendarTab

## Task Commits

Each task was committed atomically:

1. **Task 1: Month calendar grid with booking bars and popover** - `706c044` (feat)
2. **Task 2: Timeline/Gantt view** - `a8b1a40` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/src/hooks/useBookings.ts` — TanStack Query hook; queryKey includes selectedPropertyId so property-change auto-refetches; staleTime 5 min
- `frontend/src/components/calendar/BookingBar.tsx` — Horizontal bar with platform light color, truncated guest name, selective border-radius (flat on split sides), pointer cursor, absolute positioning via left/width % math
- `frontend/src/components/calendar/BookingPopover.tsx` — shadcn Popover with guest name, dates, night count, platform dot, payout, property; manages own open state
- `frontend/src/components/calendar/MonthCalendar.tsx` — 7-col CSS Grid, week row containers with absolute booking bars; splitIntoWeekSegments() for week-boundary splits; assignRowOffsets() for stacking; today highlighted
- `frontend/src/components/calendar/TimelineView.tsx` — CSS Grid 140px+N columns; height:0/overflow:visible booking bar overlay; computeSegments() with stack assignment; weekend shading; overflow-x:auto
- `frontend/src/components/calendar/CalendarTab.tsx` — currentMonth state, month/timeline view toggle, useBookings, loading skeleton, error alert, renders MonthCalendar or TimelineView
- `frontend/src/components/layout/AppShell.tsx` — Import and render CalendarTab in calendar tab content (replacing "coming soon" placeholder)

## Decisions Made
- **Booking occupancy semantics:** nights are [checkIn, checkOut-1]; last occupied night is the day before checkout. A 3-night booking Feb 15→18 occupies Feb 15, 16, 17 — not Feb 18.
- **ISO date parsing:** `new Date(y, m-1, d)` instead of `new Date(isoString)` — avoids UTC midnight being interpreted as prior local day in timezones behind UTC.
- **getPlatformColorEntry().light for calendar bars** — distinct from `.chart` used in Recharts. Light pastel variants are visually appropriate for large calendar blocks; chart colors are optimized for small Recharts dots/bars.
- **BookingBar absolute-positioned, not grid item** — bars are positioned within a full-width week row div using percentage left/width math. This is simpler than placing bars as grid items (which would require complex grid-row overlap handling).
- **TimelineView height:0/overflow:visible overlay** — booking bars are grid items spanning their day columns but with zero height and overflow:visible. This avoids pushing the underlying day cells apart while still achieving correct column alignment.
- **Stacking uses greedy lowest-available-row** — O(n²) for typical dataset (≤20 bookings per property per month). Performance is not a concern at this scale.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- AppShell had already been modified (from a prior plan not reflected in STATE.md) to import ActionsTab and ReportsTab. The CalendarTab import was added cleanly alongside those existing imports.

## Next Phase Readiness
- Calendar tab fully functional; month and timeline views both render correctly with booking data
- Plan 07-05 (Actions tab) can follow the same tab content pattern established here
- useBookings hook is available for any other component needing booking data by date range

---
*Phase: 07-dashboard*
*Completed: 2026-02-28*

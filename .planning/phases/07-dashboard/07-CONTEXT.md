# Phase 7: Dashboard - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Web dashboard showing financial metrics, occupancy, booking calendar, and pending actions from a clean interface that non-technical users (Kim) can navigate. React + Vite + shadcn/ui frontend served alongside the existing FastAPI backend. The LLM query interface is Phase 8 — not included here.

</domain>

<decisions>
## Implementation Decisions

### Dashboard layout
- Tabbed interface with 4 tabs: Home, Calendar, Reports, Actions
- Global property selector in the header: "All Properties" / individual properties — affects all tabs
- Light theme by default with a dark mode toggle — both themes maintained
- No sidebar; all navigation via tabs and header controls

### Financial display (Home tab)
- Big number stat cards at the top: YTD Revenue, YTD Expenses, Current-Month Profit
- Each card shows year-over-year comparison (vs same month last year), not month-over-month
- Below cards: bar chart for monthly booking trend (12 months) and donut chart for occupancy rate per property
- Standard financial terms (Revenue, Expenses, Profit) with hover tooltips explaining each in plain language
- "X items need attention" summary card on Home tab linking to Actions tab

### Calendar design (Calendar tab)
- Two views with toggle: month grid view (default) and timeline/Gantt view
- Month view shows bookings as colored bars spanning check-in to check-out
- Timeline view shows properties as rows with booking blocks
- Muted/pastel versions of platform brand colors (not raw brand colors) — must work in both light and dark mode
- Click on a booking shows a popover with: guest name, dates (+ night count), platform, amount, property
- All bookings visible (past + future) — navigate months freely
- Global property selector filters calendar to selected property or shows all

### Pending actions (Actions tab)
- Single flat list sorted by urgency (most urgent first)
- Color/icon indicates action type: resort form submission, VRBO message to send, unreconciled transaction
- Click item to expand details, then action button inside expanded view (not inline buttons)
- Action count badge on the Actions tab visible from all other tabs (e.g., "Actions 3")
- Empty state: simple "No pending actions" text — no illustrations or fanfare

### Claude's Discretion
- Exact shadcn/ui component choices and composition
- Responsive breakpoints and mobile adaptation
- Loading states and skeleton screens
- Error state handling for API failures
- Exact chart library selection within shadcn/ui ecosystem
- Tab transition animations (if any)
- Exact muted color palette for platform coding

</decisions>

<specifics>
## Specific Ideas

- Kim is the primary user — she checks financial and booking status without needing explanation of financial concepts
- Tooltips on financial terms bridge the gap: standard labels keep the UI professional, tooltips make it accessible
- Year-over-year comparison chosen because rental revenue is seasonal — month-over-month would mislead
- Calendar popover keeps it lightweight; no need to navigate away from the calendar view to see booking basics
- "Both views with toggle" on calendar because month view is familiar but timeline better shows gaps between stays

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-dashboard*
*Context gathered: 2026-02-28*

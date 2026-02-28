# Phase 7: Dashboard - Research

**Researched:** 2026-02-28
**Domain:** React + Vite + shadcn/ui frontend served by FastAPI; booking calendar; financial charts
**Confidence:** HIGH (core stack verified via official docs and Context7)

---

## Summary

Phase 7 builds a React + Vite + shadcn/ui single-page application served from the existing FastAPI
backend. The frontend is a static build (`dist/`) mounted on FastAPI using `StaticFiles` with a
custom SPA fallback, and during development a Vite dev server proxies API calls to FastAPI on :8000.

The locked technology choices (React, Vite, shadcn/ui) have strong official documentation and are
well-established in 2026. shadcn/ui now targets Tailwind CSS v4 with OKLCH color variables and ships
built-in chart components (`Chart`, `BarChart`, `PieChart`) built on Recharts v2 — these directly
satisfy the bar chart and donut chart requirements. The tab system, cards, badge, popover, skeleton,
accordion, and tooltip components all exist in shadcn/ui and are the correct primitives for every
UI requirement described in CONTEXT.md.

The calendar is the most complex component. There is no shadcn/ui calendar primitive that renders
multi-day booking bars. The correct approach is a **hand-crafted CSS-grid calendar** with custom
booking-bar rendering — a well-understood pattern using 7-column CSS Grid and absolutely-positioned
or flowing day-cell elements. The timeline/Gantt view is similarly custom. This is deliberate
(shadcn/ui component ownership pattern): copy and own the code rather than import a heavy calendar
library. The calendar logic is bounded and manageable.

State management uses Zustand v5 for the global property selector (one store, one slice). All
server data goes through TanStack Query v5 (`@tanstack/react-query`), which provides loading states,
background refetching, and error handling without manual `useEffect` patterns.

**Primary recommendation:** Scaffold the Vite project inside `frontend/` at repo root, build it in a
new Docker stage, copy `dist/` into the Python image, mount with `SPAStaticFiles`, and add
`CORSMiddleware` for local development. Do not use a separate nginx container — keep the single-container
deployment pattern.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.x | UI framework | Locked decision |
| Vite | 6.x | Build tool + dev server | Locked decision; pairs with React 19 |
| shadcn/ui | CLI 3.8.5 (latest) | Component library | Locked decision |
| Tailwind CSS | v4 | Styling | Required by shadcn/ui new installs |
| TypeScript | 5.x | Type safety | shadcn/ui init defaults to TS |
| @tanstack/react-query | 5.x | Server state / data fetching | Industry standard for async state |
| zustand | 5.x | Global UI state (property selector) | Lightweight (<1KB), current standard 2026 |
| react-router-dom | 7.x | Tab URL sync (optional, see note) | Clean deep-link support for tabs |
| recharts | 2.x (via shadcn chart) | Charts (do not install separately) | Bundled with shadcn chart component |

**Note on react-router:** URL-synced tabs are a nice-to-have (e.g., bookmark the Actions tab).
The shadcn `Tabs` component supports controlled `value` prop; you can sync with `useSearchParams`
from react-router without full nested routing. Use react-router-dom for the SPA shell; tabs sync
via search params (`?tab=actions`).

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | latest | Icons (Sun/Moon toggle, action type icons) | Already a shadcn/ui peer dep |
| @types/node | latest (dev) | Vite path alias TypeScript resolution | Required for `@/*` alias |
| tw-animate-css | latest (dev) | CSS animations (replaces tailwindcss-animate) | Installed by shadcn init automatically |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled calendar | FullCalendar / Mobiscroll | Those are commercial or large; shadcn philosophy is to own the code |
| Zustand | React Context | Context rerenders entire tree; Zustand selective subscriptions are cleaner |
| TanStack Query | SWR | TanStack Query v5 has more features (devtools, mutations, queryOptions API) |
| Vite proxy (dev) | CORS on FastAPI | Proxy is dev-only; CORS on FastAPI for local dev is correct for production |

### Installation

```bash
# From repo root — create the frontend project
npm create vite@latest frontend -- --template react-ts
cd frontend

# Tailwind v4 for Vite
npm install tailwindcss @tailwindcss/vite
# Update vite.config.ts to import @tailwindcss/vite plugin
# Replace src/index.css with: @import "tailwindcss";

# TypeScript path config (tsconfig.json + tsconfig.app.json)
npm install -D @types/node

# shadcn/ui init (answers: Tailwind v4, zinc base color, yes CSS variables)
npx shadcn@latest init

# Add all required shadcn/ui components
npx shadcn@latest add tabs card badge badge skeleton tooltip popover \
  select dropdown-menu accordion collapsible chart button separator

# State and data fetching
npm install @tanstack/react-query zustand react-router-dom
npm install -D @tanstack/react-query-devtools
```

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/
├── public/                   # Static assets
├── src/
│   ├── api/                  # API client functions (queryFn wrappers)
│   │   ├── client.ts         # Base fetch wrapper with error handling
│   │   ├── financial.ts      # /api/reports/* calls
│   │   ├── bookings.ts       # /api/accounting/* booking queries
│   │   ├── compliance.ts     # /compliance/* calls
│   │   └── communication.ts  # /communication/* calls
│   ├── components/
│   │   ├── ui/               # shadcn/ui generated components (do not edit)
│   │   ├── layout/
│   │   │   ├── Header.tsx    # Property selector + theme toggle + tab nav
│   │   │   └── AppShell.tsx  # Root layout wrapper
│   │   ├── home/
│   │   │   ├── StatCard.tsx           # YTD Revenue / Expenses / Profit card
│   │   │   ├── BookingTrendChart.tsx  # Bar chart (12-month)
│   │   │   └── OccupancyChart.tsx     # Donut chart per property
│   │   ├── calendar/
│   │   │   ├── MonthCalendar.tsx      # Month grid view
│   │   │   ├── TimelineView.tsx       # Gantt/timeline view
│   │   │   ├── BookingBar.tsx         # Colored booking bar element
│   │   │   └── BookingPopover.tsx     # Click popover with booking details
│   │   ├── actions/
│   │   │   ├── ActionsList.tsx        # Flat sorted list
│   │   │   └── ActionItem.tsx         # Expandable item with action button
│   │   └── shared/
│   │       ├── SkeletonCard.tsx       # Loading skeleton for cards
│   │       ├── ErrorAlert.tsx         # API error display
│   │       └── EmptyState.tsx         # "No pending actions" text
│   ├── hooks/
│   │   ├── useFinancials.ts   # useQuery wrappers for financial data
│   │   ├── useBookings.ts     # useQuery wrappers for bookings
│   │   └── useActions.ts      # useQuery for pending actions
│   ├── store/
│   │   └── usePropertyStore.ts  # Zustand store: selected property
│   ├── lib/
│   │   ├── utils.ts           # shadcn/ui cn() helper (generated)
│   │   └── platformColors.ts  # Muted platform color definitions
│   ├── App.tsx                # Router + QueryClient + ThemeProvider
│   ├── main.tsx
│   └── index.css              # @import "tailwindcss"; + :root theme vars
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tsconfig.app.json
└── package.json
```

### Pattern 1: TanStack Query for API Data

**What:** Centralize all server data fetching in custom hooks using `useQuery`. Each tab fetches its
own data. The property selector value from Zustand is included in query keys so data refetches
automatically when the property changes.

**When to use:** All API calls. Never use `useEffect` + `useState` for data fetching.

```typescript
// Source: https://tanstack.com/query/v5/docs/react/guides/queries
// src/hooks/useFinancials.ts
import { useQuery } from "@tanstack/react-query"
import { usePropertyStore } from "@/store/usePropertyStore"
import { fetchYTDMetrics } from "@/api/financial"

export function useYTDMetrics() {
  const selectedProperty = usePropertyStore((s) => s.selectedProperty)

  return useQuery({
    queryKey: ["ytd-metrics", selectedProperty],
    queryFn: () => fetchYTDMetrics(selectedProperty),
    staleTime: 5 * 60 * 1000,  // 5 minutes — financial data doesn't change often
  })
}
```

```typescript
// src/api/financial.ts
export async function fetchYTDMetrics(propertySlug: string | null) {
  const params = new URLSearchParams({ ytd: "true", breakdown: "property" })
  if (propertySlug) params.append("property_slug", propertySlug)
  const res = await fetch(`/api/reports/pl?${params}`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}
```

### Pattern 2: Zustand Property Store

**What:** Single Zustand store holds `selectedProperty: string | null` (null = "All Properties").
All query keys include this value so TanStack Query reactively refetches on change.

```typescript
// Source: https://zustand.docs.pmnd.rs/
// src/store/usePropertyStore.ts
import { create } from "zustand"

interface PropertyStore {
  selectedProperty: string | null   // null = "All Properties"
  setSelectedProperty: (slug: string | null) => void
}

export const usePropertyStore = create<PropertyStore>()((set) => ({
  selectedProperty: null,
  setSelectedProperty: (slug) => set({ selectedProperty: slug }),
}))
```

### Pattern 3: shadcn/ui Chart Components

**What:** shadcn/ui `Chart` component is a thin wrapper around Recharts. You use `ChartContainer`
with `BarChart` (for monthly trend) and `PieChart` with `innerRadius` (for donut/occupancy). Colors
reference CSS variables via `ChartConfig`.

```typescript
// Source: https://ui.shadcn.com/docs/components/chart
// Monthly booking trend bar chart
import { Bar, BarChart, CartesianGrid, XAxis } from "recharts"
import {
  ChartContainer, ChartTooltip, ChartTooltipContent, ChartLegend, ChartLegendContent
} from "@/components/ui/chart"
import type { ChartConfig } from "@/components/ui/chart"

const chartConfig = {
  bookings: { label: "Bookings", color: "var(--chart-1)" },
} satisfies ChartConfig

export function BookingTrendChart({ data }: { data: MonthlyBooking[] }) {
  return (
    <ChartContainer config={chartConfig} className="min-h-[200px] w-full">
      <BarChart data={data}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="month" tickLine={false} axisLine={false} />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Bar dataKey="bookings" fill="var(--color-bookings)" radius={4} />
      </BarChart>
    </ChartContainer>
  )
}
```

```typescript
// Donut (occupancy) chart — uses PieChart with innerRadius
import { Pie, PieChart } from "recharts"

const occupancyConfig = {
  occupied: { label: "Occupied", color: "var(--chart-1)" },
  vacant: { label: "Vacant", color: "var(--chart-2)" },
} satisfies ChartConfig

export function OccupancyChart({ occupied, total }: { occupied: number; total: number }) {
  const data = [
    { name: "occupied", value: occupied, fill: "var(--color-occupied)" },
    { name: "vacant", value: total - occupied, fill: "var(--color-vacant)" },
  ]
  return (
    <ChartContainer config={occupancyConfig} className="min-h-[150px]">
      <PieChart>
        <Pie data={data} dataKey="value" innerRadius={40} outerRadius={70} />
        <ChartTooltip content={<ChartTooltipContent />} />
      </PieChart>
    </ChartContainer>
  )
}
```

### Pattern 4: Dark Mode ThemeProvider

**What:** Official shadcn/ui Vite dark mode pattern using React Context and localStorage.
Wrap `App.tsx` root in `ThemeProvider`. ModeToggle goes in the header.

```typescript
// Source: https://ui.shadcn.com/docs/dark-mode/vite
// src/components/theme-provider.tsx
import { createContext, useContext, useEffect, useState } from "react"

type Theme = "dark" | "light" | "system"

export function ThemeProvider({
  children,
  defaultTheme = "light",   // CONTEXT.md: light theme by default
  storageKey = "dashboard-theme",
}: {
  children: React.ReactNode
  defaultTheme?: Theme
  storageKey?: string
}) {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem(storageKey) as Theme) || defaultTheme
  )

  useEffect(() => {
    const root = window.document.documentElement
    root.classList.remove("light", "dark")
    if (theme === "system") {
      const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark" : "light"
      root.classList.add(systemTheme)
      return
    }
    root.classList.add(theme)
  }, [theme])

  // ...context provider
}
```

### Pattern 5: Tab Navigation with URL Search Params

**What:** Shadcn `Tabs` with `value` controlled by `useSearchParams`. This allows direct linking
to a specific tab (e.g., `/dashboard?tab=actions`) without full page routing.

```typescript
// src/App.tsx
import { useSearchParams } from "react-router-dom"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"

const TAB_PARAM = "tab"
const DEFAULT_TAB = "home"

export function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get(TAB_PARAM) || DEFAULT_TAB
  const { data: actions } = useActions()
  const actionCount = actions?.filter(a => !a.dismissed).length ?? 0

  return (
    <Tabs value={activeTab} onValueChange={(v) => setSearchParams({ [TAB_PARAM]: v })}>
      <TabsList>
        <TabsTrigger value="home">Home</TabsTrigger>
        <TabsTrigger value="calendar">Calendar</TabsTrigger>
        <TabsTrigger value="reports">Reports</TabsTrigger>
        <TabsTrigger value="actions" className="gap-1.5">
          Actions
          {actionCount > 0 && <Badge variant="destructive">{actionCount}</Badge>}
        </TabsTrigger>
      </TabsList>
      <TabsContent value="home"><HomeTab /></TabsContent>
      <TabsContent value="calendar"><CalendarTab /></TabsContent>
      <TabsContent value="reports"><ReportsTab /></TabsContent>
      <TabsContent value="actions"><ActionsTab /></TabsContent>
    </Tabs>
  )
}
```

### Pattern 6: Expandable Action Items

**What:** The Actions tab uses shadcn `Collapsible` for each item (not `Accordion`, since
`Accordion` manages many items as a group). Each `ActionItem` is independently expandable.
The action button lives inside `CollapsibleContent`.

```typescript
// Source: https://ui.shadcn.com/docs/components/collapsible
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Button } from "@/components/ui/button"

export function ActionItem({ action }: { action: PendingAction }) {
  const [open, setOpen] = useState(false)

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex items-center gap-2 w-full text-left p-3">
        <ActionIcon type={action.type} />
        <span className="flex-1 text-sm font-medium">{action.summary}</span>
        <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
      </CollapsibleTrigger>
      <CollapsibleContent className="px-3 pb-3 space-y-2">
        <p className="text-sm text-muted-foreground">{action.detail}</p>
        <Button size="sm" onClick={() => handleAction(action)}>
          {action.actionLabel}
        </Button>
      </CollapsibleContent>
    </Collapsible>
  )
}
```

### Pattern 7: Month Grid Calendar

**What:** A hand-crafted 7-column CSS grid. Each week is a row. Bookings span multiple cells using
absolute positioning within each row. This is the shadcn/ui way — own the code, no calendar library.

**Key implementation insight:** Multi-day booking bars spanning week boundaries require splitting the
booking into segments, one per row. Calculate which cells (0–6) a booking occupies in each week row
and render a bar element with `grid-column: start / end+1` and `position: absolute` or CSS Grid
`column-span`.

```typescript
// Month grid skeleton
export function MonthCalendar({ year, month, bookings }: MonthCalendarProps) {
  const days = generateMonthDays(year, month)  // Array of {date, isCurrentMonth} objects
  const weeks = chunkIntoWeeks(days)           // Split into 7-day rows

  return (
    <div className="grid grid-cols-7 gap-px bg-border rounded-lg overflow-hidden">
      {/* Day headers: Sun Mon Tue Wed Thu Fri Sat */}
      {DAY_NAMES.map(d => (
        <div key={d} className="bg-muted text-center text-xs font-medium p-2">{d}</div>
      ))}
      {/* Day cells */}
      {days.map(({ date, isCurrentMonth }) => (
        <DayCell key={date.toISOString()} date={date} isCurrentMonth={isCurrentMonth} />
      ))}
      {/* Booking bars overlay: rendered per-week as absolutely positioned rows */}
    </div>
  )
}
```

### Pattern 8: FastAPI SPA Serving

**What:** Mount the React `dist/` directory on FastAPI using a custom `SPAStaticFiles` class that
falls back to `index.html` for any 404 (enabling React Router client-side routing). CORS middleware
added for local development (Vite dev server runs on a different port).

```python
# Source: https://davidmuraya.com/blog/serving-a-react-frontend-application-with-fastapi/
# app/main.py additions

from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            raise

# Add CORS for local dev (allow Vite dev server origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount AFTER all API routers (order matters — API routes take precedence)
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", SPAStaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")
```

### Pattern 9: Docker Multi-Stage Build

**What:** Add a Node.js build stage to the existing Dockerfile. The built `dist/` is copied into
the Python image. Docker Compose does not need a new service.

```dockerfile
# Stage 1: Build React frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python runtime (existing base)
FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-install-project

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY manage.py ./

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Pattern 10: Vite Dev Server Proxy

**What:** During local development, point Vite's dev server at FastAPI on :8000. This avoids CORS
entirely in dev. The `VITE_API_BASE` environment variable switches between proxy and direct.

```typescript
// vite.config.ts
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import path from "path"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/communication": "http://localhost:8000",
      "/compliance": "http://localhost:8000",
    },
  },
})
```

### Anti-Patterns to Avoid

- **Prop-drilling the property selector:** Use Zustand, not prop chains through 4 component levels.
- **Fetching on mount with useEffect:** Always use TanStack Query — it handles caching, deduplication, and stale state.
- **Mounting SPA before API routes:** `app.mount("/", ...)` must come AFTER all `app.include_router()` calls or the static files handler will swallow API requests.
- **Using raw recharts without shadcn ChartContainer:** `ChartContainer` handles responsive sizing and CSS variable injection. Without it, chart colors won't respect the theme.
- **Installing `tailwindcss-animate`:** The new default is `tw-animate-css`. Do not install the old package.
- **Hardcoding HSL colors for charts:** Use CSS variables (`var(--chart-1)`) so they work in both light and dark mode.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bar and donut charts | Custom SVG/canvas charts | shadcn/ui Chart + Recharts | shadcn chart wraps Recharts correctly with theme CSS variables |
| Loading placeholders | Custom shimmer divs | shadcn/ui Skeleton | Handles animation and sizing consistently |
| Dark mode toggle | Custom theme state | shadcn ThemeProvider + ModeToggle | Official pattern; persists to localStorage correctly |
| Tooltip on financial terms | Custom hover div | shadcn/ui Tooltip + TooltipProvider | Handles focus/keyboard accessibility out of box |
| Booking popover | Custom positioned div | shadcn/ui Popover | Handles viewport collision, ARIA, and focus trap |
| Select / dropdown | Custom `<select>` | shadcn/ui Select | Full keyboard nav, theming, accessibility |
| Server state (caching, loading) | useState + useEffect | TanStack Query useQuery | Deduplication, stale-while-revalidate, devtools |
| Global property state | React Context + prop drilling | Zustand store | Selective subscriptions prevent unnecessary renders |
| SPA fallback routing | nginx reverse proxy | SPAStaticFiles custom class | Keeps single container; no extra service |

**Key insight:** In this domain, every "simple" UI problem (tooltips, dropdowns, popovers) has
accessibility and focus-management complexity that shadcn/ui has already solved. The only thing
genuinely custom is the calendar grid, and that's deliberate.

---

## Platform Color Palette

Based on official brand research, the muted/pastel versions for light and dark mode use:

| Platform | Brand Hex | Muted Light | Muted Dark | CSS Variable |
|----------|-----------|-------------|------------|--------------|
| Airbnb | #FF385C | `#fca5a5` (red-300) | `#7f1d1d` (red-900) | `--platform-airbnb` |
| VRBO | #245ABC | `#93c5fd` (blue-300) | `#1e3a8a` (blue-900) | `--platform-vrbo` |
| RVShare | #004765 | `#7dd3fc` (sky-300) | `#0c4a6e` (sky-900) | `--platform-rvshare` |

Define in `src/lib/platformColors.ts`:

```typescript
// Both light and dark variants — pick based on current theme
export const PLATFORM_COLORS = {
  airbnb: {
    light: "#fca5a5",   // muted coral, readable on white
    dark: "#fca5a5",    // same — this pastel reads on dark bg too
    text: "#991b1b",    // contrast text for light bg
    textDark: "#fecaca",
  },
  vrbo: {
    light: "#93c5fd",
    dark: "#93c5fd",
    text: "#1e40af",
    textDark: "#bfdbfe",
  },
  rvshare: {
    light: "#7dd3fc",
    dark: "#7dd3fc",
    text: "#075985",
    textDark: "#bae6fd",
  },
} as const
```

**Note on dark mode calendar bars:** The same pastel hues (red-300, blue-300, sky-300) work on both
light and dark backgrounds because they are mid-saturation colors with sufficient contrast against
both white and dark-gray backgrounds.

---

## Common Pitfalls

### Pitfall 1: SPA Mount Order Swallows API Routes

**What goes wrong:** `app.mount("/", SPAStaticFiles(...))` is placed before `app.include_router()`
calls. The static files handler intercepts all requests including `/api/*` routes, returning 404s.

**Why it happens:** FastAPI processes routes and mounts in registration order. A mount on `/` is a
catch-all.

**How to avoid:** Always register all API routers first, then mount the SPA last. Add a guard:
```python
# LAST line in main.py, after all include_router() calls
if FRONTEND_DIST.exists():
    app.mount("/", SPAStaticFiles(...), name="spa")
```

**Warning signs:** FastAPI returns `{"detail": "Not Found"}` JSON for `/api/*` routes during local
dev when SPA is mounted.

---

### Pitfall 2: Tailwind v4 Dark Mode Class Strategy

**What goes wrong:** Dark mode classes (`dark:text-white`) don't apply even though the `.dark`
class is on `<html>`. Tailwind v4 changed the default dark mode variant.

**Why it happens:** Tailwind v4 uses the `media` strategy by default. shadcn's ThemeProvider adds
a `.dark` class to `<html>`, which requires the `selector` strategy.

**How to avoid:** The shadcn `init` command configures this correctly. Do not override dark mode
strategy manually. If colors don't apply in dark mode, check that `@import "tailwindcss"` does not
have any manual dark mode variant override.

**Warning signs:** Dark mode toggle appears to work (class on html element changes) but text/background
colors don't change.

---

### Pitfall 3: Chart Colors Not Applying in Dark Mode

**What goes wrong:** Chart bars render black or invisible in dark mode.

**Why it happens:** Recharts `fill` attributes don't pick up CSS variables unless threaded through
`ChartContainer`'s `config` prop. Directly using `fill="var(--chart-1)"` in a PieChart `<Pie>` on
a data item won't work — the fill must be on the data item's `fill` key.

**How to avoid:** Always use the `ChartConfig` pattern:
1. Define `chartConfig` with color as `"var(--chart-1)"` (or a hsl/oklch literal)
2. Pass `config={chartConfig}` to `ChartContainer`
3. In data items: `fill: "var(--color-key-name)"` (note: `var(--color-${key})` not `var(--chart-1)`)

**Warning signs:** Chart renders but is a flat dark color or invisible in dark mode.

---

### Pitfall 4: TanStack Query Property Key Invalidation

**What goes wrong:** Switching the property selector doesn't refetch data; old data persists.

**Why it happens:** The `queryKey` array doesn't include the `selectedProperty` value, so TanStack
Query treats it as the same query regardless of property.

**How to avoid:** Always include property identifier in queryKey:
```typescript
queryKey: ["ytd-metrics", selectedProperty]  // NOT just ["ytd-metrics"]
```

**Warning signs:** Switching property in header shows same numbers; browser devtools shows no new
network requests.

---

### Pitfall 5: Calendar Booking Bar Week Boundary Splitting

**What goes wrong:** A booking spanning from Thursday to Tuesday renders only on one week row or
causes layout overflow.

**Why it happens:** A CSS Grid calendar's rows are independent. A booking spanning two weeks must
be split into two segments: one ending at Saturday of week 1, one starting at Sunday of week 2.

**How to avoid:** In the calendar rendering logic, clip booking segments at week boundaries:
```typescript
function splitBookingByWeeks(booking: Booking, weeks: DateGrid[][]): BookingSegment[] {
  // Returns one segment per week the booking spans
  // Each segment has startCol (0–6) and endCol (0–6)
}
```

**Warning signs:** Long bookings appear truncated or extend beyond the calendar grid boundary.

---

### Pitfall 6: Backend API Endpoint Gaps for Dashboard

**What goes wrong:** The dashboard requires data that the existing API endpoints don't expose in
the right shape, requiring multiple waterfall requests.

**What exists:** `GET /api/reports/pl?ytd=true&breakdown=property` returns P&L by property.
`GET /api/accounting/journal-entries` returns individual entries. There is no single endpoint
for "all bookings with property name in date range" or "occupancy rate calculation."

**How to avoid:** Phase 07-02 and 07-03 plans should include **new dashboard-specific API endpoints**:
- `GET /api/dashboard/metrics?property_slug=X` — YTD revenue/expenses/profit + YoY comparison
- `GET /api/dashboard/bookings?start=X&end=Y&property_slug=Z` — bookings with property name,
  platform, dates, guest name, amount (for calendar)
- `GET /api/dashboard/occupancy?year=X&property_slug=Y` — 12-month occupancy rates

These aggregate queries are much more efficient as single API calls than composing frontend-side.

**Warning signs:** Dashboard tab makes 10+ API calls to render; slow initial load.

---

### Pitfall 7: Popover + Tooltip Nesting Issue

**What goes wrong:** A booking bar with both a `Tooltip` (quick hover) and a `Popover` (click for
detail) doesn't open the Popover because the Tooltip intercepts the click.

**Why it happens:** Known shadcn/ui issue (#2557) — Radix UI Popover and Tooltip conflict when
nested.

**How to avoid:** Use only Popover on calendar booking bars (click to open, shows all info).
Do not nest Tooltip + Popover. If hover-preview is needed, implement as a simple CSS `title`
attribute or use the Popover's hover trigger via `asChild` with `onMouseEnter` state.

---

### Pitfall 8: Property Selector Not Reflecting API Data

**What goes wrong:** The property selector hardcodes property slugs, but the backend exposes
properties dynamically from config YAML. The UI and backend get out of sync when a new property
is added.

**How to avoid:** Add `GET /api/properties` endpoint that returns `[{slug, display_name}]` from
the DB `properties` table. The Header component fetches this on mount and populates the selector.
Do not hardcode property names in the frontend.

---

## Code Examples

### Stat Card with Year-over-Year Comparison

```typescript
// Source: shadcn/ui Card + Badge components
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Badge } from "@/components/ui/badge"
import { InfoIcon, TrendingUp, TrendingDown } from "lucide-react"

interface StatCardProps {
  title: string
  value: string           // Formatted: "$42,150"
  tooltip: string         // Plain language explanation
  yoyChange: number       // Percent change vs same period last year
  yoyLabel: string        // "vs last year"
}

export function StatCard({ title, value, tooltip, yoyChange, yoyLabel }: StatCardProps) {
  const isPositive = yoyChange >= 0
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Tooltip>
          <TooltipTrigger>
            <InfoIcon className="size-4 text-muted-foreground" />
          </TooltipTrigger>
          <TooltipContent>
            <p className="max-w-xs text-sm">{tooltip}</p>
          </TooltipContent>
        </Tooltip>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold">{value}</p>
        <div className="flex items-center gap-1 mt-1">
          {isPositive ? (
            <TrendingUp className="size-3 text-green-600" />
          ) : (
            <TrendingDown className="size-3 text-red-600" />
          )}
          <span className={cn("text-xs", isPositive ? "text-green-600" : "text-red-600")}>
            {isPositive ? "+" : ""}{yoyChange.toFixed(1)}% {yoyLabel}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
```

### Skeleton Loading for Stat Cards

```typescript
// Source: https://ui.shadcn.com/docs/components/skeleton
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardHeader } from "@/components/ui/card"

export function StatCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-24" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-32 mb-2" />
        <Skeleton className="h-3 w-20" />
      </CardContent>
    </Card>
  )
}
```

### API Error Alert

```typescript
// Consistent error handling across all tabs
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"

export function ErrorAlert({ message }: { message: string }) {
  return (
    <Alert variant="destructive">
      <AlertCircle className="size-4" />
      <AlertDescription>{message || "Failed to load data. Try refreshing."}</AlertDescription>
    </Alert>
  )
}

// Usage in a tab:
const { data, isLoading, isError, error } = useYTDMetrics()
if (isLoading) return <StatCardSkeleton />
if (isError) return <ErrorAlert message={(error as Error).message} />
```

### New Backend Endpoint: Properties List

```python
# app/api/dashboard.py (new file)
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models.property import Property

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/properties")
def list_properties(db: Session = Depends(get_db)) -> list[dict]:
    """Return all properties for the dashboard property selector."""
    props = db.execute(select(Property).order_by(Property.slug)).scalars().all()
    return [{"slug": p.slug, "display_name": p.display_name} for p in props]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tailwind v3 with `tailwind.config.js` | Tailwind v4 with `@import "tailwindcss"` and `@theme` | 2025 | No JS config file; CSS-only configuration |
| HSL colors for shadcn variables | OKLCH colors | Jan 2026 | Better perceptual uniformity; update chart configs accordingly |
| `tailwindcss-animate` | `tw-animate-css` | 2025 | Install tw-animate-css; shadcn init handles this automatically |
| `react-router-dom` v6 | React Router v7 (import from `react-router`) | 2025 | Package name changed; v7 imports from `react-router` not `react-router-dom` |
| `React.forwardRef` in components | Regular function components with `React.ComponentProps` | Jan 2026 | shadcn components no longer use forwardRef |

**Deprecated/outdated:**
- `tailwindcss-animate`: Use `tw-animate-css` instead; shadcn init installs the correct one
- React Router `react-router-dom` as separate package: v7 merges into `react-router`
- `toast` component from shadcn: Deprecated in favor of `sonner` library; Phase 7 doesn't need toasts

---

## New API Endpoints Required

The existing backend has no endpoints optimized for the dashboard. Phase 07-01 should scaffold a
new `app/api/dashboard.py` router with:

| Endpoint | Purpose | Backend Source |
|----------|---------|----------------|
| `GET /api/dashboard/properties` | Property list for selector | `Property` model |
| `GET /api/dashboard/metrics` | YTD revenue/expenses/profit + YoY | `JournalLine` / `reports.generate_pl()` |
| `GET /api/dashboard/bookings` | Bookings with property + platform for calendar | `Booking` + `Property` join |
| `GET /api/dashboard/occupancy` | 12-month occupancy rates per property | `Booking` date arithmetic |
| `GET /api/dashboard/actions` | All pending actions (compliance + comms + recon) | Multi-table query |

The existing `GET /api/reports/pl?ytd=true` can power metrics but lacks YoY data (needs a second
call with `year=last_year`). A single dashboard endpoint is better — do the comparison server-side.

The actions endpoint must aggregate:
- `ResortSubmission` where `status='pending'` and `is_urgent=True`
- `CommunicationLog` where `status='pending'` and `platform` in (`vrbo`, `rvshare`)
- `BankTransaction` where `reconciliation_status='needs_review'`

Sorted by urgency server-side (resort forms by days until check-in, then comms by scheduled time,
then unreconciled transactions).

---

## Open Questions

1. **YoY comparison data shape**
   - What we know: `GET /api/reports/pl` supports `year=YYYY` for a full year
   - What's unclear: The dashboard needs current YTD value AND last year's same-period value. The
     backend would need either two calls or a new single endpoint that returns both periods.
   - Recommendation: Build `GET /api/dashboard/metrics` that returns both periods in one response.
     Pass `ytd=true` for current and `year=last_year&month=current_month&day=today` for comparison.

2. **Occupancy rate calculation**
   - What we know: Occupancy = occupied nights / total nights in period. Booking model has
     `check_in_date` and `check_out_date`.
   - What's unclear: How to handle partial months, same-day turnover, and "blocked" nights.
   - Recommendation: Define occupancy as `(check_out_date - check_in_date)` summed per property
     per month, divided by days in month. Compute server-side.

3. **Actions tab dismiss behavior**
   - What we know: CONTEXT.md says actions are "dismissable when actioned." The compliance
     API has `POST /compliance/submit/{booking_id}` and comms API has `POST /communication/confirm/{log_id}`.
   - What's unclear: Should the dashboard action trigger the backend action (e.g., submit the
     resort form) or just navigate/link to a confirmation? For VRBO messages marked as "pending,"
     the operator sends manually — the dashboard action button should mark it as sent.
   - Recommendation: The action button calls the appropriate existing API endpoint. On success,
     invalidate the actions query. No separate "dismiss" endpoint needed if actions are filtered
     by status server-side.

4. **Reports tab scope**
   - What we know: CONTEXT.md lists "Reports" as the fourth tab but the roadmap plan 07-06 focuses
     on "Navigation and layout." CONTEXT.md decisions don't specify what Reports tab shows.
   - What's unclear: Is Reports tab a view of P&L report data (like income statement)? Or a
     link/download for existing report formats?
   - Recommendation: Treat Reports tab as out-of-scope for initial implementation (render a
     placeholder). Raise with user before planning 07-06.

---

## Sources

### Primary (HIGH confidence)
- `https://ui.shadcn.com/docs/installation/vite` — Vite setup steps, Tailwind v4 usage
- `https://ui.shadcn.com/docs/components/chart` — ChartContainer, ChartConfig, Recharts usage
- `https://ui.shadcn.com/docs/dark-mode/vite` — ThemeProvider and ModeToggle implementation (code verified)
- `https://ui.shadcn.com/docs/tailwind-v4` — Tailwind v4 migration changes, OKLCH colors, tw-animate-css
- `https://ui.shadcn.com/docs/theming` — CSS variable structure for light/dark mode
- `https://ui.shadcn.com/docs/components/tabs` — Tabs, TabsList, TabsTrigger, TabsContent API
- `https://ui.shadcn.com/docs/components/accordion` — Accordion vs Collapsible distinction
- `https://ui.shadcn.com/docs/components/skeleton` — Skeleton component usage
- `https://ui.shadcn.com/docs/components/popover` — Popover API, alignment props
- `https://fastapi.tiangolo.com/tutorial/cors/` — CORSMiddleware exact parameters
- `https://davidmuraya.com/blog/serving-a-react-frontend-application-with-fastapi/` — SPAStaticFiles pattern
- `https://zustand.docs.pmnd.rs/` — Zustand v5 TypeScript store creation
- `https://tanstack.com/query/v5/docs/react/guides/queries` — useQuery API pattern

### Secondary (MEDIUM confidence)
- `https://www.brandcolorcode.com/vrbo` — VRBO brand hex codes (official-adjacent)
- `https://brandfetch.com/rvshare.com` — RVShare brand hex #004765 (Astronaut Blue)
- `https://usbrandcolors.com/airbnb-colors/` — Airbnb brand hex #FF385C
- `https://github.com/fastapi/fastapi/discussions/5134` — Docker multi-stage build for Vite+FastAPI
- `https://tanstack.com/query/latest` — TanStack Query v5 overview

### Tertiary (LOW confidence)
- WebSearch: shadcn/ui Popover + Tooltip nesting issue (#2557) — found in GitHub issues search
- WebSearch: React Router v7 tab routing patterns — verified structure is correct but not code-tested

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via official docs (shadcn, Vite, TanStack, Zustand)
- Architecture: HIGH — patterns are from official documentation and tested community practice
- Calendar implementation: MEDIUM — custom CSS grid calendar is the right approach but the exact
  multi-week booking-bar algorithm will need implementation iteration
- API endpoint gaps: HIGH — verified by reading the actual backend source code
- Platform colors: MEDIUM — primary brand colors verified; muted/pastel derivation is judgment call
- Pitfalls: HIGH — verified against official docs, GitHub issues, and source code review

**Research date:** 2026-02-28
**Valid until:** 2026-03-30 (30 days — shadcn/ui moves fast but core patterns are stable)

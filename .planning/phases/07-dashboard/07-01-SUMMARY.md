---
phase: 07-dashboard
plan: 01
subsystem: ui
tags: [react, vite, typescript, tailwindcss, shadcn, tanstack-query, zustand, react-router, docker, fastapi, spa]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: Dockerfile and docker-compose.yml base, FastAPI app/main.py entry point

provides:
  - React 19 + Vite 7 + TypeScript frontend project scaffold at frontend/
  - 14 shadcn/ui components (tabs, card, badge, skeleton, tooltip, popover, select, dropdown-menu, accordion, collapsible, chart, button, separator, alert)
  - Tailwind v4 via @tailwindcss/vite plugin with zinc-based CSS variable theme
  - TanStack Query + Zustand + React Router v7 installed
  - Typed API client (apiFetch<T>) with /api prefix and error handling
  - Vite dev server proxy /api -> localhost:8000
  - Docker multi-stage build (Node:22-alpine frontend stage + Python stage)
  - FastAPI SPAStaticFiles serving frontend/dist at root with index.html fallback
  - CORSMiddleware for Vite dev server (localhost:5173)

affects:
  - 07-02-dashboard-backend-api
  - 07-03-dashboard-ui
  - All subsequent dashboard plans

# Tech tracking
tech-stack:
  added:
    - react@19
    - vite@7
    - typescript@5.9
    - tailwindcss@4 (@tailwindcss/vite)
    - shadcn/ui (new-york style, zinc base)
    - "@tanstack/react-query@5"
    - zustand@5
    - react-router-dom@7
    - lucide-react
    - clsx + tailwind-merge
    - class-variance-authority
    - recharts (chart component peer dep)
    - radix-ui
  patterns:
    - Multi-stage Docker build: Node build stage -> Python app stage
    - SPAStaticFiles class for client-side routing fallback in FastAPI
    - Guarded SPA mount (os.path.isdir) so backend starts without frontend build
    - CORS via CORSMiddleware for local Vite dev only
    - API client with typed generics (apiFetch<T>) prepending /api

key-files:
  created:
    - frontend/package.json
    - frontend/vite.config.ts
    - frontend/tsconfig.app.json
    - frontend/tsconfig.json
    - frontend/index.html
    - frontend/src/main.tsx
    - frontend/src/App.tsx
    - frontend/src/index.css
    - frontend/src/api/client.ts
    - frontend/src/lib/utils.ts
    - frontend/components.json
    - frontend/src/components/ui/ (14 shadcn/ui component files)
  modified:
    - Dockerfile
    - app/main.py

key-decisions:
  - "Tailwind v4 @apply limitation: @apply border-border fails with Tailwind v4 CSS variable utilities; replaced with direct hsl(var(--border)) in @layer base"
  - "shadcn/ui components.json aliases resolve from project root; shadcn CLI wrote to frontend/@/ instead of frontend/src/; moved to src/components/ui/"
  - "SPAStaticFiles guarded with os.path.isdir('frontend/dist') — backend starts cleanly without frontend build during backend-only dev"
  - "CORSMiddleware allows localhost:5173 only (Vite dev server); production served from same origin via FastAPI SPA mount"
  - "SPA mount registered after all API routers (must be last to not shadow /api/ routes)"

patterns-established:
  - "Tailwind v4 CSS variables: define in :root via @layer base as HSL space-separated values (no hsl()), use hsl(var(--token)) in CSS rules"
  - "apiFetch<T>(path) — all frontend API calls use this; /api prefix prepended, errors parsed from detail field"

# Metrics
duration: 5min
completed: 2026-02-28
---

# Phase 7 Plan 01: Frontend Scaffold and SPA Integration Summary

**React 19 + Vite 7 + shadcn/ui scaffold with Tailwind v4, Docker multi-stage build, and FastAPI SPAStaticFiles serving at root**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-28T22:08:33Z
- **Completed:** 2026-02-28T22:13:33Z
- **Tasks:** 2/2
- **Files modified:** 30+

## Accomplishments

- Created complete React + Vite + TypeScript frontend project with all shadcn/ui components, TanStack Query, Zustand, and React Router
- Updated Dockerfile to Node:22-alpine multi-stage build that compiles frontend and embeds dist/ in the Python image
- FastAPI now serves the SPA at root with index.html fallback for client-side routing; CORS configured for local Vite dev

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Vite + React + shadcn/ui project** - `1a2f654` (feat)
2. **Task 2: Docker multi-stage build and FastAPI SPA serving** - `60e68b5` (feat)

## Files Created/Modified

- `frontend/package.json` - React 19 + Vite 7 + all deps (tailwindcss v4, TanStack Query, Zustand, React Router, shadcn peer deps)
- `frontend/vite.config.ts` - @tailwindcss/vite plugin, @ alias, /api proxy to :8000, dist outDir
- `frontend/tsconfig.app.json` - Added baseUrl + paths for @ alias, types: [node]
- `frontend/components.json` - shadcn/ui config (new-york style, zinc, CSS vars, Tailwind v4)
- `frontend/src/index.css` - Tailwind v4 import + full shadcn zinc CSS variable theme
- `frontend/src/App.tsx` - Minimal placeholder ("Dashboard loading...")
- `frontend/src/api/client.ts` - apiFetch<T> typed wrapper with /api prefix and error handling
- `frontend/src/lib/utils.ts` - cn() helper (clsx + tailwind-merge)
- `frontend/src/components/ui/` - 14 shadcn/ui components (tabs, card, badge, skeleton, tooltip, popover, select, dropdown-menu, accordion, collapsible, chart, button, separator, alert)
- `Dockerfile` - Added Node:22-alpine frontend-build stage; COPY --from into Python stage
- `app/main.py` - Added SPAStaticFiles class, CORSMiddleware, guarded SPA mount at "/"

## Decisions Made

- **Tailwind v4 @apply limitation:** The `@apply border-border` syntax fails with Tailwind v4 because CSS variable utility classes require theme registration via `@theme`. Used direct `hsl(var(--border))` in `@layer base` instead - correct and portable.
- **shadcn component path resolution:** shadcn CLI wrote components to `frontend/@/` (literal `@` directory) instead of `frontend/src/`. Moved to `frontend/src/components/ui/` which is the correct path alias target.
- **SPAStaticFiles guard:** `os.path.isdir("frontend/dist")` check ensures FastAPI starts without the frontend build being present — backend-only development workflow preserved.
- **SPA mount last:** `app.mount("/", ...)` must come after all `app.include_router()` calls to avoid shadowing API routes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tailwind v4 @apply border-border fails at build time**
- **Found during:** Task 1 (npm run build verification)
- **Issue:** `@apply border-border` in `@layer base` fails — Tailwind v4 doesn't support @apply with CSS-variable-based utility classes in the same way as v3
- **Fix:** Replaced `@apply border-border` and `@apply bg-background text-foreground` with direct `hsl(var(--border))` / `hsl(var(--background))` CSS values in `@layer base`
- **Files modified:** `frontend/src/index.css`
- **Verification:** `npm run build` succeeds, produces dist/index.html
- **Committed in:** `1a2f654` (part of Task 1 commit)

**2. [Rule 1 - Bug] shadcn CLI placed components in wrong directory**
- **Found during:** Task 1 (post-install file inspection)
- **Issue:** shadcn CLI resolved `@/components` to a literal `frontend/@/components/ui/` directory instead of `frontend/src/components/ui/`
- **Fix:** Copied all 14 component `.tsx` files from `frontend/@/components/ui/` to `frontend/src/components/ui/`, removed the erroneous `@/` directory
- **Files modified:** `frontend/src/components/ui/*.tsx` (all 14 components)
- **Verification:** `npm run build` succeeds with components in correct location; TypeScript paths resolve correctly
- **Committed in:** `1a2f654` (rename committed, files were already staged from initial scaffold)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes required for correct build. No scope creep.

## Issues Encountered

None beyond the two auto-fixed bugs above.

## User Setup Required

None - no external service configuration required. The frontend scaffold is self-contained and the Docker build is fully automated.

## Next Phase Readiness

- Frontend scaffold complete: React 19, Vite 7, TypeScript, Tailwind v4, shadcn/ui, TanStack Query, Zustand, React Router all installed and building
- `frontend/dist/index.html` produced by `npm run build` — Docker multi-stage confirmed working
- `python -c "from app.main import app; print('OK')"` passes — SPA serving integrated without errors
- `docker build -t rental-mgmt-test .` succeeds in ~30s
- Dashboard API router (07-02) already committed — ready for 07-03 (dashboard UI components)

---
*Phase: 07-dashboard*
*Completed: 2026-02-28*

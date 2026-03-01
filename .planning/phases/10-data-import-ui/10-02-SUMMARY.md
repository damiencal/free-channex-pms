---
phase: 10-data-import-ui
plan: 02
subsystem: ui
tags: [react, typescript, csv, xhr, drag-drop, file-upload, tanstack-query, lucide, radix-ui]

# Dependency graph
requires:
  - phase: 10-01
    provides: Progress/Label/Input UI primitives, Vite /ingestion proxy, useImportHistory hook
  - phase: 09-01
    provides: ingestion router at /ingestion prefix (FormData, not apiFetch)

provides:
  - CsvDropZone: drag-and-drop file zone with platform selector, XHR upload with real progress events, state machine
  - CsvUploadResult: success summary with record counts + scrollable ID list, multi-line error display
  - ImportResult interface: exported from CsvDropZone, shared with CsvUploadResult

affects:
  - 10-03: ImportTab or parent page will compose CsvDropZone + CsvUploadResult together

# Tech tracking
tech-stack:
  added: []
  patterns:
    - XHR for file upload with progress (not fetch) — enables upload.onprogress events for real progress bar
    - State machine pattern for multi-phase UI flow (idle -> file-selected -> uploading -> success/error)
    - Parent-controlled result display — drop zone delegates success/error to parent via onResult callback
    - Shared exported interface (ImportResult) across sibling components

key-files:
  created:
    - frontend/src/components/actions/CsvDropZone.tsx
    - frontend/src/components/actions/CsvUploadResult.tsx
  modified: []

key-decisions:
  - "CsvDropZone delegates success/error rendering to parent via onResult callback — keeps component boundaries clean; parent decides whether to show CsvUploadResult or inline"
  - "Upload URL is /ingestion/{platform}/upload (not /api/ingestion/) — consistent with [09-01] ingestion router prefix decision"
  - "ImportResult interface exported from CsvDropZone — CsvUploadResult imports it; single source of truth for the backend response shape"
  - "XHR used instead of fetch — fetch cannot expose upload progress events; XHR xhr.upload.onprogress enables real progress tracking"
  - "Cache invalidation targets ['dashboard'] and ['ingestion','history'] on success — ensures dashboard metrics and import history refresh automatically"

patterns-established:
  - "XHR upload pattern: uploadCsv() inline helper with onProgress callback, resolves ImportResult, rejects with Error message"
  - "State machine for file upload: idle | file-selected | uploading | success | error as discriminated union"
  - "Result persistence: no auto-dismiss; user must click 'Upload Another' or X to reset"

# Metrics
duration: 1min
completed: 2026-03-01
---

# Phase 10 Plan 02: CSV Upload Components Summary

**Drag-and-drop CSV upload with XHR progress tracking, platform selector, and detailed success/error result display via two composable React components**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-01T04:59:29Z
- **Completed:** 2026-03-01T05:00:45Z
- **Tasks:** 2
- **Files modified:** 2 (both created)

## Accomplishments
- CsvDropZone: full state machine covering idle, file-selected, uploading, and delegated success/error states; XHR upload to `/ingestion/{platform}/upload` with real progress events
- CsvUploadResult: success display with platform-aware record labels (Mercury shows "bank transactions"), scrollable inserted/updated ID lists with separate "New"/"Updated" sections, multi-line error display with scrollable list
- ImportResult interface exported from CsvDropZone and imported by CsvUploadResult — single source of truth for backend response shape

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CsvDropZone component with upload state machine** - `38388da` (feat)
2. **Task 2: Create CsvUploadResult component for success and error display** - `4604a48` (feat)

**Plan metadata:** _(final docs commit below)_

## Files Created/Modified
- `frontend/src/components/actions/CsvDropZone.tsx` - Drop zone with drag-and-drop, file picker, platform Select, XHR upload with progress, cache invalidation; exports ImportResult interface
- `frontend/src/components/actions/CsvUploadResult.tsx` - Success summary grid + scrollable ID list + dismiss button; error multi-line display + retry button; imports ImportResult from CsvDropZone

## Decisions Made
- CsvDropZone calls `onResult(result, null)` on success and `onResult(null, message)` on error — parent owns result display (composable, avoids tight coupling)
- Upload URL is `/ingestion/${platform}/upload` — not `/api/ingestion/` (honoring [09-01] decision that ingestion router stays at `/ingestion`)
- ImportResult exported from CsvDropZone, imported by CsvUploadResult — sibling import rather than a shared types file; appropriate for tightly coupled component pair
- XHR over fetch — `fetch` API has no upload progress event; `xhr.upload.onprogress` is the only way to get real-time upload progress

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Both components are ready to be composed by a parent (ImportTab / DataImportPage)
- Plan 10-03 will integrate CsvDropZone + CsvUploadResult into the full Import tab UI, connect to import history display from useImportHistory hook (10-01)
- No blockers

---
*Phase: 10-data-import-ui*
*Completed: 2026-03-01*

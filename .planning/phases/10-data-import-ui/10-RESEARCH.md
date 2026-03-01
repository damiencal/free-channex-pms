# Phase 10: Data Import UI - Research

**Researched:** 2026-02-28
**Domain:** React file upload UI, drag-and-drop, form handling, TanStack Query mutations, Radix UI components
**Confidence:** HIGH — all findings verified against actual codebase files and installed package type declarations

## Summary

Phase 10 is a pure frontend phase. All seven backend endpoints required already exist (`POST /ingestion/airbnb/upload`, `/ingestion/vrbo/upload`, `/ingestion/mercury/upload`, `/ingestion/rvshare/entry`, `GET /ingestion/history`, `GET /ingestion/bookings`, `GET /ingestion/bank-transactions`). The task is to wire these endpoints to a user interface inside the existing Actions tab.

The standard stack for this phase is already installed: React 19, TanStack Query v5, Radix UI (via the `radix-ui` monorepo package), shadcn/ui components, Tailwind v4, Zustand. **No new npm packages are needed.** Drag-and-drop file upload, progress simulation, the RVshare form, and the history accordion can all be built from native browser APIs and existing installed components. The only new UI primitives needed — `Progress`, `Label`, and a plain `<input type="file">` — are built from installed packages (`radix-ui` exports `Progress` and `Label` from `@radix-ui/react-progress` and `@radix-ui/react-label` which are already in `node_modules`).

The upload endpoints accept `multipart/form-data`. They cannot use `apiFetch` (which forces `Content-Type: application/json`). Uploads must use raw `fetch()` with a `FormData` body — the same pattern the ingestion router was designed for. The RVshare endpoint (`POST /ingestion/rvshare/entry`) accepts JSON and CAN use `apiFetch`.

**Primary recommendation:** Build the entire Data Import UI using only existing installed packages. Create three new shadcn/ui wrapper components (`progress.tsx`, `label.tsx`, `input.tsx`) following the identical pattern of existing wrappers. Use `XMLHttpRequest` for file upload to get real upload progress events.

## Standard Stack

### Core (Already Installed — Zero New Dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 19 | ^19.2.0 | Component rendering | Already in use |
| TanStack Query | ^5.90.21 | Server state + mutations | Already in use; `useMutation` handles upload state machine |
| `radix-ui` package | ^1.4.3 | UI primitives | Already in use; exports `Progress` and `Label` |
| Tailwind v4 | ^4.2.1 | Styling | Already in use |
| `lucide-react` | ^0.575.0 | Icons (Upload, X, Check, ChevronDown) | Already in use |
| Zustand | ^5.0.11 | Property selector state | Already in use via `usePropertyStore` |

### New UI Components to Create (No New npm Packages)

| Component | Source | Pattern |
|-----------|--------|---------|
| `src/components/ui/progress.tsx` | `import { Progress as ProgressPrimitive } from "radix-ui"` | Identical to existing accordion.tsx, select.tsx pattern |
| `src/components/ui/label.tsx` | `import { Label as LabelPrimitive } from "radix-ui"` | Identical pattern |
| `src/components/ui/input.tsx` | Native `<input>` element | No Radix needed; shadcn/ui style wrapper |

### No New Installations Needed

Verified: `@radix-ui/react-progress` and `@radix-ui/react-label` are both present in `frontend/node_modules/@radix-ui/`. The `radix-ui` monorepo package already re-exports them. No `npm install` required.

**Installation:** None.

## Architecture Patterns

### Recommended Project Structure

```
src/components/actions/
├── ActionsTab.tsx              # EXISTING — modify to add DataImport section
├── ActionItem.tsx              # EXISTING — no change
├── ActionsList.tsx             # EXISTING — no change
├── DataImportSection.tsx       # NEW — top-level section: drop zone + RVshare form + history
├── CsvDropZone.tsx             # NEW — file drop zone with platform selector
├── CsvUploadResult.tsx         # NEW — success summary + imported records list
├── RVshareEntryForm.tsx        # NEW — collapsible manual booking form
└── ImportHistoryAccordion.tsx  # NEW — collapsible history list

src/components/ui/
├── progress.tsx                # NEW — Radix Progress wrapper
├── label.tsx                   # NEW — Radix Label wrapper
└── input.tsx                   # NEW — native input wrapper (shadcn style)

src/hooks/
└── useImportHistory.ts         # NEW — GET /ingestion/history query hook
```

### Pattern 1: File Upload with XMLHttpRequest (Progress Events)

**What:** Native `fetch()` does not expose upload progress. `XMLHttpRequest` fires `xhr.upload.onprogress` events with `loaded` and `total` bytes. Use XHR wrapped in a Promise for upload + progress tracking.

**When to use:** Any `FormData` file upload that needs a progress bar.

**Why XHR over fetch:** The Fetch API does not support upload progress in current browser implementations. XHR's `xhr.upload.onprogress` is the standard approach.

**Example:**
```typescript
// Source: MDN Web Docs — XMLHttpRequest.upload
function uploadWithProgress(
  url: string,
  formData: FormData,
  onProgress: (pct: number) => void,
): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', url)
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as unknown)
      } else {
        // Extract FastAPI detail error message
        try {
          const body = JSON.parse(xhr.responseText) as { detail?: string }
          reject(new Error(body.detail ?? `HTTP ${xhr.status}`))
        } catch {
          reject(new Error(`HTTP ${xhr.status}`))
        }
      }
    }
    xhr.onerror = () => reject(new Error('Network error'))
    xhr.send(formData)
  })
}
```

**Important:** The upload endpoint prefix is `/ingestion` (not `/api/ingestion`). The ingestion router uses `prefix="/ingestion"` without `/api/`. This is a confirmed prior decision ([09-01]). The upload URL is `/ingestion/airbnb/upload` etc., NOT `/api/ingestion/...`.

**Vite proxy:** Vite proxies `/api` and `/health` to `localhost:8000` but NOT `/ingestion`. In development, the upload URL must hit the backend directly. Check current Vite config — currently only `/api` and `/health` are proxied. The ingestion prefix will need to be added to the proxy config OR the frontend must call via a different mechanism.

**CRITICAL OPEN QUESTION:** Vite's `vite.config.ts` only proxies `/api` and `/health`. Upload calls to `/ingestion/...` will fail in dev because they won't be proxied to the FastAPI backend. Either:
  1. Add `/ingestion` to the Vite proxy config (preferred — minimal change), OR
  2. Hardcode `http://localhost:8000` in dev (fragile)

  Option 1 is correct. Add to `vite.config.ts`:
  ```typescript
  '/ingestion': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
  ```

### Pattern 2: TanStack Query `useMutation` for RVshare JSON Entry

**What:** The RVshare manual entry endpoint (`POST /ingestion/rvshare/entry`) accepts JSON. Use `useMutation` + `apiFetch` — same pattern as ActionItem's `submitFormMutation`.

**When to use:** Any JSON POST that needs loading/error/success state.

**Example:**
```typescript
// Source: TanStack Query v5 docs — useMutation
const rvShareMutation = useMutation({
  mutationFn: (data: RVshareFormData) =>
    apiFetch<ImportResult>('/ingestion/rvshare/entry', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  onSuccess: () => {
    // invalidate dashboard bookings so new booking appears
    void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  },
})
```

**Note:** The RVshare endpoint IS at `/ingestion/rvshare/entry` without `/api/`. `apiFetch` prepends `/api`, so you CANNOT use `apiFetch` for RVshare entry. Use raw `fetch('/ingestion/rvshare/entry', ...)` instead. This is consistent with the prior decision that upload endpoints use FormData fetch, not apiFetch.

**Correction to above:** Re-checking: `apiFetch` prepends `/api` making the URL `/api/ingestion/rvshare/entry`, but the router is at `/ingestion/rvshare/entry`. The RVshare entry must use raw `fetch` with `Content-Type: application/json`, not `apiFetch`.

### Pattern 3: Drag-and-Drop File Zone (Native HTML5)

**What:** Use native `onDragOver`, `onDragLeave`, `onDrop` events on a `<div>` plus a hidden `<input type="file">`. No library needed.

**When to use:** Single-file drag-and-drop with a visible drop target.

**Example:**
```typescript
// Source: MDN Web Docs — HTML Drag and Drop API
function CsvDropZone({ onFile }: { onFile: (file: File) => void }) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) onFile(file)
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={cn(
        'border-2 border-dashed rounded-lg p-4 cursor-pointer text-center transition-colors',
        isDragging ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
      )}
    >
      <Upload className="mx-auto h-6 w-6 text-muted-foreground mb-2" />
      <p className="text-sm text-muted-foreground">Drop CSV here or click to browse</p>
      <input ref={inputRef} type="file" accept=".csv" className="hidden" onChange={...} />
    </div>
  )
}
```

### Pattern 4: Progress Bar Component (Radix Progress)

**What:** Wrap `Progress` from `radix-ui` the same way other wrappers are built.

**Example:**
```typescript
// Source: @radix-ui/react-progress — type declaration in node_modules
import { Progress as ProgressPrimitive } from "radix-ui"
import { cn } from "@/lib/utils"

function Progress({ className, value, ...props }: React.ComponentProps<typeof ProgressPrimitive.Root>) {
  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      className={cn("bg-secondary relative h-2 w-full overflow-hidden rounded-full", className)}
      value={value}
      {...props}
    >
      <ProgressPrimitive.Indicator
        data-slot="progress-indicator"
        className="bg-primary h-full w-full flex-1 transition-all"
        style={{ transform: `translateX(-${100 - (value ?? 0)}%)` }}
      />
    </ProgressPrimitive.Root>
  )
}
```

### Pattern 5: Upload State Machine

The upload flow has discrete states. Track with `useState`:

```typescript
type UploadState =
  | { phase: 'idle' }
  | { phase: 'file-selected'; file: File; platform: string | null }
  | { phase: 'uploading'; progress: number }
  | { phase: 'success'; result: ImportResult }
  | { phase: 'error'; message: string }
```

State transitions:
- `idle` → `file-selected` (on file drop or pick)
- `file-selected` → `idle` (file cleared) or `uploading` (submit clicked)
- `uploading` → `success` or `error`
- `success` → `idle` (user clicks "Upload another" or X)
- `error` → `idle` (user clicks "Try again")

### Pattern 6: RVshare Form — Validate on Blur

**What:** Per-field validation triggered on `onBlur`. Use `useState` per field for error messages. No form library needed given the small number of fields (6 fields: confirmation_code, guest_name, check_in_date, check_out_date, net_amount, property_slug).

**Fields required by `RVshareEntryRequest` Pydantic schema:**
- `confirmation_code: str` — text input
- `guest_name: str` — text input
- `check_in_date: date` — date input (`<input type="date">`)
- `check_out_date: date` — date input
- `net_amount: Decimal` — number input
- `property_slug: str` — Select dropdown (property list from `/api/dashboard/properties`)
- `notes: str | null` — optional textarea

**Property slug source:** Reuse the `['dashboard', 'properties']` query already cached by `AppShell`. Property list is available in `useQuery({ queryKey: ['dashboard', 'properties'] })` — no extra fetch.

**Date picker choice (Claude's Discretion):** Use `<input type="date">` — native browser date picker, zero dependencies, consistent with the project's no-toast-library approach. Downside: styling is browser-controlled (inconsistent cross-browser). For this internal tool with DASH-07 requirements (non-technical user usability), native date input is acceptable and simplest.

### Pattern 7: Import History Query Hook

```typescript
// src/hooks/useImportHistory.ts
export interface ImportRun {
  id: number
  platform: string
  filename: string
  inserted_count: number
  updated_count: number
  skipped_count: number
  imported_at: string  // ISO datetime string
}

export function useImportHistory(limit = 10) {
  return useQuery<ImportRun[]>({
    queryKey: ['ingestion', 'history', limit],
    queryFn: () => {
      // NOTE: /ingestion/history is NOT under /api/. Cannot use apiFetch.
      return fetch(`/ingestion/history?limit=${limit}`)
        .then(res => res.json()) as Promise<ImportRun[]>
    },
    staleTime: 60 * 1000,
  })
}
```

**Same issue:** `/ingestion/history` is not under `/api/` so it can't use `apiFetch`. Use raw `fetch`.

### Pattern 8: Collapsible History Section

Use the existing `Collapsible` + `CollapsibleTrigger` + `CollapsibleContent` components (already in `src/components/ui/collapsible.tsx`). Start collapsed (`open={false}`).

### Pattern 9: "Show More" for History

The context decision is a "Show more" link — not pagination. Implement by toggling between `limit=10` and `limit=50` on the query.

```typescript
const [showAll, setShowAll] = useState(false)
const { data: history } = useImportHistory(showAll ? 50 : 10)
```

### Pattern 10: After-Upload Cache Invalidation

After a successful CSV import, new bookings must appear on the dashboard without manual steps (success criterion 4). Invalidate the relevant TanStack Query cache keys:

```typescript
onSuccess: () => {
  void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  void queryClient.invalidateQueries({ queryKey: ['ingestion', 'history'] })
}
```

The `['dashboard']` prefix invalidates all dashboard queries (bookings, metrics, actions) in one call.

### Anti-Patterns to Avoid

- **Do not use `apiFetch` for any `/ingestion/` endpoint.** `apiFetch` prepends `/api`, but the ingestion router lives at `/ingestion/` without `/api/`. This is an established prior decision ([09-01]).
- **Do not install react-dropzone or react-hook-form.** Native HTML5 drag-and-drop and a small useState form are sufficient for 6 fields and a single drop zone.
- **Do not install a date picker library** (e.g., react-day-picker). Native `<input type="date">` is sufficient.
- **Do not use `fetch` for upload progress.** Fetch API does not expose upload progress; XHR is required.
- **Do not auto-dismiss results.** The context decision explicitly requires results to persist until user dismisses.
- **Do not add a separate platform to the RVshare form.** Platform is always "rvshare" — hardcoded server-side.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress bar | Custom div with width animation | Radix `Progress` (already installed) | Accessibility attributes (`aria-valuenow`, `role="progressbar"`) handled |
| Accordion/collapsible | Custom open/close state + div | Existing `Collapsible` component | Already installed and styled |
| Platform select dropdown | Custom dropdown | Existing `Select` component | Already installed, accessible, styled |
| Property select in RVshare form | Custom dropdown | Existing `Select` + `['dashboard', 'properties']` query | Cache already warm from AppShell |
| Drag-and-drop file library | react-dropzone | Native HTML5 events | No new dependency; single file, simple case |
| Form state management | react-hook-form, formik | `useState` per field | 6 fields, no complex cross-validation |

**Key insight:** This is an internal tool with ~6 form fields. The cost of adding a form library exceeds its value. Every needed primitive is in the existing shadcn/ui component set or in `radix-ui`'s already-installed exports.

## Common Pitfalls

### Pitfall 1: Using apiFetch for Ingestion Endpoints
**What goes wrong:** File upload returns 404. RVshare entry returns 404. History returns 404.
**Why it happens:** `apiFetch` prepends `/api`. The ingestion router prefix is `/ingestion`, not `/api/ingestion`.
**How to avoid:** Use raw `fetch('/ingestion/...')` for all ingestion endpoints. The prior decision [09-01] explicitly documents this.
**Warning signs:** 404 errors in browser dev tools on any `/api/ingestion/` URL.

### Pitfall 2: Vite Dev Proxy Not Configured for /ingestion
**What goes wrong:** In development, `fetch('/ingestion/airbnb/upload')` hits Vite's dev server, which returns 404 (no handler).
**Why it happens:** `vite.config.ts` only proxies `/api` and `/health`. `/ingestion` is unproxied.
**How to avoid:** Add `/ingestion` to the Vite proxy config before building any upload UI:
```typescript
'/ingestion': {
  target: 'http://localhost:8000',
  changeOrigin: true,
},
```
**Warning signs:** Network tab shows 404 on `/ingestion/...` in dev.

### Pitfall 3: Tailwind v4 @apply Limitation
**What goes wrong:** Custom CSS using `@apply border-border` fails to compile.
**Why it happens:** Prior decision [07-01] documents that Tailwind v4 `@apply` with CSS variable tokens fails. Must use `hsl(var(--token))` directly.
**How to avoid:** Don't use `@apply` with design token classes. Use inline Tailwind utilities or `hsl(var(--border))` directly in `@layer base` rules.
**Warning signs:** Build fails with CSS compilation error referencing `@apply border-border`.

### Pitfall 4: Platform Dropdown Without File Yet Selected
**What goes wrong:** User selects platform before choosing a file, or submits without a platform selected.
**Why it happens:** The drop zone design shows file first, then platform. The form may be submittable in an incomplete state.
**How to avoid:** Disable the submit button until both `file !== null` AND `platform !== null`. Show the platform selector only after a file is selected (conditional render).

### Pitfall 5: RVshare Form Submits check_out_date Before check_in_date
**What goes wrong:** Backend returns 422 from Pydantic validation or booking makes no logical sense.
**Why it happens:** Date inputs have no cross-field validation by default.
**How to avoid:** On blur of `check_out_date`, validate that `check_out_date > check_in_date`. Display an inline error if not.

### Pitfall 6: Upload Progress Jumps to 100% Instantly for Small Files
**What goes wrong:** Progress bar flashes 0→100 immediately, feels broken.
**Why it happens:** XHR upload progress fires for network upload only. For small CSVs on localhost, the upload completes in <1ms. Server processing time is not reflected in the progress bar.
**How to avoid:** After XHR upload completes (100%), show a brief "Processing..." state with an indeterminate indicator or hold at 95% until response comes back. Keep the progress bar visible until the fetch response resolves.

### Pitfall 7: "all-or-nothing" Import Error Display
**What goes wrong:** The backend returns a 422 with a multi-line error string (all row errors collected). Displaying `error.message` raw may show a wall of text.
**Why it happens:** The normalizer joins all errors with `"\n".join(errors)` into a single string. For files with many bad rows, this is a long string.
**How to avoid:** Split the error message on `\n` and render as a scrollable `<ul>` with a max-height, not a single `<p>`.

### Pitfall 8: Success Result "inserted_ids" vs Display Records
**What goes wrong:** Planner assumes success result has individual record details (guest name, dates). It doesn't.
**Why it happens:** The upload endpoints return aggregated counts plus `inserted_ids` (platform booking IDs as strings). Guest names, dates, and property slugs are NOT in the upload response.
**How to avoid:** The success result display can show: record count, platform, new vs skipped count, filename. For "scrollable list of individual imported records" (context decision), use the `inserted_ids` list (confirmation codes), not a rich booking display. Or: after successful upload, fire a separate `GET /ingestion/bookings?limit=N` request to fetch the just-imported records by confirmation code.

**Upload response shape (verified from normalizer.py):**
```typescript
interface ImportResult {
  platform: string      // "airbnb" | "vrbo" | "mercury"
  filename: string      // original filename
  inserted: number      // count of new records
  updated: number       // count of updated records
  skipped: number       // always 0 (current implementation)
  inserted_ids: string[] // platform booking IDs (confirmation codes)
  updated_ids: string[]  // platform booking IDs
  // inserted_db_ids and welcome_async_ids NOT returned (internal only)
}
```

**Mercury upload response** is the same shape but `inserted_ids` contains bank `transaction_id` strings. The success display for Mercury should say "bank transactions" not "bookings".

## Code Examples

Verified patterns from official sources and actual project code:

### Creating a shadcn/ui Progress Component

```typescript
// src/components/ui/progress.tsx
// Source: @radix-ui/react-progress type declarations (node_modules)
// Pattern: identical to src/components/ui/accordion.tsx wrapper style
"use client"

import * as React from "react"
import { Progress as ProgressPrimitive } from "radix-ui"
import { cn } from "@/lib/utils"

function Progress({
  className,
  value,
  ...props
}: React.ComponentProps<typeof ProgressPrimitive.Root>) {
  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      className={cn(
        "bg-secondary relative h-2 w-full overflow-hidden rounded-full",
        className
      )}
      value={value}
      {...props}
    >
      <ProgressPrimitive.Indicator
        data-slot="progress-indicator"
        className="bg-primary h-full w-full flex-1 transition-all duration-300"
        style={{ transform: `translateX(-${100 - (value ?? 0)}%)` }}
      />
    </ProgressPrimitive.Root>
  )
}

export { Progress }
```

### Creating a shadcn/ui Label Component

```typescript
// src/components/ui/label.tsx
// Source: @radix-ui/react-label type declarations (node_modules)
"use client"

import * as React from "react"
import { Label as LabelPrimitive } from "radix-ui"
import { cn } from "@/lib/utils"

function Label({
  className,
  ...props
}: React.ComponentProps<typeof LabelPrimitive.Root>) {
  return (
    <LabelPrimitive.Root
      data-slot="label"
      className={cn(
        "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
        className
      )}
      {...props}
    />
  )
}

export { Label }
```

### Creating a shadcn/ui Input Component

```typescript
// src/components/ui/input.tsx
// Source: shadcn/ui pattern — native input element, no Radix needed
import * as React from "react"
import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "border-input bg-background placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 flex h-9 w-full rounded-md border px-3 py-1 text-sm shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export { Input }
```

### Upload with XHR Progress

```typescript
// src/components/actions/DataImportSection.tsx (illustrative)
// Source: MDN — XMLHttpRequest.upload.onprogress
function uploadCsv(
  platform: 'airbnb' | 'vrbo' | 'mercury',
  file: File,
  onProgress: (pct: number) => void,
): Promise<ImportResult> {
  return new Promise((resolve, reject) => {
    const formData = new FormData()
    formData.append('file', file)

    const xhr = new XMLHttpRequest()
    // NOTE: /ingestion/ not /api/ingestion/ — confirmed by prior decision [09-01]
    xhr.open('POST', `/ingestion/${platform}/upload`)

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as ImportResult)
      } else {
        try {
          const body = JSON.parse(xhr.responseText) as { detail?: string }
          reject(new Error(
            typeof body.detail === 'string'
              ? body.detail
              : JSON.stringify(body.detail)
          ))
        } catch {
          reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`))
        }
      }
    }

    xhr.onerror = () => reject(new Error('Network error during upload'))
    xhr.send(formData)
  })
}
```

### RVshare Entry Form Submission (raw fetch, not apiFetch)

```typescript
// Source: actual project pattern — apiFetch cannot be used for /ingestion/ endpoints
async function submitRVshare(data: RVshareFormData): Promise<ImportResult> {
  const response = await fetch('/ingestion/rvshare/entry', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const body = (await response.json()) as { detail?: string }
    throw new Error(body.detail ?? `HTTP ${response.status}`)
  }
  return response.json() as Promise<ImportResult>
}
```

### Cache Invalidation After Successful Import

```typescript
// Source: TanStack Query v5 docs — queryClient.invalidateQueries
// Consistent with ActionItem.tsx pattern in this project
const queryClient = useQueryClient()

// After any successful import (CSV or RVshare):
void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
void queryClient.invalidateQueries({ queryKey: ['ingestion', 'history'] })
```

### Collapsible RVshare Form (using existing Collapsible component)

```typescript
// Source: src/components/ui/collapsible.tsx — existing component
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

function RVshareEntryForm() {
  const [open, setOpen] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        {submitted ? (
          <p className="text-sm text-green-600 dark:text-green-400">Booking added</p>
        ) : (
          <Button variant="outline" size="sm">
            {open ? 'Cancel' : 'Add RVshare Booking'}
          </Button>
        )}
      </CollapsibleTrigger>
      <CollapsibleContent>
        {/* form fields */}
      </CollapsibleContent>
    </Collapsible>
  )
}
```

### ActionsTab Modification

```typescript
// src/components/actions/ActionsTab.tsx — extend existing structure
// Add DataImportSection above or below the existing ActionsList
export function ActionsTab() {
  // ... existing code ...
  return (
    <div className="space-y-6">
      <DataImportSection />   {/* NEW — CSV upload + RVshare form + history */}
      <ActionsList items={items} />   {/* EXISTING — unchanged */}
    </div>
  )
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom drag-and-drop state | HTML5 native events | N/A (always available) | No library needed |
| fetch() for upload progress | XMLHttpRequest | N/A (fetch still no upload progress in 2026) | XHR required for progress |
| Separate form library (formik) | useState per field | N/A for small forms | Simpler, fewer deps |
| `@radix-ui/*` individual package imports | `radix-ui` monorepo import | radix-ui v1.x | `import { Progress } from "radix-ui"` works |
| Tailwind v3 config JS file | Tailwind v4 CSS-based config | Tailwind v4 | No `tailwind.config.js`; use `@layer base` / `src/index.css` |

**Deprecated/outdated:**
- `@apply border-border` in CSS: Tailwind v4 breaks this. Use `border-color: hsl(var(--border))` in `@layer base` rules directly.
- Importing from `@radix-ui/react-progress` directly: works, but the project convention is `import { Progress } from "radix-ui"` for consistency with all other UI primitives.

## Open Questions

1. **Vite proxy for /ingestion**
   - What we know: Vite proxies `/api` and `/health`. All ingestion endpoints are at `/ingestion/`.
   - What's unclear: Was this intentionally left un-proxied (e.g., CORS or other reason), or was it simply not needed before the UI existed?
   - Recommendation: Add `/ingestion` to the proxy in `vite.config.ts` as the first task of this phase. Verify it works in dev before building UI.

2. **Success result: "scrollable list of individual imported records"**
   - What we know: The upload response returns `inserted_ids` (platform booking IDs/confirmation codes as strings). It does NOT return rich booking data (guest names, dates, amounts).
   - What's unclear: Does the context decision's "scrollable list of individual imported records" mean showing confirmation codes, or does it mean fetching full booking details after upload?
   - Recommendation: Display confirmation codes in the scrollable list — they are meaningful identifiers. If richer data is needed, fire a follow-up `GET /ingestion/bookings` filtered by the returned IDs, but this complicates the success state. A scrollable list of confirmation codes (e.g., "HMABCDE123 · HMABCDE456 · ...") satisfies the requirement without an extra round-trip.

3. **Import history: "property" column**
   - What we know: `GET /ingestion/history` returns `id, platform, filename, inserted_count, updated_count, skipped_count, imported_at`. It does NOT return `property_slug`.
   - What's unclear: The context decision lists "property" as a column in import history. The backend endpoint doesn't return it.
   - Recommendation: The `ImportRun` model has no `property_id` foreign key — a single import run can span multiple properties (e.g., an Airbnb CSV with bookings for both properties). The "property" column in history should either be omitted (show "—") or inferred from the filename if possible. Surface this as a limitation in the plan.

## Sources

### Primary (HIGH confidence)
- Actual source files in `/Users/tunderhill/development/airbnb-tools/app/api/ingestion.py` — endpoint URLs, request/response shapes
- Actual source files in `/Users/tunderhill/development/airbnb-tools/app/ingestion/normalizer.py` — response dict structure
- Actual source files in `/Users/tunderhill/development/airbnb-tools/app/ingestion/schemas.py` — RVshareEntryRequest fields
- Actual source files in `/Users/tunderhill/development/airbnb-tools/frontend/src/components/actions/ActionItem.tsx` — useMutation pattern
- Actual source files in `/Users/tunderhill/development/airbnb-tools/frontend/src/api/client.ts` — apiFetch behavior
- `/Users/tunderhill/development/airbnb-tools/frontend/node_modules/radix-ui/dist/index.d.ts` — Progress, Label exports confirmed
- `/Users/tunderhill/development/airbnb-tools/frontend/node_modules/@radix-ui/react-progress/dist/index.d.ts` — Progress component API
- `/Users/tunderhill/development/airbnb-tools/frontend/node_modules/@radix-ui/react-label/dist/index.d.ts` — Label component API
- Prior decision [09-01] in CONTEXT.md — `/ingestion` router prefix confirmed intentional
- Prior decision [07-01] in STATE.md — Tailwind v4 @apply limitation

### Secondary (MEDIUM confidence)
- MDN Web Docs patterns for XMLHttpRequest.upload.onprogress and HTML5 drag-and-drop (standard browser APIs, stable)
- TanStack Query v5 `useMutation` pattern — consistent with existing codebase usage in `ActionItem.tsx`

### Tertiary (LOW confidence)
- None — all findings are verified against installed packages or actual source files.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against package.json and node_modules
- Architecture: HIGH — verified against existing component patterns and backend API source
- Pitfalls: HIGH — derived from actual prior decisions and source code inspection
- Open Questions: MEDIUM — identified from code gaps, recommendations are reasoned but not confirmed by user

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (stable — no fast-moving dependencies; all libraries already locked in package.json)

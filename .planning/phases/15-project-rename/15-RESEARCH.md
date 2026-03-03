# Phase 15: Project Rename - Research

**Researched:** 2026-03-03
**Domain:** Project identity transformation — Python packaging, Docker, frontend branding, SVG icon design
**Confidence:** HIGH

## Summary

Phase 15 is a pure identity transformation: every reference to "airbnb-tools" and "Rental Management Suite" is replaced with "Roost" and "Rental Operations Platform" respectively. No logic changes, no new features.

The codebase was audited exhaustively. The scope is narrower than it might appear: the Python module directory stays as `app/` (no import changes), env var NAMES stay unchanged (only some VALUES change), and the vast majority of "airbnb" references in source code are platform-specific (referring to the Airbnb booking platform) and must be kept. Only a small set of project-identity strings require updating.

The operation follows a strict order: all code changes first, then the directory rename last. Docker Compose service names have a cascading effect on the DATABASE_URL hostname in `.env.example` that must be addressed.

**Primary recommendation:** Execute changes in three logical waves: (1) Python/Docker/pyproject identity, (2) Frontend branding + SVG icon, (3) Planning docs + directory rename.

---

## Standard Stack

No new libraries are required. This phase uses only existing tooling.

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| uv | current | Regenerate uv.lock after pyproject.toml rename | Already in use |
| Docker Compose | v2 | Service renaming, image name assignment | Already in use |
| Tailwind CSS | v4.2.x | Theme CSS variable changes | Already in use |
| SVG | — | Inline favicon/logo, no external library needed | Browser-native |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `mv` / shell | — | Directory rename (final step only) | Last action in phase |
| `git mv` | — | NOT used — `mv` then `git add -A` is standard | Standard rename approach |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline SVG in `/public/roost.svg` | External icon font | SVG is simpler, no dependency, works as favicon |
| Manual file edits | `sed -i` bulk replace | Manual edits are safer given the platform/project distinction required |

---

## Architecture Patterns

### Rename Decision Tree

The critical distinction in this codebase is **platform reference** (keep) vs. **project identity reference** (change):

- **Platform references (KEEP as-is):** Any "airbnb" referring to the Airbnb booking platform, its CSV format, its fee model, its column names, its API behavior
- **Project identity references (CHANGE):** "airbnb-tools" as a project/directory name, "Rental Management Suite" as the app title, "rental-management" as the Python distribution name

### Files Requiring Changes (Complete Inventory)

**Python backend (project identity only):**

| File | What Changes | What Stays |
|------|-------------|-----------|
| `pyproject.toml` | `name = "rental-management"` → `"roost-rental"` | Everything else |
| `app/main.py` | `"Starting Rental Management Suite"` → `"Starting Roost"` ; `title="Rental Management Suite"` → `"Roost"` ; `description="Self-hosted vacation rental management platform"` → `"Rental Operations Platform"` | All Airbnb platform logic |
| `app/logging.py` | Docstring first line: `"Structlog configuration for the Rental Management Suite."` → `"Structlog configuration for Roost."` | Everything else |
| `manage.py` | Docstring `"Rental Management Suite CLI."` → `"Roost CLI."` ; `typer.Typer(help="Rental Management Suite CLI")` → `"Roost CLI"` ; echo `"Rental Management Suite — Property Setup"` → `"Roost — Property Setup"` | All property setup logic |
| `app/db.py` | Fallback DB URL `rental_management` — LEAVE AS-IS (fallback only, not project identity) | All |
| `alembic/env.py` | Fallback DB URL `rental_management` — LEAVE AS-IS (fallback only, not project identity) | All |
| `app/query/prompt.py` | `"vacation rental management system"` — this is descriptive of domain, not project identity. LEAVE AS-IS. | All |
| `uv.lock` | Regenerated automatically after `uv sync` | N/A |

**Docker:**

| File | What Changes | Notes |
|------|-------------|-------|
| `docker-compose.yml` | Service `db` → `roost-db` ; service `app` → `roost-api` ; add `image: roost` to roost-api service ; `depends_on: db:` → `depends_on: roost-db:` ; volume `db_data:` stays (avoid breaking existing installs) | See cascading DATABASE_URL note below |
| `.env.example` | `DATABASE_URL=...@db:...` → `DATABASE_URL=...@roost-db:...` (hostname only, because service was renamed) ; `POSTGRES_DB=rental_management` LEAVE AS-IS (database name, not project identity) ; `POSTGRES_USER=rental` LEAVE AS-IS | Service hostname change is the only value change |

**Frontend branding:**

| File | What Changes | What Stays |
|------|-------------|-----------|
| `frontend/package.json` | `"name": "frontend"` → `"name": "roost"` | All else |
| `frontend/index.html` | `<title>Rental Dashboard</title>` → `<title>Roost \| Rental Operations</title>` ; `href="/vite.svg"` → `href="/roost.svg"` | Structure |
| `frontend/public/roost.svg` | NEW FILE — house/nest motif SVG, warm earthy tones | — |
| `frontend/public/vite.svg` | DELETE (replaced by roost.svg) | — |
| `frontend/src/components/layout/Header.tsx` | `<h1>Rental Dashboard</h1>` → two-line `<h1>Roost</h1>` + `<p>Rental Operations</p>` ; `DARK_MODE_KEY = 'rental-dashboard-dark-mode'` → `'roost-dark-mode'` | Property selector, dark mode logic |
| `frontend/src/store/usePropertyStore.ts` | `name: 'rental-dashboard-property'` → `name: 'roost-property'` | Store logic |

**Frontend files with "airbnb" that do NOT need changes:**

These files reference "airbnb" as the booking platform and must stay unchanged:
- `frontend/src/components/actions/CsvDropZone.tsx` — platform selector "Airbnb"
- `frontend/src/components/actions/ImportHistoryAccordion.tsx` — capitalization comment/example
- `frontend/src/components/finance/MatchCandidateList.tsx` — platform color badge
- `frontend/src/components/finance/ReconciliationPanel.tsx` — platform color badge
- `frontend/src/components/home/BookingTrendChart.tsx` — platform display label
- `frontend/src/lib/platformColors.ts` — platform color definitions
- `frontend/src/components/query/StarterPrompts.tsx` — example query about Airbnb bookings

**Planning docs (active docs only — historical plans are left as historical artifacts):**

| File | What Changes |
|------|-------------|
| `.planning/MILESTONES.md` | Heading `"Rental Management Suite"` → `"Roost"` |
| `.planning/PROJECT.md` | One reference to `"airbnb-tools"` in Active requirements list |
| `.planning/REQUIREMENTS.md` | RNAM requirements descriptions reference old names (update descriptions) |
| `.planning/ROADMAP.md` | Four references to `"airbnb-tools"` and `"Rental Management Suite"` |
| `.planning/STATE.md` | Currently clean — no changes needed |

**Planning docs to LEAVE as-is (historical records):**
- All `phases/*/PLAN.md` files — these are executed historical artifacts
- `phases/*/RESEARCH.md` files — historical research
- `milestones/v1.0-MILESTONE-AUDIT.md` — historical record, its `"airbnb-tools"` references are historical context

**README.md:**

| File | What Changes |
|------|-------------|
| `README.md` | Heading `"Rental Management Suite"` → `"Roost"` ; description → updated ; `docker compose restart app` → `docker compose restart roost-api` |

### Docker Compose Service Rename Cascade

Critical dependency: when `db` service is renamed to `roost-db`, Docker creates a network alias of `roost-db` for the container. Any service connecting to the database via hostname `db` will break. The cascading fix:

1. Rename service `db` → `roost-db` in `docker-compose.yml`
2. Update `depends_on: db:` → `depends_on: roost-db:`
3. Update `.env.example` DATABASE_URL hostname: `@db:` → `@roost-db:`

The `POSTGRES_DB=rental_management` database name and `POSTGRES_USER=rental` in `.env.example` are LEFT unchanged — these are database-internal names, not project identity references, and changing them would require a database migration that is out of scope.

### Docker Compose Volume Naming

The `db_data` named volume stays as `db_data` — do NOT rename to `roost-db-data`. Renaming would orphan existing users' data. The volume name is internal and not user-visible.

The compose project name (which prefixes volume names: `airbnb-tools_db_data`) will automatically become `roost_db_data` after the directory rename, because Docker Compose derives the project name from the directory name. This is automatic and correct.

Optionally, add `name: roost` at the top level of `docker-compose.yml` to make the project name explicit and independent of directory name — recommended for clarity.

### Docker Image Name (RNAM-05)

The app service currently has no `image:` field. Docker Compose auto-generates the image name as `{project_name}-{service_name}` (e.g., `airbnb-tools-app`). To satisfy RNAM-05:

Add `image: roost` under the `roost-api` service in `docker-compose.yml`:

```yaml
  roost-api:
    build: .
    image: roost
    ...
```

### Python Distribution Name (RNAM-01)

```toml
# pyproject.toml
[project]
name = "roost-rental"        # was: "rental-management"
version = "0.1.0"
description = "Roost — Self-hosted vacation rental operations platform"
```

After editing `pyproject.toml`, run `uv sync` to regenerate `uv.lock`. The `uv.lock` entry for `name = "rental-management"` will become `name = "roost-rental"` automatically.

The `[tool.hatch.build.targets.wheel] packages = ["app"]` stays unchanged — the Python module directory remains `app/`.

### SVG Icon Design (Claude's Discretion)

Design a simple house/nest motif SVG for `frontend/public/roost.svg`. Warm earthy tones: browns, terracotta, warm gold.

Recommended design: a stylized house silhouette with a simple "arch" or "nest" shape, using:
- Terracotta/clay: `#C4622D` (primary shape)
- Warm gold: `#D4A853` (accent/roof highlight)
- Deep brown: `#6B3A2A` (outline/shadow)

As a favicon-optimized SVG (32×32 viewBox, clean shapes, no fine detail):

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <!-- Chimney -->
  <rect x="20" y="6" width="4" height="8" fill="#6B3A2A" rx="0.5"/>
  <!-- Roof -->
  <polygon points="4,16 16,4 28,16" fill="#C4622D"/>
  <!-- Roof ridge highlight -->
  <polygon points="10,16 16,10 22,16" fill="#D4A853" opacity="0.5"/>
  <!-- Wall -->
  <rect x="7" y="16" width="18" height="12" fill="#D4A853" rx="1"/>
  <!-- Door -->
  <rect x="13" y="21" width="6" height="7" fill="#6B3A2A" rx="1"/>
</svg>
```

This design works at small sizes, has strong silhouette recognition, and uses the earthy palette.

### Header Component Branding

The updated Header should show "Roost" prominently with "Rental Operations" as a small subtitle. Current layout: single `<h1>` line. Updated pattern:

```tsx
<div className="flex flex-col leading-tight shrink-0">
  <h1 className="text-lg font-bold">Roost</h1>
  <p className="text-xs text-muted-foreground">Rental Operations</p>
</div>
```

### Execution Order

All changes must happen inside `airbnb-tools/` before the directory rename:

1. `pyproject.toml` — distribution name update
2. `uv sync` — regenerate `uv.lock`
3. `docker-compose.yml` — service/image name updates
4. `.env.example` — DATABASE_URL hostname update
5. `README.md` — heading and service name reference
6. `app/main.py`, `app/logging.py`, `manage.py` — string updates
7. `frontend/package.json` — name update
8. `frontend/index.html` — title + favicon ref update
9. Create `frontend/public/roost.svg` — new SVG icon
10. Delete `frontend/public/vite.svg` — remove old icon
11. `frontend/src/components/layout/Header.tsx` — branding + localStorage key
12. `frontend/src/store/usePropertyStore.ts` — localStorage key
13. `.planning/` active docs — update references
14. Verification: `docker-compose build`, `npm run build`, `python -m pytest`
15. Provide post-rename checklist (IDE workspace, aliases, shell scripts)
16. Rename `airbnb-tools/` → `roost/` (final step)

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SVG favicon | Complex vector editor workflow | Hand-write simple SVG directly | Favicon SVGs need only basic shapes; simple paths work better at small sizes |
| uv.lock update | Manual lock file editing | `uv sync` after pyproject.toml edit | Lock files are auto-generated; never hand-edit |
| Docker project name | Hardcode everywhere | Set `name: roost` once at top of docker-compose.yml | Single source of truth |

**Key insight:** The temptation to do a broad `sed -i` replace of "airbnb" → "roost" would break all the platform-specific references (CSV adapters, fee model config, reconciliation logic). Every "airbnb" reference must be evaluated individually.

---

## Common Pitfalls

### Pitfall 1: Over-replacing "airbnb"
**What goes wrong:** A project-wide find-replace of "airbnb" → "roost" or "roost-rental" breaks the Airbnb platform adapter, fee model, CSV column names, and platform color definitions.
**Why it happens:** "airbnb" appears both as a project name component AND as a platform identifier string throughout the codebase.
**How to avoid:** Use the file-by-file inventory in this document. Only the explicitly listed strings change. Everything else stays.
**Warning signs:** Tests fail on airbnb CSV parsing; `platform == "airbnb"` comparisons break.

### Pitfall 2: Service rename breaks DATABASE_URL
**What goes wrong:** `docker-compose up` starts `roost-api` but it can't connect to the database because DATABASE_URL still has `@db:` as hostname.
**Why it happens:** Docker Compose uses the service name as the network hostname. Renaming `db` → `roost-db` changes the hostname.
**How to avoid:** Update `.env.example` DATABASE_URL to `@roost-db:` in the same commit as the service rename. Document this in user-facing notes.
**Warning signs:** "could not connect to server" or "Connection refused" on startup; health check fails.

### Pitfall 3: Directory rename before code changes
**What goes wrong:** Renaming the directory first breaks all active terminal sessions, IDE workspaces, Docker bind mounts, and git operations.
**Why it happens:** Everything referencing the absolute path `/Users/.../airbnb-tools` breaks on rename.
**How to avoid:** Directory rename is the LAST step. All file edits happen inside `airbnb-tools/` first.
**Warning signs:** Immediate shell `cd` errors; IDE loses file references.

### Pitfall 4: localStorage key change loses user state silently
**What goes wrong:** After renaming `rental-dashboard-dark-mode` → `roost-dark-mode`, all users lose their dark mode preference and property selection.
**Why it happens:** Browser localStorage is keyed by exact string. Old keys are orphaned, not migrated.
**How to avoid:** This is acceptable for a rename — note it in the checklist. The user experience impact is minor (re-select dark mode once).
**Warning signs:** N/A — expected behavior.

### Pitfall 5: docker-compose volume data loss
**What goes wrong:** If `db_data` volume is renamed to something like `roost-db-data` in docker-compose.yml, existing users lose their database on next `docker-compose up`.
**Why it happens:** Docker treats different volume names as different volumes.
**How to avoid:** Keep `db_data` volume name unchanged. Only the service names and project name change.
**Warning signs:** Database appears empty after `docker-compose up` following the rename.

### Pitfall 6: uv.lock not regenerated
**What goes wrong:** `uv.lock` still contains `name = "rental-management"`, which means a project-wide grep for the old name will find it.
**Why it happens:** uv.lock is not automatically updated when pyproject.toml changes — requires explicit `uv sync`.
**How to avoid:** Run `uv sync` immediately after editing `pyproject.toml`. Commit both files together.
**Warning signs:** Grep for "rental-management" still returns uv.lock after changes.

### Pitfall 7: RNAM-01 vs. RNAM-03 confusion
**What goes wrong:** Trying to rename the `app/` Python module directory to `roost/` to match the new package name.
**Why it happens:** RNAM-01 says "Python package renamed" — could be misread as renaming the source directory.
**How to avoid:** The Python distribution name (`roost-rental`) is what changes in pyproject.toml. The module directory stays `app/`. `[tool.hatch.build.targets.wheel] packages = ["app"]` stays unchanged. All imports (`from app.config import ...`) stay unchanged.
**Warning signs:** Attempted to mv app/ → roost/ and broke all imports.

---

## Code Examples

### docker-compose.yml After Rename

```yaml
name: roost

services:
  roost-db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  roost-api:
    build: .
    image: roost
    restart: unless-stopped
    command: >
      sh -c "/app/.venv/bin/alembic upgrade head &&
             /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000"
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config:ro
      - ./templates:/app/templates:ro
      - ./pdf_mappings:/app/pdf_mappings:ro
      - ./archive:/app/archive
      - ./confirmations:/app/confirmations:ro
    depends_on:
      roost-db:
        condition: service_healthy
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  db_data:
```

### .env.example DATABASE_URL Change

```bash
# Only the hostname changes (@db: → @roost-db:)
# Database name (rental_management) and user (rental) stay unchanged
DATABASE_URL=postgresql+psycopg://rental:changeme@roost-db:5432/rental_management
```

### app/main.py Key Changes

```python
# Line 65: startup log
log.info("Starting Roost")

# Lines 138-140: FastAPI metadata
app = FastAPI(
    title="Roost",
    description="Rental Operations Platform — Self-hosted vacation rental management",
    version="0.1.0",
    lifespan=lifespan,
)
```

### manage.py Key Changes

```python
"""
Roost CLI.

Commands:
  setup            Interactive wizard to create a new property configuration
  list-properties  List all configured properties
...
"""
cli = typer.Typer(help="Roost CLI")

# In setup():
typer.echo("  Roost — Property Setup")
```

### Header.tsx Key Changes

```tsx
const DARK_MODE_KEY = 'roost-dark-mode'

// In render:
<div className="flex flex-col leading-tight shrink-0">
  <h1 className="text-lg font-bold">Roost</h1>
  <p className="text-xs text-muted-foreground">Rental Operations</p>
</div>
```

### usePropertyStore.ts Key Change

```typescript
persist(
  (set) => ({
    selectedPropertyId: null,
    setSelectedPropertyId: (id) => set({ selectedPropertyId: id }),
  }),
  {
    name: 'roost-property',  // was: 'rental-dashboard-property'
  }
)
```

### Post-Rename User Checklist (to include in commit message or README)

After running `mv airbnb-tools roost`:

1. Update IDE workspace/project root to point to `roost/`
2. Update any shell aliases (e.g., `alias art='cd ~/development/airbnb-tools'`)
3. Update any terminal window presets or shell scripts referencing the old path
4. If using existing `.env`, update `DATABASE_URL` to use `@roost-db:` as hostname (if upgrading)
5. Run `docker-compose down` and `docker-compose up --build` to apply service renames

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Auto-derived Docker project name from directory | Explicit `name: roost` in docker-compose.yml | Docker project name is stable regardless of where the directory lives |
| Implicit image name (`airbnb-tools-app`) | Explicit `image: roost` | RNAM-05 compliant; pushable to registry under consistent name |
| Vite default favicon (`vite.svg`) | Project-specific `roost.svg` | Brand identity established |

---

## Open Questions

1. **`.env.example` database credentials scope**
   - What we know: Decision says "env vars: no prefix change — keep DATABASE_URL, SMTP_HOST, etc. as-is"
   - What's unclear: Whether "as-is" applies only to variable names or also their default values (like `POSTGRES_DB=rental_management`, `POSTGRES_USER=rental`)
   - Recommendation: Keep `POSTGRES_DB=rental_management` and `POSTGRES_USER=rental` unchanged — these are database-internal credentials, not project identity. Only the hostname in `DATABASE_URL` changes due to the service rename.

2. **README.md scope**
   - What we know: README contains "Rental Management Suite" which must change; also references `docker compose restart app` which becomes `docker compose restart roost-api`
   - What's unclear: The CONTEXT says RNAM-06 covers documentation. Phase 16 is specifically for documentation rewrite. Should README get a minimal update here (just the identity strings) or a full rewrite?
   - Recommendation: Minimal update in Phase 15 — replace identity strings only. Full README rewrite is Phase 16's job.

3. **`.planning/research/` legacy docs**
   - What we know: `SUMMARY.md` has "Airbnb Tools — Self-hosted Vacation Rental Management Suite"; `ARCHITECTURE.md` has `airbnb-tools/` path reference
   - What's unclear: CONTEXT says update STATE.md, ROADMAP.md, etc. — does "etc." include the legacy research docs?
   - Recommendation: Update `SUMMARY.md` and `ARCHITECTURE.md` only if the CONTEXT phrase "Update .planning/ docs" is interpreted broadly. Otherwise, treat them as historical. Leave them unless the user explicitly includes research docs in scope.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase audit — all tracked files inspected via `git ls-files` + grep
- `docker-compose.yml` — current service structure verified
- `pyproject.toml` — current package name verified
- `frontend/package.json` — current frontend package name verified
- `.planning/phases/15-project-rename/15-CONTEXT.md` — user decisions locked

### Secondary (MEDIUM confidence)
- Docker Compose v2 documentation — `name:` field behavior and project naming conventions
- Tailwind CSS v4 — `@theme inline` pattern confirmed from index.css (existing usage)

### Tertiary (LOW confidence)
- None — all findings are from direct codebase inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies needed; all tooling already in use
- Architecture: HIGH — complete file-by-file audit performed on tracked files
- Pitfalls: HIGH — all pitfalls identified from actual code structure, not speculation
- SVG design: MEDIUM — design recommendation based on stated aesthetic direction; exact values are Claude's discretion

**Research date:** 2026-03-03
**Valid until:** Phase 15 completion (stable domain, no fast-moving libraries)

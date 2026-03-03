# Phase 15: Project Rename - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace every reference to "airbnb-tools" and "Rental Management Suite" with "Roost" across package configs, Docker, imports, docs, and directory. The project builds and runs under its new identity. No new features or capabilities — this is purely an identity transformation.

</domain>

<decisions>
## Implementation Decisions

### Brand casing & naming
- Python distribution name: `roost-rental` in pyproject.toml (avoids PyPI name collisions)
- Python module directory stays as `app/` — no import path changes (app.config, app.models, etc.)
- Docker Compose service names: `roost-` prefix (roost-api, roost-db, roost-frontend, roost-ollama)
- Environment variables: no prefix change — keep DATABASE_URL, SMTP_HOST, etc. as-is
- "Rental Management Suite" replaced with "Rental Operations Platform" wherever it appears

### Airbnb reference handling
- Git remote URL stays unchanged — that's Phase 17 (GitHub Publication)
- Claude's discretion: keep "Airbnb" where it accurately describes the platform being integrated with; genericize where it refers to the project itself
- Claude's discretion: rename code symbols (classes, variables, modules) containing "airbnb" based on whether they're platform-specific or project-name references

### UI branding
- Browser tab title: "Roost | Rental Operations"
- App header/navbar: "Roost" prominently with "Rental Operations" as small subtitle
- Generate a simple SVG icon (house/nest motif) as favicon and logo placeholder
- Color direction: warm earthy tones (browns, terracotta, warm gold) — fits the "roost/nest" identity

### Directory rename
- Rename airbnb-tools/ to roost/ as the very last step in the phase
- Provide a checklist of what the user needs to update post-rename (IDE workspace, terminal aliases, shell scripts, etc.)
- Update .planning/ docs (STATE.md, ROADMAP.md, etc.) to reference "roost" instead of "airbnb-tools"

### Verification
- Full verification after rename: docker-compose build, frontend build, and Python tests must all pass

### Claude's Discretion
- Exact SVG icon design
- Which "Airbnb" references to keep vs. genericize (context-dependent)
- Code symbol renaming decisions (airbnb_client → keep if platform-specific, rename if project-name)
- Warm earthy tone exact color values
- Order of rename operations within plans

</decisions>

<specifics>
## Specific Ideas

- Distribution name `roost-rental` specifically chosen to avoid PyPI name collisions with a bare `roost`
- Tab title format "Roost | Rental Operations" mirrors modern SaaS patterns
- Warm earthy tones (browns, terracotta, warm gold) chosen to match the "roost/nest" brand metaphor
- Directory rename is explicitly last — all code changes happen in airbnb-tools/ first, then the final mv

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-project-rename*
*Context gathered: 2026-03-03*

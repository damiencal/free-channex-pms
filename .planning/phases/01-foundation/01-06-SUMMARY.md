---
phase: 01-foundation
plan: 06
subsystem: config
tags: [pydantic, jinja2, yaml, docker, typer, config-schema]

# Dependency graph
requires:
  - phase: 01-02
    provides: PropertyConfig BaseModel and load_all_properties validation infrastructure
  - phase: 01-05
    provides: Jinja2 template engine with StrictUndefined and SAMPLE_BOOKING_DATA pattern

provides:
  - PropertyConfig with resort_checkin_instructions required field
  - pre_arrival.txt using config-driven resort instructions (no hardcoded values)
  - README.md documenting exact two-step setup (cp .env.example + property YAML)
  - pyproject.toml manage entry point corrected to manage:cli

affects: [02-data-ingestion, 05-pdf-pipeline, all future phases using PropertyConfig]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - All property-specific content (including resort instructions) in config YAMLs — no hardcoded strings in templates
    - SAMPLE_BOOKING_DATA must be updated whenever a new template variable is added

key-files:
  created:
    - README.md
  modified:
    - app/config.py
    - app/templates.py
    - templates/default/pre_arrival.txt
    - config/config.example.yaml
    - config/jay.yaml
    - config/minnie.yaml
    - manage.py
    - pyproject.toml

key-decisions:
  - "resort_checkin_instructions is a required field (no default) — forces operator to provide property-specific instructions at config time"
  - "Pre-arrival template now fully config-driven — no hardcoded property data anywhere in templates/"

patterns-established:
  - "New template variable = update SAMPLE_BOOKING_DATA + all property YAMLs + config.example.yaml"

# Metrics
duration: 1min
completed: 2026-02-27
---

# Phase 1 Plan 06: Gap Closure Summary

**PropertyConfig extended with config-driven resort_checkin_instructions, hardcoded resort text removed from pre_arrival.txt, README.md created with exact two-step setup, and manage:cli entry point fixed**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-27T17:00:46Z
- **Completed:** 2026-02-27T17:02:19Z
- **Tasks:** 2
- **Files modified:** 9 (8 modified + 1 created)

## Accomplishments
- Removed hardcoded "Sun Retreats Fort Myers Beach" from default pre_arrival.txt by adding `resort_checkin_instructions` to PropertyConfig and using `{{ resort_checkin_instructions }}` in the template
- Created README.md documenting both required manual setup steps: `cp .env.example .env` and property YAML configuration
- Fixed pyproject.toml console script entry point from `manage:app` to `manage:cli` (manage.py defines `cli = typer.Typer()`, not `app`)
- Updated all three property YAML files (config.example.yaml, jay.yaml, minnie.yaml) and SAMPLE_BOOKING_DATA so startup validation continues to pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add resort_checkin_instructions to config schema, update template and validation, fix entry point** - `e42b3da` (feat)
2. **Task 2: Create README.md with setup instructions** - `20234fe` (docs)

**Plan metadata:** (see final commit)

## Files Created/Modified
- `README.md` - Setup documentation with exact steps to get the system running
- `app/config.py` - PropertyConfig with new required `resort_checkin_instructions: str` field
- `app/templates.py` - SAMPLE_BOOKING_DATA extended with resort_checkin_instructions key
- `templates/default/pre_arrival.txt` - Replaced hardcoded resort line with `{{ resort_checkin_instructions }}`
- `config/config.example.yaml` - New field documented with example value
- `config/jay.yaml` - New required field populated with Jay-specific instructions
- `config/minnie.yaml` - New required field populated with Minnie-specific instructions
- `manage.py` - Setup wizard prompts for resort_checkin_instructions and writes it to config
- `pyproject.toml` - Entry point corrected from `manage:app` to `manage:cli`

## Decisions Made
- `resort_checkin_instructions` has no default value — it is required like all other PropertyConfig fields, ensuring operators consciously provide property-specific text rather than silently using a generic fallback
- README kept concise and operator-focused — no badges, contributing guidelines, license sections, or changelog

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 1 Foundation verification score now 5/5 (was 3/5 before this plan)
- All must-have truths satisfied: docker-compose startup documented, no hardcoded property data in templates, manage entry point resolves correctly
- Phase 2 (data ingestion) can begin — PropertyConfig schema is stable

---
*Phase: 01-foundation*
*Completed: 2026-02-27*

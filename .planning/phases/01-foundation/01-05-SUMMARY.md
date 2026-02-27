---
phase: 01-foundation
plan: 05
subsystem: infra
tags: [jinja2, templates, pdf, typer, questionary, python-slugify, yaml, cli, structlog]

# Dependency graph
requires:
  - phase: 01-02
    provides: PropertyConfig schema with slug field; config/ YAML files for jay and minnie
  - phase: 01-03
    provides: app/ package structure; property slugs used for template resolution
provides:
  - templates/default/welcome.txt with Jinja2 variables (guest_name, property_name, checkin_date, checkout_date)
  - templates/default/pre_arrival.txt with Jinja2 variables (lock_code, site_number)
  - app/templates.py with build_template_env() (per-property FileSystemLoader override), validate_all_templates() (fail-fast startup), render_template()
  - pdf_mappings/example_form.json documenting three-source-type schema (booking/property/static) for Phase 5
  - manage.py Typer CLI with interactive setup wizard and list-properties command
  - app/main.py updated with template validation as startup step 2 (after config load, before DB check)
affects:
  - 02 (bookings — will call render_template for welcome/pre-arrival messaging)
  - 05 (PDF pipeline — pdf_mappings/ schema used to build form-filling logic)
  - all phases (manage.py setup wizard is the onboarding path for new properties)

# Tech tracking
tech-stack:
  added:
    - jinja2 (FileSystemLoader + StrictUndefined for fail-fast template validation)
    - typer (CLI framework for manage.py)
    - questionary (interactive prompt library for setup wizard)
    - python-slugify (slug normalization; avoids hand-rolling slug generation)
  patterns:
    - Per-property template override: FileSystemLoader searches [slug_dir, default_dir] in order
    - StrictUndefined: undefined template variables raise UndefinedError at render time
    - SAMPLE_BOOKING_DATA covers all template variables; used in startup validation
    - Fail-all-at-once validation: collect all template errors before raising SystemExit
    - PDF mapping schema: three source types (booking/property/static) with optional format field
    - CLI wizard: questionary prompts -> slugify -> collision check -> YAML write

key-files:
  created:
    - templates/default/welcome.txt
    - templates/default/pre_arrival.txt
    - app/templates.py
    - pdf_mappings/example_form.json
    - manage.py
  modified:
    - app/main.py (added validate_all_templates as startup step 2)

key-decisions:
  - "StrictUndefined in Jinja2 environment — raises UndefinedError on typos at render time rather than silently emitting empty string"
  - "SAMPLE_BOOKING_DATA must cover ALL template variables — startup validation uses it against every template for every property"
  - "Per-property template override via FileSystemLoader search path order — templates/{slug}/ before templates/default/"
  - "PDF mapping schema uses three source types (booking/property/static) — 'static' for resort-policy N/A fields like guest phone/email"
  - "python-slugify for slug normalization — never hand-roll slug generation (RESEARCH.md pitfall 7)"
  - "CLI wizard checks slug collisions from existing YAML files, not DB — config files are source of truth in Phase 1"
  - "sort_keys=False in yaml.dump — preserves field order in generated YAML for readability"

patterns-established:
  - "Template override: create templates/{slug}/{template_name}.txt to override default for a specific property"
  - "Template validation: validate_all_templates([slugs]) is called in lifespan after config load, before DB check"
  - "PDF mapping schema: one JSON file per form type in pdf_mappings/; each field maps to booking/property/static source"

# Metrics
duration: 3min
completed: 2026-02-27
---

# Phase 1 Plan 05: Jinja2 Templates, PDF Mapping Schema, and CLI Wizard Summary

**Jinja2 FileSystemLoader template engine with per-property overrides, three-source-type PDF field mapping schema, and Typer+questionary CLI setup wizard with slug collision detection**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-27T16:31:51Z
- **Completed:** 2026-02-27T16:34:23Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Jinja2 template engine with per-property override resolution: `templates/{slug}/` takes priority over `templates/default/` via FileSystemLoader search path ordering
- Startup template validation using `StrictUndefined` catches variable typos across all property templates before the app accepts any requests
- PDF field mapping schema documented with three source types (booking, property, static) — ready for Phase 5 form filling
- Interactive CLI wizard creates valid property YAML configs with questionary prompts, python-slugify normalization, and slug collision detection against existing config files
- Template validation wired into FastAPI lifespan as step 2 (after config load, before DB check)

## Task Commits

Each task was committed atomically:

1. **Task 1: Jinja2 template engine with per-property override resolution and default templates** - `178e9b1` (feat)
2. **Task 2: PDF mapping schema, CLI setup wizard, and template validation wired to startup** - `fb52479` (feat)

**Plan metadata:** _(docs commit — see below)_

## Files Created/Modified

- `templates/default/welcome.txt` - Default welcome message with guest_name, property_name, checkin_date, checkout_date
- `templates/default/pre_arrival.txt` - Default pre-arrival message with lock_code, site_number, property_name
- `app/templates.py` - build_template_env() (FileSystemLoader with slug/default priority), validate_all_templates() (fail-all-at-once startup check), render_template() (property+template+data → string)
- `pdf_mappings/example_form.json` - Documented example mapping schema: 9 fields with booking/property/static sources, format key for date fields
- `manage.py` - Typer CLI: `setup` wizard (questionary prompts, slugify, collision detection, YAML write) + `list-properties` command
- `app/main.py` - Added `validate_all_templates` import and call as lifespan step 2; renumbered DB check to 3, Ollama check to 4

## Decisions Made

- **StrictUndefined in Jinja2**: Raises UndefinedError on undefined variables at render time rather than silently producing empty string. Catches template typos at startup validation.
- **SAMPLE_BOOKING_DATA covers all variables**: The sample data dict must include every variable used in any template across any property. Adding a new variable to a template requires adding it to SAMPLE_BOOKING_DATA or startup validation will fail.
- **python-slugify for slug normalization**: The wizard slugifies both the default suggestion and the user input. Prevents invalid slug formats (spaces, uppercase, special chars) without hand-rolling validation.
- **Config files as source of truth (Phase 1)**: The CLI wizard reads existing slugs from YAML files (not the DB) for collision detection. Property-to-DB sync deferred to future plan (Phase 2 or startup upsert).
- **PDF mapping schema source types**: Three types — `booking` (from imported booking data), `property` (from property config), `static` (hardcoded value). Static source handles resort-policy constraints like guest phone/email marked N/A.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 2 (data ingestion): `render_template()` is ready to send welcome/pre-arrival messages after booking import
- Phase 5 (PDF compliance): `pdf_mappings/` schema is documented; actual Sun Retreats form fields to be mapped after PDF inspection (blocker in STATE.md: AcroForm vs. XFA unverified)
- New properties: `python manage.py setup` is the onboarding path; creates valid YAML config in `config/`
- Template customization: operators create `templates/{slug}/` directory with overriding templates; no code changes needed

---
*Phase: 01-foundation*
*Completed: 2026-02-27*

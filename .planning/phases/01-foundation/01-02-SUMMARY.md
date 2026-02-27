---
phase: 01-foundation
plan: 02
subsystem: config
tags: [pydantic-settings, yaml, pyyaml, config, fail-fast, property-config]

# Dependency graph
requires:
  - phase: 01-01
    provides: pydantic-settings[yaml] installed, uv-managed environment, config/ bind-mount in docker-compose.yml
provides:
  - app/config.py with AppConfig, PropertyConfig, load_app_config, get_config
  - config/base.yaml with system-wide defaults (ollama_url)
  - config/config.example.yaml as documented template for new properties
  - config/jay.yaml (Unit 110) and config/minnie.yaml (Unit 170) property configs
  - Fail-fast validation that collects all errors and exits with per-field messages
  - Dynamic glob discovery of per-property YAML files (not hardcoded to jay/minnie)
  - Singleton config pattern: load once at startup, access via get_config()
affects:
  - 01-03 (app skeleton — imports get_config() from this module in lifespan)
  - 01-04 (database migrations — alembic env.py may need DATABASE_URL from config)
  - 01-05 (templates — PropertyConfig.slug used for template directory resolution)
  - all subsequent phases (AppConfig and PropertyConfig are foundational data types)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - pydantic-settings YamlConfigSettingsSource for base.yaml → AppConfig
    - PropertyConfig as plain BaseModel (not BaseSettings) — one per yaml file
    - settings_customise_sources: env > .env > base.yaml priority stack
    - load_all_properties(): glob discovery + collect-all-errors fail-fast
    - Module-level singleton (_config) with load_app_config() + get_config() accessors

key-files:
  created:
    - app/config.py
    - config/base.yaml
    - config/config.example.yaml
    - config/jay.yaml
    - config/minnie.yaml
  modified: []

key-decisions:
  - "PropertyConfig is BaseModel not BaseSettings — per-property YAMLs loaded manually via glob, not by pydantic-settings"
  - "load_all_properties() collects ALL validation errors before raising SystemExit — operator sees every problem at once"
  - "config.example.yaml excluded from property discovery by name — allows it to coexist with real configs"
  - "CHANGE_ME placeholders in jay.yaml and minnie.yaml — real values are personal data, not secrets, but not committed"

patterns-established:
  - "Secrets in .env only: database_url from .env; no passwords or API keys in any YAML file"
  - "Dynamic discovery: config/*.yaml glob excludes base.yaml and config.example.yaml by name"
  - "Fail-fast with full error list: collect all errors, single SystemExit with human-readable lines"
  - "Singleton pattern: load_app_config() caches result in _config; get_config() raises if not loaded"

# Metrics
duration: 3min
completed: 2026-02-27
---

# Phase 1 Plan 02: Pydantic Settings Config Schema Summary

**pydantic-settings AppConfig + per-property PropertyConfig with YamlConfigSettingsSource, glob discovery, and fail-fast validation printing every missing field**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-27T16:26:27Z
- **Completed:** 2026-02-27T16:29:01Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Config subsystem loads config/base.yaml (via YamlConfigSettingsSource) + .env (DATABASE_URL secret) into AppConfig
- Per-property YAML files discovered dynamically via glob — extensible to any number of properties without code changes
- Fail-fast validation collects all field errors across all property files before exiting — operator sees every problem in one run
- Duplicate slug detection prevents two properties from claiming the same identifier

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Pydantic Settings config schema with YAML + .env loading** - `06d45ba` (feat)
2. **Task 2: Create base.yaml, config.example.yaml, and per-property config files** - `5f26618` (feat)

**Plan metadata:** _(final docs commit — see below)_

## Files Created/Modified

- `app/config.py` - AppConfig (BaseSettings, yaml_file=config/base.yaml) + PropertyConfig (BaseModel) + load_all_properties() + load_app_config() + get_config()
- `config/base.yaml` - System-wide defaults: ollama_url only; no secrets
- `config/config.example.yaml` - Documented template with all 5 required PropertyConfig fields and inline comments
- `config/jay.yaml` - Unit 110 property config with CHANGE_ME placeholders for lock_code and resort_contact_email
- `config/minnie.yaml` - Unit 170 property config with CHANGE_ME placeholders for lock_code and resort_contact_email

## Decisions Made

- **PropertyConfig as BaseModel (not BaseSettings):** Per-property YAMLs can't use pydantic-settings source loading because the list of files is dynamic. Each file is loaded manually with `yaml.safe_load()` + `PropertyConfig(**data)`, giving full Pydantic validation with clean per-field error messages.
- **Collect-all-errors fail-fast pattern:** `load_all_properties()` accumulates all ValidationError messages across all files before raising `SystemExit`. This means an operator with 5 misconfigured properties sees all 5 errors in one run, not one error per restart.
- **`config.example.yaml` exclusion by name:** The exclusion list `("base.yaml", "config.example.yaml")` lets the example file coexist permanently in config/ without being loaded as a property. New operators can read it in place without moving it first.
- **CHANGE_ME placeholders:** jay.yaml and minnie.yaml contain `CHANGE_ME` for lock_code and resort_contact_email. These values are personal operational data (not secrets requiring encryption), but they shouldn't be committed with real values to a repository. The app validates them as non-empty strings — operators must fill them in before the system sends messages.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

Operators must replace `CHANGE_ME` placeholders in `config/jay.yaml` and `config/minnie.yaml` with real values before the system can send guest communications:
- `lock_code` — door access code for pre-arrival messages
- `resort_contact_email` — email address for booking form submissions

These changes take effect after container restart (config/ is bind-mounted).

## Next Phase Readiness

- Plan 01-03 (app skeleton): `get_config()` is ready to call from FastAPI lifespan; `AppConfig.properties` gives the list of property slugs for template directory resolution
- Plan 01-04 (database): `PropertyConfig.slug` provides the business key for the `properties` table rows; `AppConfig.database_url` provides the connection string
- Plan 01-05 (templates/PDF): `PropertyConfig.slug` maps directly to `templates/{slug}/` override directories
- All subsequent phases: `PropertyConfig` is the canonical property data type; all downstream components import from `app.config`

**No blockers.** Config subsystem complete and verified.

---
*Phase: 01-foundation*
*Completed: 2026-02-27*

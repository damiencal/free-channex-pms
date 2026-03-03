---
phase: 16-documentation
plan: 02
subsystem: docs
tags: [docker, fastapi, contributing, deployment, smtp, ollama, postgresql, yaml-config]

# Dependency graph
requires:
  - phase: 16-01
    provides: README.md exists; project described for new readers
provides:
  - CONTRIBUTING.md with full bare-metal and Docker dev environment setup
  - docs/deployment.md with step-by-step Docker self-hosting guide
  - docs/ directory established for remaining phase documentation
affects:
  - 16-03 (architecture doc goes in docs/)
  - 16-04 (API doc goes in docs/)
  - Any contributor or self-hoster reading the repo

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "docs/ directory established for architecture, API, and deployment guides"
    - "SMTP documented as required (not optional) for compliance/communication features"
    - "Ollama documented as optional with explicit graceful degradation language"

key-files:
  created:
    - CONTRIBUTING.md
    - docs/deployment.md
  modified: []

key-decisions:
  - "SMTP is required in deployment guide — resort form submission silently fails without it"
  - "Ollama is optional — health endpoint shows 'unavailable' but status stays 'ok'"
  - "listing_slug_map explanation included — critical for multi-property CSV assignment to work"
  - "Gmail App Password guidance included — SMTP_PASSWORD is not the Gmail account password"
  - "auto_submit_threshold set to 0 documented as the way to disable auto-submission"

patterns-established:
  - "Deployment guide uses field reference tables for all config options (not just prose)"
  - "CONTRIBUTING.md covers both bare-metal and Docker paths in parallel"

# Metrics
duration: 3min
completed: 2026-03-03
---

# Phase 16 Plan 02: CONTRIBUTING.md and Deployment Guide Summary

**CONTRIBUTING.md and docs/deployment.md — complete developer onboarding and Docker self-hosting guide with full config field reference, SMTP required, Ollama optional**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T22:50:18Z
- **Completed:** 2026-03-03T22:52:58Z
- **Tasks:** 2
- **Files modified:** 2 created

## Accomplishments

- CONTRIBUTING.md covers prerequisites, bare-metal setup (backend + frontend), Docker Compose alternative with hot-reload override, project structure reference, code style guidelines, PR process, and issue reporting
- docs/deployment.md is a 7-step copy-pasteable Docker self-hosting guide with every .env variable, base.yaml field, and property config field documented in reference tables
- SMTP is explicitly required with Gmail App Password guidance; Ollama is explicitly optional with clear degradation explanation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CONTRIBUTING.md** - `7fcc0b6` (docs)
2. **Task 2: Create docs/deployment.md** - `4c5a083` (docs)

**Plan metadata:** _(committed with SUMMARY.md)_

## Files Created/Modified

- `CONTRIBUTING.md` — Developer onboarding: prerequisites, backend setup (uv/alembic/uvicorn), frontend setup (npm/Vite), Docker alternative, project structure, code style, PR and issue guidelines
- `docs/deployment.md` — Self-hoster guide: .env configuration, base.yaml walkthrough, property config field reference, startup and verification steps, Ollama setup, templates, PDF forms, updating, troubleshooting

## Decisions Made

- SMTP documented as required, not optional — resort form email submission silently fails without it, and the config fields have empty-string defaults that can mislead self-hosters into thinking it's optional
- `listing_slug_map` given its own explanation section — it is non-obvious and critical; without it, CSV imports assign bookings to no property
- Gmail App Password guidance added inline — self-hosters commonly try their account password first, which fails with Gmail's security model
- `auto_submit_threshold: 0` documented as the way to disable automatic form submission for operators who want manual approval on all submissions
- `host.docker.internal` Linux workaround documented in both Ollama section and troubleshooting — this is a common Docker pain point on Linux hosts

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required beyond what the deployment guide covers.

## Next Phase Readiness

- `docs/` directory is established and ready for architecture.md (Plan 03) and api.md (Plan 04)
- Both documents are consistent with the actual codebase (config fields read directly from `app/config.py` and example YAML files)
- Self-hoster can go zero-to-running following docs/deployment.md; developer can set up a local environment following CONTRIBUTING.md

---
*Phase: 16-documentation*
*Completed: 2026-03-03*

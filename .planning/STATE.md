# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-02)

**Core value:** Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration
**Current focus:** v1.1 Open Source Release — Phase 16: Documentation

## Current Position

Phase: 16 of 17 (Documentation)
Plan: 01 of 4 complete (16-01-PLAN.md done)
Status: In progress — Phase 16 plan 1 complete
Last activity: 2026-03-03 — Completed 16-01-PLAN.md (README.md + CHANGELOG.md)

Progress: [█████░░░░░] 53% (2.25/4 phases complete in v1.1)

## Performance Metrics

**v1.0 Milestone:**
- Total plans completed: 56
- Total phases: 13
- Total commits: 244
- Python LOC: 10,725
- TypeScript LOC: 9,734
- Timeline: 5 days (2026-02-26 -> 2026-03-02)

**v1.1 Milestone:**
- Total plans completed: 8 (14-01, 14-02, 14-03, 14-04, 15-01, 15-02, 15-03, 16-01)
- Total phases: 4 (Phases 14-17)
- Phases complete: 2 (Phase 14, Phase 15)
- Requirements: 27 (17 complete, 10 remaining)

## Accumulated Context

### Decisions

All v1.0 decisions archived in `.planning/milestones/v1.0-ROADMAP.md`.

v1.1 decisions (16-01 additions):
- README badges placed one per line (not inline) — renders identically on GitHub; satisfies grep-countability
- Screenshots kept as placeholders in README — deferred until running dev instance with populated data
- CHANGELOG v1.0.0 dated 2026-03-02 (actual ship date) not 2026-03-03 (documentation date)
- README cross-reference links to docs/architecture.md, docs/api.md, docs/deployment.md, CONTRIBUTING.md established before those files exist

v1.1 decisions:
- Apache 2.0 license selected for open source release
- Full rename to "Roost" for professional branding
- Package distribution name: roost-rental (not roost — avoids PyPI collision risk, more descriptive)
- Docker service names: roost-api and roost-db (service name == DATABASE_URL hostname)
- POSTGRES_DB=rental_management and db_data volume left unchanged — database implementation detail, not project identity; changing would break existing installs
- image: roost added to docker-compose roost-api for named Docker image builds
- config/*.yaml gitignored; only example templates (base.example.yaml, config.example.yaml) tracked
- Empty string default (not CHANGE_ME) for resort_contact_name in app/config.py — fails clearly at runtime if unconfigured
- CHANGE_ME sentinel pattern for all PII placeholder fields in tracked config templates
- pypdf (BSD-3-Clause) replaces pymupdf (AGPL-3.0) as the PDF library
- psycopg (LGPL-3.0), text-unidecode (Artistic/GPL dual), certifi (MPL-2.0) confirmed acceptable for Apache 2.0 distribution
- pypdf direct annotation /V update used instead of update_page_form_field_values() due to pypdf 6.7.5 bug with WinAnsiEncoding fonts
- NOTICE lists direct dependencies only (not transitive) per Apache 2.0 common practice
- git-filter-repo --replace-text affects author names too — requires separate --name-callback pass to restore author attribution
- Copyright holder name (Thomas Underhill) in LICENSE/NOTICE is legal attribution, not PII
- Active requirement descriptions in REQUIREMENTS.md and ROADMAP.md must not embed old identity strings — use forward-looking language that passes grep verification
- research/ directory files are active docs (not historical artifacts) — excluded only .planning/phases/ and .planning/milestones/ from identity verification

### Pending Todos

None.

### Blockers/Concerns

None.

### Tech Debt Carried Forward

14 low-severity items from v1.0 (see `.planning/milestones/v1.0-MILESTONE-AUDIT.md`). None blocking v1.1 work.

## Session Continuity

Last session: 2026-03-03T22:50:46Z
Stopped at: Completed 16-01-PLAN.md
Resume file: None
Next action: Execute 16-02-PLAN.md (CONTRIBUTING.md)

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-02)

**Core value:** Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration
**Current focus:** v1.1 Open Source Release — Phase 15: Project Rename

## Current Position

Phase: 15 of 17 (Project Rename)
Plan: 0 of TBD in current phase
Status: Not started — Phase 14 complete, ready to plan Phase 15
Last activity: 2026-03-03 — Phase 14 complete (4 plans, 3 waves, verified)

Progress: [██░░░░░░░░] 25% (1/4 phases complete in v1.1)

## Performance Metrics

**v1.0 Milestone:**
- Total plans completed: 56
- Total phases: 13
- Total commits: 244
- Python LOC: 10,725
- TypeScript LOC: 9,734
- Timeline: 5 days (2026-02-26 -> 2026-03-02)

**v1.1 Milestone:**
- Total plans completed: 4 (14-01, 14-02, 14-03, 14-04)
- Total phases: 4 (Phases 14-17)
- Phases complete: 1 (Phase 14)
- Requirements: 27 (10 complete, 17 remaining)

## Accumulated Context

### Decisions

All v1.0 decisions archived in `.planning/milestones/v1.0-ROADMAP.md`.

v1.1 decisions:
- Apache 2.0 license selected for open source release
- Full rename to "Roost" for professional branding
- config/*.yaml gitignored; only example templates (base.example.yaml, config.example.yaml) tracked
- Empty string default (not CHANGE_ME) for resort_contact_name in app/config.py — fails clearly at runtime if unconfigured
- CHANGE_ME sentinel pattern for all PII placeholder fields in tracked config templates
- pypdf (BSD-3-Clause) replaces pymupdf (AGPL-3.0) as the PDF library
- psycopg (LGPL-3.0), text-unidecode (Artistic/GPL dual), certifi (MPL-2.0) confirmed acceptable for Apache 2.0 distribution
- pypdf direct annotation /V update used instead of update_page_form_field_values() due to pypdf 6.7.5 bug with WinAnsiEncoding fonts
- NOTICE lists direct dependencies only (not transitive) per Apache 2.0 common practice
- git-filter-repo --replace-text affects author names too — requires separate --name-callback pass to restore author attribution
- Copyright holder name (Thomas Underhill) in LICENSE/NOTICE is legal attribution, not PII

### Pending Todos

None.

### Blockers/Concerns

None.

### Tech Debt Carried Forward

14 low-severity items from v1.0 (see `.planning/milestones/v1.0-MILESTONE-AUDIT.md`). None blocking v1.1 work.

## Session Continuity

Last session: 2026-03-03
Stopped at: Phase 14 complete and verified, ready to plan Phase 15
Resume file: None
Next action: /gsd:discuss-phase 15 or /gsd:plan-phase 15

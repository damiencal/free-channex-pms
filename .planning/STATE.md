# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-02)

**Core value:** Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration
**Current focus:** v1.1 Open Source Release — Phase 14: License Audit & Repository Hygiene

## Current Position

Phase: 14 of 17 (License Audit & Repository Hygiene)
Plan: 3 of 4 in current phase
Status: In progress — plans 01-03 complete, plan 04 remaining
Last activity: 2026-03-03 — Completed 14-03-PLAN.md (gitignore, PII scrub, config templates)

Progress: [░░░░░░░░░░] 0% v1.0 complete → v1.1 in progress (3/4 plans done)

## Performance Metrics

**v1.0 Milestone:**
- Total plans completed: 56
- Total phases: 13
- Total commits: 244
- Python LOC: 10,725
- TypeScript LOC: 9,734
- Timeline: 5 days (2026-02-26 -> 2026-03-02)

**v1.1 Milestone:**
- Total plans completed: 3 (14-01, 14-02, 14-03)
- Total phases: 4 (Phases 14-17)
- Requirements: 27

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

### Pending Todos

None.

### Blockers/Concerns

None.

### Tech Debt Carried Forward

14 low-severity items from v1.0 (see `.planning/milestones/v1.0-MILESTONE-AUDIT.md`). None blocking v1.1 work.

## Session Continuity

Last session: 2026-03-03T06:59:21Z
Stopped at: Completed 14-01-PLAN.md (license audit + pymupdf → pypdf replacement)
Resume file: None
Next action: Execute 14-04-PLAN.md (rename to Roost)

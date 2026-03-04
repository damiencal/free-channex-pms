# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-02)

**Core value:** Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration
**Current focus:** v1.1 Open Source Release — COMPLETE

## Current Position

Phase: 17 of 17 (GitHub Publication)
Plan: 2 of 2 complete
Status: COMPLETE — repository public, v1.0.0 release live
Last activity: 2026-03-04 — Completed 17-02-PLAN.md (public flip and v1.0.0 release)

Progress: [██████████] 100% (4/4 phases complete in v1.1)

## Performance Metrics

**v1.0 Milestone:**
- Total plans completed: 56
- Total phases: 13
- Total commits: 244
- Python LOC: 10,725
- TypeScript LOC: 9,734
- Timeline: 5 days (2026-02-26 -> 2026-03-02)

**v1.1 Milestone:**
- Total plans completed: 13 (14-01 through 14-04, 15-01 through 15-03, 16-01 through 16-04, 17-01 through 17-02)
- Total phases: 4 (Phases 14-17)
- Phases complete: 4 (Phase 14, Phase 15, Phase 16, Phase 17) — ALL COMPLETE
- Requirements: 27 (27 complete, 0 remaining)

## Accumulated Context

### Decisions

All v1.0 decisions archived in `.planning/milestones/v1.0-ROADMAP.md`.

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
- README badges placed one per line (not inline) — renders identically on GitHub; satisfies grep-countability
- Screenshots kept as placeholders in README — deferred until running dev instance with populated data
- CHANGELOG v1.0.0 dated 2026-03-02 (actual ship date) not 2026-03-03 (documentation date)
- SMTP documented as required in deployment guide — resort form submission silently fails without it
- listing_slug_map given its own explanation — critical for multi-property CSV assignment
- Gmail App Password guidance added inline in deployment guide
- 4-diagram structure for architecture doc: system components graph, automation pipeline sequence, full ERD, startup sequence graph
- Automation pipeline documented as async-after-response pattern (BackgroundTasks fire after HTTP response returns)
- Airbnb messaging documented as native_configured — platform delivers, Roost only logs and notifies operator
- reconciliation/confirm body uses booking_id + bank_transaction_id (not match_id) — verified from MatchConfirmRequest schema
- GitHub Licensee requires exact canonical text from choosealicense.com — non-canonical Apache 2.0 variants fail SPDX detection
- Apache 2.0 copyright attribution belongs in NOTICE only — copyright header in LICENSE blocks GitHub Licensee fingerprinting
- v1.0.0 tag created separately from existing v1.0 — both coexist; v1.0.0 is the canonical SemVer public release tag
- Release notes written inline (not --notes-from-tag) — v1.0 tag annotation contains internal planning details not suitable for public release notes
- Screenshot links removed from README before public flip (de5c16e) — clean launch with no broken images

### Pending Todos

None.

### Blockers/Concerns

None.

### Tech Debt Carried Forward

14 low-severity items from v1.0 (see `.planning/milestones/v1.0-MILESTONE-AUDIT.md`). None blocking v1.1 work.

## Session Continuity

Last session: 2026-03-04
Stopped at: Completed 17-02-PLAN.md — repository public, v1.0.0 release live
Resume file: None
Next action: None — v1.1 milestone complete. Roost is publicly available at https://github.com/captainarcher/roost

# Roadmap: Roost

## Milestones

- v1.0 MVP - Phases 1-13 (shipped 2026-03-02)
- **v1.1 Open Source Release** - Phases 14-17 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-13) - SHIPPED 2026-03-02</summary>

See `.planning/milestones/v1.0-ROADMAP.md` for full v1.0 phase history.

13 phases, 56 plans, 244 commits. Complete vacation rental management platform with automated accounting, resort compliance, guest communication, and AI-powered natural language interface.

</details>

### v1.1 Open Source Release (In Progress)

**Milestone Goal:** Prepare the codebase for open source publication — audit licenses, scrub private data, rename to Roost, write documentation, and publish to GitHub as captainarcher/roost.

- [ ] **Phase 14: License Audit & Repository Hygiene** - Ensure all dependencies are Apache 2.0-compatible and all private data is excluded from git
- [ ] **Phase 15: Project Rename** - Rename everything from "airbnb-tools" to "Roost" across package configs, Docker, imports, docs, and directory
- [ ] **Phase 16: Documentation** - Create comprehensive open source documentation (README, CONTRIBUTING, architecture, API, deployment, CHANGELOG)
- [ ] **Phase 17: GitHub Publication** - Create repository, push code, and verify GitHub detects license

## Phase Details

### Phase 14: License Audit & Repository Hygiene
**Goal**: The codebase is legally clean and free of private data, ready for public exposure
**Depends on**: Phase 13 (v1.0 complete)
**Requirements**: LICS-01, LICS-02, LICS-03, LICS-04, LICS-05, HYGN-01, HYGN-02, HYGN-03, HYGN-04, HYGN-05
**Success Criteria** (what must be TRUE):
  1. Every Python and npm dependency has a license compatible with Apache 2.0 (MIT, BSD, Apache 2.0, ISC, PSF) — no GPL/LGPL/unknown licenses remain
  2. A LICENSE file with the full Apache 2.0 text exists at the repo root
  3. A NOTICE file lists all third-party dependencies and their licenses
  4. .gitignore excludes .env, archive/, real configs, db_data/, confirmations/, and CSVs — and no real names, addresses, guest data, or financial data exist in any tracked file
  5. config.example.yaml exists with only CHANGE_ME placeholder values, and git history contains no leaked secrets or PII
**Plans**: 4 plans

Plans:
- [ ] 14-01-PLAN.md — License audit + replace pymupdf (AGPL) with pypdf (BSD)
- [ ] 14-02-PLAN.md — Create LICENSE and NOTICE files
- [ ] 14-03-PLAN.md — Update .gitignore and scrub PII from tracked configs
- [ ] 14-04-PLAN.md — Rewrite git history to remove PII + gitleaks verification

### Phase 15: Project Rename
**Goal**: Every reference to "airbnb-tools" and "Rental Management Suite" is replaced with "Roost" — the project builds and runs under its new identity
**Depends on**: Phase 14 (licenses resolved before renaming — no point renaming a dependency that gets replaced)
**Requirements**: RNAM-01, RNAM-02, RNAM-03, RNAM-04, RNAM-05, RNAM-06, RNAM-07
**Success Criteria** (what must be TRUE):
  1. Python package is named `roost` in pyproject.toml and all imports resolve correctly
  2. Docker Compose uses `roost-` prefixed service names and `roost` image name — `docker-compose up` builds and runs successfully
  3. Frontend package.json name is `roost` and the app builds without errors
  4. A project-wide search for "airbnb-tools" and "Rental Management Suite" returns zero results in any tracked file
  5. The local directory is renamed from `airbnb-tools` to `roost` (final task in this phase)
**Plans**: TBD

Plans:
- [ ] 15-01: [TBD]

### Phase 16: Documentation
**Goal**: A developer or self-hoster can understand, set up, contribute to, and deploy Roost from the documentation alone
**Depends on**: Phase 15 (docs must reference "Roost" names, not old names)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06
**Success Criteria** (what must be TRUE):
  1. README.md provides a clear project description, feature overview, quick start guide, and badge placeholders — a visitor understands what Roost does within 30 seconds
  2. CONTRIBUTING.md explains how to set up a dev environment, code style expectations, and how to submit a PR
  3. Architecture and API docs exist — a developer can understand the system's components, data flow, and every endpoint with request/response examples
  4. Deployment guide walks through Docker setup, config file creation, Ollama setup, and SMTP configuration — a new user can self-host from scratch
  5. CHANGELOG.md exists with a v1.0 release entry documenting what shipped
**Plans**: TBD

Plans:
- [ ] 16-01: [TBD]

### Phase 17: GitHub Publication
**Goal**: Roost is publicly available on GitHub with proper metadata, and the repository is ready for community discovery
**Depends on**: Phase 16 (all code, docs, and license must be finalized before push)
**Requirements**: GHUB-01, GHUB-02, GHUB-03, GHUB-04
**Success Criteria** (what must be TRUE):
  1. GitHub repository exists at captainarcher/roost
  2. Repository has a description, relevant topics (vacation-rental, property-management, self-hosted, docker, fastapi, react), and homepage set
  3. Initial push includes all code, documentation, and LICENSE file
  4. GitHub's license detection shows Apache 2.0 on the repository page
**Plans**: TBD

Plans:
- [ ] 17-01: [TBD]

## Progress

**Execution Order:** 14 -> 15 -> 16 -> 17

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 14. License Audit & Repository Hygiene | v1.1 | 0/4 | Planning complete | - |
| 15. Project Rename | v1.1 | 0/TBD | Not started | - |
| 16. Documentation | v1.1 | 0/TBD | Not started | - |
| 17. GitHub Publication | v1.1 | 0/TBD | Not started | - |

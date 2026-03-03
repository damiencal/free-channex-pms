# Requirements: Roost

**Defined:** 2026-03-02
**Core Value:** Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration.

## v1.1 Requirements

### License Compliance

- [ ] **LICS-01**: All Python dependencies use licenses compatible with Apache 2.0 (MIT, BSD, Apache 2.0, ISC, PSF)
- [ ] **LICS-02**: All npm dependencies (production + dev) use licenses compatible with Apache 2.0
- [ ] **LICS-03**: Any LGPL, GPL, or incompatible-licensed dependency is replaced with an Apache 2.0-compatible alternative
- [ ] **LICS-04**: A LICENSE file with the full Apache 2.0 license text exists at the repo root
- [ ] **LICS-05**: A NOTICE file lists all third-party dependencies and their licenses per Apache 2.0 requirements

### Project Rename

- [ ] **RNAM-01**: Python package renamed from `rental-management` to `roost` in pyproject.toml
- [ ] **RNAM-02**: Docker Compose service names use `roost-` prefix (roost-app, roost-db)
- [ ] **RNAM-03**: All Python imports use `app/` package (verify no `rental-management` references remain)
- [ ] **RNAM-04**: Frontend package.json name changed to `roost`
- [ ] **RNAM-05**: Docker image name uses `roost` (not `airbnb-tools`)
- [ ] **RNAM-06**: All documentation, comments, and strings referencing "airbnb-tools" or "Rental Management Suite" updated to "Roost"
- [ ] **RNAM-07**: Local directory renamed from `airbnb-tools` to `roost`

### Documentation

- [ ] **DOCS-01**: README.md with project description, feature overview, screenshots placeholder, quick start guide, and badge placeholders
- [ ] **DOCS-02**: CONTRIBUTING.md with development setup, code style, PR process, and issue guidelines
- [ ] **DOCS-03**: Architecture overview document explaining system components, data flow, and tech stack
- [ ] **DOCS-04**: API documentation listing all endpoints with request/response examples
- [ ] **DOCS-05**: Deployment guide covering Docker setup, config file creation, Ollama setup, and SMTP configuration
- [ ] **DOCS-06**: CHANGELOG.md with v1.0 release entry

### Repository Hygiene

- [ ] **HYGN-01**: .gitignore excludes all private data: .env, archive/, config/*.yaml (except config.example.yaml), db_data/, confirmations/, *.csv
- [ ] **HYGN-02**: No real property names, addresses, guest data, or financial data exists in tracked files
- [ ] **HYGN-03**: config.example.yaml contains only placeholder/example values (CHANGE_ME pattern)
- [ ] **HYGN-04**: Any committed sample data uses clearly fake values
- [ ] **HYGN-05**: git history reviewed — no secrets or PII in any committed file (or clean history if found)

### GitHub Publication

- [ ] **GHUB-01**: GitHub repository created at captainarcher/roost
- [ ] **GHUB-02**: Repository has description, topics (vacation-rental, property-management, self-hosted, docker, fastapi, react), and homepage
- [ ] **GHUB-03**: Initial push includes all code, docs, and LICENSE
- [ ] **GHUB-04**: GitHub repository has Apache 2.0 license detected by GitHub

## Out of Scope

| Feature | Reason |
|---------|--------|
| CI/CD pipeline (GitHub Actions) | Can be added post-publish; not needed for initial release |
| Automated testing in CI | Tests exist locally; CI setup is v1.2 work |
| GitHub Pages documentation site | Markdown docs in repo sufficient for launch |
| Pre-built Docker images on GHCR | Users build locally via docker-compose; registry publishing is future work |
| Issue templates | Can be added iteratively after initial community feedback |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LICS-01 | Phase 14 | Pending |
| LICS-02 | Phase 14 | Pending |
| LICS-03 | Phase 14 | Pending |
| LICS-04 | Phase 14 | Pending |
| LICS-05 | Phase 14 | Pending |
| RNAM-01 | Phase 15 | Pending |
| RNAM-02 | Phase 15 | Pending |
| RNAM-03 | Phase 15 | Pending |
| RNAM-04 | Phase 15 | Pending |
| RNAM-05 | Phase 15 | Pending |
| RNAM-06 | Phase 15 | Pending |
| RNAM-07 | Phase 15 | Pending |
| DOCS-01 | Phase 16 | Pending |
| DOCS-02 | Phase 16 | Pending |
| DOCS-03 | Phase 16 | Pending |
| DOCS-04 | Phase 16 | Pending |
| DOCS-05 | Phase 16 | Pending |
| DOCS-06 | Phase 16 | Pending |
| HYGN-01 | Phase 14 | Pending |
| HYGN-02 | Phase 14 | Pending |
| HYGN-03 | Phase 14 | Pending |
| HYGN-04 | Phase 14 | Pending |
| HYGN-05 | Phase 14 | Pending |
| GHUB-01 | Phase 17 | Pending |
| GHUB-02 | Phase 17 | Pending |
| GHUB-03 | Phase 17 | Pending |
| GHUB-04 | Phase 17 | Pending |

**Coverage:**
- v1.1 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0

---
*Requirements defined: 2026-03-02*
*Traceability updated: 2026-03-02*

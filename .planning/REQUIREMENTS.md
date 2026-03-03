# Requirements: Roost

**Defined:** 2026-03-02
**Core Value:** Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration.

## v1.1 Requirements

### License Compliance

- [x] **LICS-01**: All Python dependencies use licenses compatible with Apache 2.0 (MIT, BSD, Apache 2.0, ISC, PSF)
- [x] **LICS-02**: All npm dependencies (production + dev) use licenses compatible with Apache 2.0
- [x] **LICS-03**: Any LGPL, GPL, or incompatible-licensed dependency is replaced with an Apache 2.0-compatible alternative
- [x] **LICS-04**: A LICENSE file with the full Apache 2.0 license text exists at the repo root
- [x] **LICS-05**: A NOTICE file lists all third-party dependencies and their licenses per Apache 2.0 requirements

### Project Rename

- [x] **RNAM-01**: Python package renamed from `rental-management` to `roost-rental` in pyproject.toml
- [x] **RNAM-02**: Docker Compose service names use `roost-` prefix (roost-api, roost-db)
- [x] **RNAM-03**: All Python imports use `app/` package (verify no `rental-management` references remain)
- [x] **RNAM-04**: Frontend package.json name changed to `roost`
- [x] **RNAM-05**: Docker image name uses `roost`
- [x] **RNAM-06**: All documentation, comments, and strings updated to reference "Roost" — no old identity strings remain in tracked files
- [ ] **RNAM-07**: Local directory named `roost`

### Documentation

- [ ] **DOCS-01**: README.md with project description, feature overview, screenshots placeholder, quick start guide, and badge placeholders
- [ ] **DOCS-02**: CONTRIBUTING.md with development setup, code style, PR process, and issue guidelines
- [ ] **DOCS-03**: Architecture overview document explaining system components, data flow, and tech stack
- [ ] **DOCS-04**: API documentation listing all endpoints with request/response examples
- [ ] **DOCS-05**: Deployment guide covering Docker setup, config file creation, Ollama setup, and SMTP configuration
- [ ] **DOCS-06**: CHANGELOG.md with v1.0 release entry

### Repository Hygiene

- [x] **HYGN-01**: .gitignore excludes all private data: .env, archive/, config/*.yaml (except config.example.yaml), db_data/, confirmations/, *.csv
- [x] **HYGN-02**: No real property names, addresses, guest data, or financial data exists in tracked files
- [x] **HYGN-03**: config.example.yaml contains only placeholder/example values (CHANGE_ME pattern)
- [x] **HYGN-04**: Any committed sample data uses clearly fake values
- [x] **HYGN-05**: git history reviewed — no secrets or PII in any committed file (or clean history if found)

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
| LICS-01 | Phase 14 | Complete |
| LICS-02 | Phase 14 | Complete |
| LICS-03 | Phase 14 | Complete |
| LICS-04 | Phase 14 | Complete |
| LICS-05 | Phase 14 | Complete |
| RNAM-01 | Phase 15 | Complete |
| RNAM-02 | Phase 15 | Complete |
| RNAM-03 | Phase 15 | Complete |
| RNAM-04 | Phase 15 | Complete |
| RNAM-05 | Phase 15 | Complete |
| RNAM-06 | Phase 15 | Complete |
| RNAM-07 | Phase 15 | Pending |
| DOCS-01 | Phase 16 | Pending |
| DOCS-02 | Phase 16 | Pending |
| DOCS-03 | Phase 16 | Pending |
| DOCS-04 | Phase 16 | Pending |
| DOCS-05 | Phase 16 | Pending |
| DOCS-06 | Phase 16 | Pending |
| HYGN-01 | Phase 14 | Complete |
| HYGN-02 | Phase 14 | Complete |
| HYGN-03 | Phase 14 | Complete |
| HYGN-04 | Phase 14 | Complete |
| HYGN-05 | Phase 14 | Complete |
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
*Traceability updated: 2026-03-03*

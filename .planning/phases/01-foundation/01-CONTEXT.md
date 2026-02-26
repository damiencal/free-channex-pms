# Phase 1: Foundation - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Project scaffolding, Docker deployment, config schema, and database with migrations. The system runs, deploys, and loads configuration — everything else is built on top of this. No business logic, no data processing, no UI.

</domain>

<decisions>
## Implementation Decisions

### Config file experience
- Per-property config files: `config/` directory with `base.yaml` + one YAML per property (e.g., `jay.yaml`, `minnie.yaml`)
- Secrets (DB passwords, API keys, SMTP credentials) in `.env`; everything else in YAML config files
- Fail fast on config validation errors — app refuses to start and prints exactly what's wrong (e.g., "config/jay.yaml: missing 'lock_code' field")
- Config changes require a container restart — no hot-reload in v1

### Database schema scope
- Minimal per phase — Phase 1 defines only what Phase 1 needs; each later phase adds its own tables/columns via new Alembic migrations
- Properties are extensible first-class entities with unique identifiers and human-friendly short names (not hardcoded for two properties)
- System designed for resale to other hosts — any number of properties, not limited to Jay and Minnie
- Initial setup via CLI wizard (`python manage.py setup`) that walks through property onboarding and generates config files, plus a well-documented `config.example.yaml` for manual setup
- GUI property onboarding in Phase 7 (dashboard)

### First-run experience
- Verbose startup log: each service reports status line by line ("Database connected ✓", "Ollama reachable ✓", "Config loaded: 2 properties ✓")
- Single mode — no dev/prod split for v1 (self-hosted tool, production hardening not critical yet)
- Ollama not required to start — system starts fully functional with Ollama status shown as "unavailable"; LLM features disabled until Ollama comes up
- Health endpoint (`GET /health`) returns detailed diagnostics: DB connection status, Ollama status, loaded properties, last import time, etc.

### Template format
- Email/message templates as separate `.txt` or `.md` files in a `templates/` directory, not inline in YAML
- Per-property template overrides: global defaults in `templates/default/`, property-specific overrides in `templates/{property}/` (e.g., `templates/jay/welcome.txt` overrides `templates/default/welcome.txt`)
- PDF field mappings in JSON format — one mapping file per form type
- All templates validated on startup — system checks templates render correctly with sample data, catches variable name typos before they matter

### Claude's Discretion
- Config synced to DB vs config-only for properties (pick what works best for downstream SQL joins)
- Property identifier format (UUID, slug, auto-increment)
- Exact CLI wizard implementation and prompt flow
- Template variable syntax (Jinja2, Mustache, etc.)
- Logging framework and format
- Docker base image selection

</decisions>

<specifics>
## Specific Ideas

- "Since this will be released externally, enable properties to be extended for additional rental properties" — design for multi-host use from day one
- Properties have a unique identifier with a short name (jay, minnie for this user) — not hardcoded, generated during onboarding
- Setup wizard creates config files; later the dashboard GUI can also onboard properties

</specifics>

<deferred>
## Deferred Ideas

- GUI property onboarding — Phase 7 (Dashboard)
- Hot-reload config without restart — future enhancement if needed

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-02-26*

# Roost

## What This Is

An open-source, self-hosted vacation rental management platform that automates accounting, resort compliance, and guest communication across multiple booking platforms (Airbnb, VRBO, RVshare). Designed for small-scale vacation rental owners who want zero-touch operations with full financial visibility. Runs in Docker with an Ollama-powered natural language interface for non-technical users.

## Core Value

Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration.

## Requirements

### Validated

- ✓ Process financial exports from Airbnb, VRBO, RVshare, and Mercury bank into unified bookkeeping — v1.0
- ✓ Generate P&L statements, balance sheets, and income statements — v1.0
- ✓ Track revenue, expenses, loans, rent, and utilities across properties — v1.0
- ✓ Provide a dashboard showing key financial and operational data — v1.0
- ✓ Offer a natural language query interface (via local Ollama) for non-technical users to ask financial questions — v1.0
- ✓ Auto-detect new bookings from platform notifications/exports — v1.0
- ✓ Auto-fill resort PDF booking form with guest and booking details from config-driven mappings — v1.0
- ✓ Attach booking confirmation and email completed form to resort contact — v1.0
- ✓ Send welcome message via platform messaging upon booking confirmation — v1.0
- ✓ Send arrival message via platform messaging 2-3 days before check-in with property details and lock codes — v1.0
- ✓ All property-specific data (unit names, lock codes, resort contacts, templates, etc.) lives in configuration files — v1.0
- ✓ Message templates are user-editable and stored in config — v1.0
- ✓ Fully containerized with Docker for self-hosting — v1.0

### Active

- [ ] All dependencies use Apache 2.0-compatible licenses
- [ ] Project identity unified as "Roost" everywhere (package, Docker, imports, configs, directory)
- [ ] Comprehensive open source documentation (README, CONTRIBUTING, LICENSE, architecture, API, deployment)
- [ ] All private data excluded from git (env files, configs with secrets, logs, sample data, archive)
- [ ] Published to GitHub as captainarcher/roost

### Out of Scope

- Dynamic/guest-specific lock code integration — future enhancement, static codes sufficient for v1
- Mobile app — web dashboard accessed from any device
- Multi-user access control — two users (owner + spouse), no role-based permissions needed
- Direct booking / own website — relies entirely on third-party platforms
- Real-time sync with booking platforms — batch/polling approach acceptable

## Context

- **Properties:** Two vacation rental units at Sun Retreats Fort Myers Beach (Jay=Unit 110, Minnie=Unit 170)
- **Platforms:** Airbnb, VRBO, RVshare — each has different export formats and API availability
- **Banking:** Mercury business bank account
- **Resort requirement:** Sun Outdoors Booking Form must be submitted with booking confirmation at least 3 days before arrival. Host info is pre-populated; guest phone/email fields marked N/A. Form goes to resort Welcome Center via email.
- **Users:** Thomas (primary operator, technical), Kim (spouse, needs simple interface — no business/financial background)
- **Infrastructure:** Self-hosted on local network machine running Ollama, deployed via Docker
- **Open source:** Intended for GitHub publication — all configuration externalized, no hardcoded property-specific data
- **Codebase:** v1.0 shipped — 10,725 lines Python (FastAPI + SQLAlchemy), 9,734 lines TypeScript (React + Vite + shadcn/ui), PostgreSQL database with Alembic migrations
- **Tech debt:** 14 low-severity items carried forward (config placeholders, unverified CSV headers, cache invalidation gaps, stale docstrings)

## Constraints

- **Hosting**: Self-hosted Docker on local network — no cloud services for core functionality
- **LLM**: Local Ollama instance — no external API calls for the natural language interface
- **Configuration**: All property-specific data must be in config files, not code — open-source ready
- **Platform APIs**: Airbnb supports reservation CSV exports; VRBO supports CSV exports; RVshare has no export format (manual entry)
- **PDF Form**: Specific Sun Outdoors Booking Form format — but the system supports configurable PDF form filling via field mapping JSON

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Self-hosted Docker deployment | User has local infrastructure, wants data sovereignty | ✓ Good — single `docker-compose up` deploys all services |
| Local Ollama for LLM queries | Already running on local network, no external API costs | ✓ Good — text-to-SQL with llama3.2, no external calls |
| Config-driven architecture | Open-source ready, no hardcoded property data | ✓ Good — YAML configs for properties, templates, PDF mappings |
| Batch/polling for booking detection | Simpler than real-time webhooks, acceptable latency | ✓ Good — CSV upload approach works well for small scale |
| Platform messaging (not direct email) for guest comms | Messages go through Airbnb/VRBO/RVshare messaging systems | ✓ Good — Airbnb native triggers + operator email for VRBO |
| Polars for CSV ingestion | 5-25x faster than pandas, less memory | ✓ Good — fast imports with low resource usage |
| PyMuPDF for PDF form filling | pypdf doesn't regenerate appearance streams (blank in Preview/iOS) | ✓ Good — field.update() + doc.bake() renders in all viewers |
| Double-entry bookkeeping | Accurate financial tracking with balanced ledger | ✓ Good — every transaction has balanced debits/credits |
| React + Vite + shadcn/ui for frontend | Modern, fast, accessible component library | ✓ Good — clean dashboard accessible to non-technical users |
| Text-to-SQL (never LLM arithmetic) | Accuracy and verifiability | ✓ Good — every number comes from SQL, not LLM |

| Apache 2.0 license for open source release | Standard permissive license, compatible with commercial use | — Pending |
| Full rename to "Roost" | Professional branding for open source, removes platform-specific name | — Pending |

---
*Last updated: 2026-03-02 after v1.1 milestone start*

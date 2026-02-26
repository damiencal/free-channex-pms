# Rental Management Suite

## What This Is

An open-source, self-hosted vacation rental management platform that automates accounting, resort compliance, and guest communication across multiple booking platforms (Airbnb, VRBO, RVshare). Designed for small-scale vacation rental owners who want zero-touch operations with full financial visibility. Runs in Docker with an Ollama-powered natural language interface for non-technical users.

## Core Value

Automated end-to-end rental operations — from booking notification to accounting entry — with zero manual intervention after initial configuration.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Process financial exports from Airbnb, VRBO, RVshare, and Mercury bank into unified bookkeeping
- [ ] Generate P&L statements, balance sheets, and income statements
- [ ] Track revenue, expenses, loans, rent, and utilities across properties
- [ ] Provide a dashboard showing key financial and operational data
- [ ] Offer a natural language query interface (via local Ollama) for non-technical users to ask financial questions
- [ ] Auto-detect new bookings from platform notifications/exports
- [ ] Auto-fill resort PDF booking form with guest and booking details from config-driven mappings
- [ ] Attach booking confirmation and email completed form to resort contact
- [ ] Send welcome message via platform messaging upon booking confirmation
- [ ] Send arrival message via platform messaging 2-3 days before check-in with property details and lock codes
- [ ] All property-specific data (unit names, lock codes, resort contacts, templates, etc.) lives in configuration files
- [ ] Message templates are user-editable and stored in config
- [ ] Fully containerized with Docker for self-hosting

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

## Constraints

- **Hosting**: Self-hosted Docker on local network — no cloud services for core functionality
- **LLM**: Local Ollama instance — no external API calls for the natural language interface
- **Configuration**: All property-specific data must be in config files, not code — open-source ready
- **Platform APIs**: Airbnb confirmed to support reservation exports; VRBO and RVshare API/export availability needs research
- **PDF Form**: Specific Sun Outdoors Booking Form format — but the system should support configurable PDF form filling, not hardcode this form

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Self-hosted Docker deployment | User has local infrastructure, wants data sovereignty | — Pending |
| Local Ollama for LLM queries | Already running on local network, no external API costs | — Pending |
| Config-driven architecture | Open-source ready, no hardcoded property data | — Pending |
| Batch/polling for booking detection | Simpler than real-time webhooks, acceptable latency | — Pending |
| Platform messaging (not direct email) for guest comms | Messages go through Airbnb/VRBO/RVshare messaging systems | — Pending |

---
*Last updated: 2026-02-26 after initialization*

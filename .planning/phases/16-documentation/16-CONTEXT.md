# Phase 16: Documentation - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Create comprehensive open source documentation so a developer or self-hoster can understand, set up, contribute to, and deploy Roost from the documentation alone. Deliverables: README.md, CONTRIBUTING.md, architecture doc, API doc, deployment guide, CHANGELOG.md.

</domain>

<decisions>
## Implementation Decisions

### README tone & structure
- Professional and concise tone — clean, minimal, let the project speak for itself (think Fastify or Caddy)
- Above the fold: description, feature bullet list, then quick start — give visitors context before asking them to install
- Include screenshots of key dashboard views (dashboard, booking detail, accounting)
- Badges: Claude's discretion on which badges to include

### Docs depth & audience
- Primary audience: self-hosters — people who want to deploy and run Roost for their own vacation rentals
- File organization: README, CONTRIBUTING, CHANGELOG at repo root; architecture, API, deployment guides in `docs/` directory
- Deployment guide: step-by-step walkthrough spelling out every command — assumes reader has Docker but not FastAPI/Postgres experience
- Deployment covers Docker only — bare metal / dev mode setup goes in CONTRIBUTING.md if needed

### Architecture doc scope
- Detailed walkthrough — component responsibilities, data flow, key design decisions and rationale (3-5 pages)
- Include Mermaid diagrams (inline code blocks that render on GitHub)
- Dedicated section for the end-to-end automation pipeline (booking -> accounting -> compliance -> communication) — this is the core differentiator
- Include entity relationship diagram (ERD) for the data model

### API documentation format
- Both auto-generated and hand-written: link to FastAPI's built-in /docs for full OpenAPI spec, plus curated markdown guide for key workflows
- Hand-written guide organized by workflow ("Process a new booking", "Generate a financial report") not by resource
- Curl examples for key workflows only — minor endpoints get descriptions without full examples

### CHANGELOG format
- Follow keepachangelog.com format: Added, Changed, Fixed, Removed sections per version
- v1.0 entry documenting what shipped

### Claude's Discretion
- Badge selection for README
- Exact screenshot selection and placement
- CONTRIBUTING.md dev environment setup depth
- Which workflows warrant curl examples in API docs
- Mermaid diagram styling and level of detail

</decisions>

<specifics>
## Specific Ideas

- README should present features before quick start — visitors should understand what Roost does before being asked to install it
- Architecture doc should emphasize what makes Roost unique: the full automation pipeline from booking notification to accounting entry
- Deployment guide should be copy-paste friendly — a new self-hoster follows the commands sequentially and has a running instance

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-documentation*
*Context gathered: 2026-03-03*

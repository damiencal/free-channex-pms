# Phase 17: GitHub Publication - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Publish Roost to GitHub as a public open source repository at captainarcher/roost. Set up repository metadata for discoverability, push all code and documentation, create a v1.0 release, and verify GitHub detects the Apache 2.0 license. Repository creation, configuration, and initial release only — ongoing community management is out of scope.

</domain>

<decisions>
## Implementation Decisions

### Push strategy
- Push full git history (history was scrubbed of PII in Phase 14 — shows project evolution)
- Create repository as **private first**, review rendering and metadata on GitHub, then flip to public
- Set captainarcher/roost as the new origin remote (replace any existing origin)
- Default branch: `main` (already in use)

### Repository metadata
- Description: "Automated vacation rental management — booking to accounting with zero manual intervention"
- Topics: Claude's discretion — optimize for discoverability (starting set from roadmap: vacation-rental, property-management, self-hosted, docker, fastapi, react — extend as appropriate)
- Homepage URL: leave blank for now — add later if a docs site or demo exists
- Social preview image: skip for now — use GitHub's default preview

### Repository settings
- Enable Issues + Discussions (Issues for bugs/features, Discussions for questions and community)
- Disable Wiki (docs live in the repo)
- No branch protection rules — solo maintainer, keep it simple
- Skip issue/PR templates for initial launch — add later if community grows
- Skip FUNDING.yml — no sponsor links for now

### Release & tagging
- Create a GitHub Release for v1.0.0 alongside the initial push
- Tag name: `v1.0.0` (semantic versioning with patch number)
- Release notes: shorter summary with link to CHANGELOG.md for full details
- Just v1.0.0 — open source prep (v1.1) is invisible infrastructure, not a user-facing release

### Claude's Discretion
- Exact topic selection beyond the base set
- Release notes wording
- Order of operations for the gh CLI commands
- Whether to verify any additional GitHub rendering (README, badges, etc.)

</decisions>

<specifics>
## Specific Ideas

- Repository target: captainarcher/roost (from roadmap requirements)
- Private-first approach lets user review how README, badges, license, and docs render on GitHub before going public

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-github-publication*
*Context gathered: 2026-03-03*

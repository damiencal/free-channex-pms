# Phase 17: GitHub Publication - Research

**Researched:** 2026-03-03
**Domain:** GitHub repository creation, configuration, and release via gh CLI
**Confidence:** HIGH

## Summary

This phase publishes Roost to GitHub as a public open source repository at captainarcher/roost using the gh CLI (v2.79.0, already installed and authenticated as captainarcher). All locked decisions are verifiable with exact gh CLI flags sourced from live help output. The gh CLI provides a complete, scriptable workflow covering repository creation, metadata editing, visibility change, and release creation — no third-party tooling is needed.

The standard approach is: create the repo as private using `gh repo create` with `--source` and `--push`, configure metadata with `gh repo edit`, flip visibility to public with `--visibility public`, then create the GitHub Release with `gh release create`. This order matches the user's "private first, review, then flip" decision and avoids pushing to a public repo accidentally.

One important pre-existing condition to handle: there is already a local annotated git tag `v1.0` in the repo. The plan calls for a `v1.0.0` release. These are two different tags — `v1.0.0` does not exist yet and must be created. Also, the repo currently has no origin remote configured, which means `gh repo create` with `--source=. --remote=origin` will work cleanly without the existing-remote conflict.

**Primary recommendation:** Use the gh CLI exclusively. Create private repo with `--source=. --remote=origin --push`, configure all metadata with `gh repo edit`, flip to public with `--visibility public --accept-visibility-change-consequences`, then create the release with `gh release create v1.0.0`.

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| gh CLI | 2.79.0 (installed) | Repository creation, metadata, releases | Official GitHub CLI — single tool for all operations |
| git | system | Tag creation, remote management | Already in use throughout project |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| GitHub web UI | n/a | Verify rendering of README, badges, license badge | Manual spot-check after each metadata change |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| gh CLI | GitHub API via curl | gh CLI is far simpler and already authenticated |
| gh CLI | GitHub web UI | Web UI can't be scripted or verified in tasks |

**Installation:** gh CLI is already installed at v2.79.0 and authenticated as captainarcher. No installation needed.

## Architecture Patterns

### Recommended Operation Order

The locked decision is "private first, review, then flip to public." This dictates the exact sequence:

```
1. Create repo (private) + push history
2. Configure metadata (description, topics, features)
3. Review rendering on GitHub (README, license badge, topics)
4. Flip visibility to public
5. Create git tag v1.0.0
6. Create GitHub Release v1.0.0
```

Steps 5 and 6 happen after going public so the release is immediately visible to users.

### Pattern 1: Create Private Repo from Existing Local Repo

**What:** Use `gh repo create` with `--source` and `--push` to create the GitHub remote and push the full history in one step.
**When to use:** Always — this is the correct approach when local repo has no origin remote.

```bash
# Source: gh repo create --help (live, verified 2026-03-03)
gh repo create captainarcher/roost \
  --private \
  --description "Automated vacation rental management — booking to accounting with zero manual intervention" \
  --source=. \
  --remote=origin \
  --push
```

Note: `--disable-wiki` is available in `gh repo create` but `--enable-discussions` is NOT — discussions must be enabled afterward with `gh repo edit`.

### Pattern 2: Configure Repository Metadata

**What:** Use `gh repo edit` to set topics, enable discussions, and disable wiki after creation.
**When to use:** After repo creation — some flags (topics, discussions) are only available in `gh repo edit`.

```bash
# Source: gh repo edit --help (live, verified 2026-03-03)
# Add topics one at a time (--add-topic accepts 'strings' type)
gh repo edit captainarcher/roost \
  --add-topic vacation-rental \
  --add-topic property-management \
  --add-topic self-hosted \
  --add-topic docker \
  --add-topic fastapi \
  --add-topic react \
  --add-topic airbnb \
  --add-topic python \
  --add-topic typescript \
  --add-topic automation \
  --add-topic accounting \
  --add-topic open-source \
  --enable-issues \
  --enable-discussions \
  --enable-wiki=false
```

### Pattern 3: Flip Visibility to Public

**What:** `gh repo edit --visibility public` requires the `--accept-visibility-change-consequences` flag.
**When to use:** After private-phase review confirms everything renders correctly.

```bash
# Source: gh repo edit --help (live, verified 2026-03-03)
gh repo edit captainarcher/roost \
  --visibility public \
  --accept-visibility-change-consequences
```

### Pattern 4: Create Annotated Tag and GitHub Release

**What:** Create a new annotated git tag `v1.0.0` (different from existing `v1.0`), push it, then create the GitHub Release.
**When to use:** After going public, so the release is immediately visible.

```bash
# Source: git documentation + gh release create --help (live, verified 2026-03-03)

# Step 1: Create new annotated tag v1.0.0
git tag -a v1.0.0 -m "v1.0.0 - Initial open source release"

# Step 2: Push the tag to GitHub
git push origin v1.0.0

# Step 3: Create release with custom notes
gh release create v1.0.0 \
  --title "v1.0.0 - Initial Open Source Release" \
  --notes "See [CHANGELOG.md](CHANGELOG.md) for full details." \
  --latest
```

### Anti-Patterns to Avoid

- **Adding `--enable-discussions` to `gh repo create`:** This flag does not exist in `gh repo create`. Only `--disable-issues` and `--disable-wiki` exist there. Discussions must be enabled via `gh repo edit`.
- **Using `--source=. --push` when an origin remote already exists:** This will fail with "Unable to add remote 'origin'". In this case the remote does not yet exist, so this is safe.
- **Trying to rename `v1.0` to `v1.0.0`:** Git tags cannot be renamed. Create `v1.0.0` as a new tag alongside `v1.0`. Both can coexist pointing to the same or different commits.
- **Using `--notes-from-tag` for the release:** The existing `v1.0` tag annotation contains internal planning details (stats, phase counts). `v1.0.0` should use custom `--notes` pointing to CHANGELOG.md instead.
- **Creating the release before going public:** Release will exist but is visible immediately — do after flip.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Remote creation + first push | Manual git remote add + git push | `gh repo create --source=. --remote=origin --push` | Handles authentication and URL automatically |
| Repository metadata | GitHub API calls | `gh repo edit` | Built-in, handles auth, idempotent |
| Visibility change | Web UI click | `gh repo edit --visibility public` | Scriptable, verifiable |
| Release creation | Manual GitHub web UI | `gh release create` | Automatable, captures tag atomically |

**Key insight:** Every step of this phase is a single gh CLI command. No custom scripting, no API calls, no web UI required.

## Common Pitfalls

### Pitfall 1: `--enable-discussions` Not Available in `gh repo create`

**What goes wrong:** Attempting to pass `--enable-discussions` to `gh repo create` fails with "unknown flag."
**Why it happens:** `gh repo create` only has `--disable-issues` and `--disable-wiki` feature flags. Discussions enablement is a `gh repo edit` operation only.
**How to avoid:** Always enable discussions via `gh repo edit` after creation.
**Warning signs:** Unknown flag error from gh CLI.

### Pitfall 2: `--accept-visibility-change-consequences` Required

**What goes wrong:** `gh repo edit --visibility public` fails without the accept flag.
**Why it happens:** GitHub requires explicit acknowledgment of consequences (lost stars, detached forks, etc.) even for new repositories.
**How to avoid:** Always pass `--accept-visibility-change-consequences` alongside `--visibility`.
**Warning signs:** gh CLI error mentioning "consequences."

### Pitfall 3: v1.0 Tag Already Exists — v1.0.0 Must Be Created Separately

**What goes wrong:** Assuming `v1.0.0` exists when the repo already has a `v1.0` annotated tag. These are different and both will be pushed to GitHub.
**Why it happens:** The v1.0 tag was created during the milestone completion phase.
**How to avoid:** Create a new `git tag -a v1.0.0` explicitly. Both tags will coexist on GitHub; this is fine.
**Warning signs:** If you try `gh release create v1.0` instead of `v1.0.0`, the release will use the wrong tag name.

### Pitfall 4: Apache 2.0 License Detection — Full Text Required

**What goes wrong:** GitHub's license detector (Licensee) fails to detect Apache 2.0 if the LICENSE file contains only the boilerplate notice.
**Why it happens:** Licensee matches against full license text templates, not abbreviated notices.
**How to avoid:** The existing LICENSE file in roost is 200 lines with the full Apache 2.0 text — this is correct format and Licensee will detect it.
**Warning signs:** No license badge appearing on the repository page after push.

### Pitfall 5: Topics With Invalid Characters

**What goes wrong:** Topics with spaces, uppercase letters, or special characters are rejected.
**Why it happens:** GitHub topics must be lowercase, use hyphens only, max 50 characters, max 20 topics total.
**How to avoid:** Use only lowercase-with-hyphens topic strings.
**Warning signs:** `gh repo edit` error when adding topics.

### Pitfall 6: `--add-topic` May Return 404 in Edge Cases

**What goes wrong:** Rare 404 error from `gh repo edit --add-topic` on owned repositories.
**Why it happens:** Token scope issue; the captainarcher account is already authenticated with correct repo scope so this should not occur.
**How to avoid:** Verify with `gh auth status` before running. If it occurs, run `GH_DEBUG=api gh repo edit --add-topic ...` to diagnose.
**Warning signs:** HTTP 404 from API during topic add.

## Code Examples

Verified commands from live gh CLI help (2026-03-03):

### Complete Operation Sequence

```bash
# 1. Create private repo, add origin remote, push full history
gh repo create captainarcher/roost \
  --private \
  --description "Automated vacation rental management — booking to accounting with zero manual intervention" \
  --disable-wiki \
  --source=. \
  --remote=origin \
  --push

# 2. Configure topics and features (cannot be done in create step)
gh repo edit captainarcher/roost \
  --add-topic vacation-rental \
  --add-topic property-management \
  --add-topic self-hosted \
  --add-topic docker \
  --add-topic fastapi \
  --add-topic react \
  --add-topic airbnb \
  --add-topic python \
  --add-topic typescript \
  --add-topic automation \
  --add-topic accounting \
  --add-topic open-source \
  --enable-discussions

# 3. Verify rendering privately (manual step — open in browser)
# Check: README renders, license badge shows Apache 2.0, topics visible

# 4. Flip to public
gh repo edit captainarcher/roost \
  --visibility public \
  --accept-visibility-change-consequences

# 5. Create v1.0.0 tag (v1.0 already exists — this is a new, separate tag)
git tag -a v1.0.0 -m "v1.0.0 - Initial open source release"
git push origin v1.0.0

# 6. Create GitHub Release
gh release create v1.0.0 \
  --title "v1.0.0 - Initial Open Source Release" \
  --notes "Roost is a self-hosted vacation rental management platform with automated accounting, resort compliance, and AI-powered financial queries.

See [CHANGELOG.md](CHANGELOG.md) for the complete list of features and changes." \
  --latest
```

### Verify License Detection

```bash
# Check GitHub's license detection via API after push
gh api repos/captainarcher/roost --jq '.license'
# Expected: {"key":"apache-2.0","name":"Apache License 2.0",...}
```

### Verify Repo Metadata

```bash
# Verify topics, description, and settings were applied
gh repo view captainarney/roost --json description,repositoryTopics,hasIssuesEnabled,hasDiscussionsEnabled,hasWikiEnabled
```

## Topic Selection Recommendation

The locked base set is: `vacation-rental, property-management, self-hosted, docker, fastapi, react`.

Recommended additions based on ecosystem research and GitHub discoverability:

| Topic | Rationale |
|-------|-----------|
| `airbnb` | Common search term for vacation rental tools |
| `python` | Primary backend language — ecosystem discoverability |
| `typescript` | Frontend language — ecosystem discoverability |
| `automation` | Core value proposition |
| `accounting` | Differentiator vs other rental tools |
| `open-source` | Discoverability for people seeking OSS alternatives |

Total: 12 topics. GitHub limit is 20 — room to add more later.

GitHub topic rules (verified from official docs):
- Lowercase only
- Hyphens only (no spaces, underscores, or special characters)
- Max 50 characters each
- Max 20 topics per repository

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual git push + GitHub web UI | `gh repo create --source=. --push` | gh CLI v1.0+ | Single command replaces multi-step web flow |
| Web UI for repo settings | `gh repo edit` flags | gh CLI v2.x | Scriptable, verifiable metadata configuration |
| Manual release creation | `gh release create` | gh CLI v1.x | Fully automatable release workflow |

**Deprecated/outdated:**
- Using the GitHub API directly via curl for repo creation: Replaced by `gh repo create` which handles auth automatically.
- Creating releases via git notes: GitHub Releases (`gh release create`) is the standard approach.

## Open Questions

1. **Should `--disable-wiki` be passed at creation time or via `gh repo edit`?**
   - What we know: `--disable-wiki` IS available in `gh repo create` (verified from help output)
   - Recommendation: Pass it at creation time to minimize the number of commands. `gh repo edit --enable-wiki=false` also works if forgotten.

2. **Should the v1.0.0 release notes reference CHANGELOG.md with a relative path or full URL?**
   - What we know: GitHub renders release notes as Markdown. Relative paths like `CHANGELOG.md` will link correctly within the repo context.
   - Recommendation: Use `[CHANGELOG.md](CHANGELOG.md)` — GitHub renders this as a link to the file in the default branch.

3. **What happens to the existing `v1.0` tag when pushed?**
   - What we know: Both `v1.0` and `v1.0.0` will appear in GitHub's tag list. GitHub does not create a release for `v1.0` automatically — only for `v1.0.0` which will have an explicit release created.
   - Recommendation: This is fine. `v1.0` will appear as a tag without an associated release. `v1.0.0` will have the full release.

## Sources

### Primary (HIGH confidence)

- `gh repo create --help` — Live output from installed gh 2.79.0, verified 2026-03-03
- `gh repo edit --help` — Live output from installed gh 2.79.0, verified 2026-03-03
- `gh release create --help` — Live output from installed gh 2.79.0, verified 2026-03-03
- `git tag v1.0 show` — Live output confirming existing v1.0 annotated tag
- `https://cli.github.com/manual/gh_repo_create` — Official gh CLI manual
- `https://cli.github.com/manual/gh_repo_edit` — Official gh CLI manual
- `https://cli.github.com/manual/gh_release_create` — Official gh CLI manual
- `https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics` — Official GitHub Docs for topic rules

### Secondary (MEDIUM confidence)

- `https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository` — GitHub license detection docs (Licensee-based, Apache 2.0 requires full text)
- `https://github.com/licensee/licensee/issues/103` — Confirmed: full Apache 2.0 text required for detection
- `https://github.com/cli/cli/issues/7127` — Existing origin remote conflict pattern documented

### Tertiary (LOW confidence)

- WebSearch results for topic discoverability (vacation-rental, property-management GitHub topics) — used for topic selection recommendations only

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against live installed gh CLI 2.79.0
- Architecture (operation sequence): HIGH — all flags verified from official help output
- Pitfalls: HIGH — confirmed from official documentation and live CLI behavior
- Topic recommendations: MEDIUM — based on GitHub ecosystem research and official topic rules

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (gh CLI stable, GitHub API stable)

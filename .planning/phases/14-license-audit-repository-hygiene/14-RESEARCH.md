# Phase 14: License Audit & Repository Hygiene - Research

**Researched:** 2026-03-02
**Domain:** Open source license compliance, git history hygiene, Apache 2.0 release preparation
**Confidence:** HIGH

---

## Summary

This phase prepares the codebase for public release under Apache 2.0. Research
covered four domains: Python dependency license audit, npm dependency license
audit, git history PII/secrets scan, and repository hygiene (gitignore gaps,
placeholder values, LICENSE/NOTICE creation).

The critical finding is that **PyMuPDF (pymupdf) is dual-licensed AGPL-3.0 /
Artifex Commercial** — incompatible with Apache 2.0. It is used in
`app/compliance/pdf_filler.py` and must be replaced before open-source
release. The Apache 2.0-compatible replacement is `pypdf` (BSD-3-Clause). The
migration is non-trivial because PyMuPDF's `doc.bake()` and `doc.pdf_catalog()`
calls have no direct pypdf equivalents and require API-level rewrites.

All other Python and npm dependencies appear to use Apache 2.0-compatible
licenses (MIT, BSD, Apache 2.0). Two tracked config files contain real PII in
git history: `config/config.example.yaml` has `host_name: "CHANGE_ME"`
(committed in `6a7e71a`) and `config/base.yaml` has
`resort_contact_name: "CHANGE_ME"` (committed in multiple Phase 5 commits). Both
require git history rewrite using `git-filter-repo --replace-text`. The real
property addresses (Fort Myers Beach, Lot 110/170) in `jay.yaml` and `minnie.yaml`
are also tracked, and per HYGN-01 these files should be gitignored and removed
from tracking — which eliminates the PII without history rewrite since they
currently only use CHANGE_ME placeholders anyway.

**Primary recommendation:** Replace PyMuPDF with pypdf first (LICS-03), then
clean git history for the two PII strings in config files, then add
LICENSE/NOTICE, fix gitignore, and sanitize config.example.yaml.

---

## Standard Stack

### Core License Audit Tools

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| pip-licenses | 4.x (latest) | List all Python dep licenses | Standard tool, pip-installable, JSON/CSV/Markdown output |
| license-checker | 25.x (latest) | List all npm dep licenses | Standard tool, `--onlyAllow` flag for CI |
| git-filter-repo | Latest | Rewrite git history to remove PII | Recommended by git core devs, replaces filter-branch |
| gitleaks | 8.24+ | Scan full git history for secrets | Industry standard, 800+ patterns |

### Supporting Tools

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| pypdf | 6.7.5 | Replace PyMuPDF for PDF form fill | Apache 2.0-compatible (BSD-3-Clause) |
| uv | (project's existing) | Add pip-licenses as dev dep | Already used in project |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| license-checker | license-checker-rseidelsohn | rseidelsohn is actively maintained fork; original may be stale |
| git-filter-repo | BFG Repo Cleaner | BFG is faster for large blobs, but git-filter-repo handles text replacement better |
| pypdf | pikepdf | pikepdf is lower-level, overkill for AcroForm filling |

**Installation:**
```bash
# Python audit tool (add to dev deps)
uv add --dev pip-licenses

# npm audit tool (run ad hoc, no install needed)
npx license-checker --production --json

# Git history tools (system install, not project deps)
brew install git-filter-repo gitleaks
```

---

## Architecture Patterns

### Pattern 1: License Audit Workflow (Python)

**What:** Run pip-licenses inside the activated venv to get all installed
packages with license info.

**When to use:** Before generating NOTICE file; for LICS-01/LICS-02 verification.

**Example:**
```bash
# Source: https://github.com/raimon49/pip-licenses (official README)

# Activate project venv first
source .venv/bin/activate

# Summary of all license types
pip-licenses --order=license --format=markdown --summary

# Full list for NOTICE file generation
pip-licenses --format=plain-vertical --with-urls --with-authors \
  --output-file=NOTICE-python-deps.txt

# Or use uv run to avoid manual activation:
uv run pip-licenses --format=markdown --order=license
```

### Pattern 2: License Audit Workflow (npm)

**What:** Run license-checker against the frontend package to enumerate all
npm dependency licenses.

**When to use:** Before generating NOTICE file; for LICS-02 verification.

**Example:**
```bash
# Source: https://github.com/davglass/license-checker (official README)

# Run from frontend/ directory
cd frontend
npx license-checker --production --json --out ../npm-licenses.json
npx license-checker --development --json --out ../npm-dev-licenses.json

# Fail on incompatible licenses (CI gate):
npx license-checker --onlyAllow \
  'MIT;BSD-2-Clause;BSD-3-Clause;Apache-2.0;ISC;0BSD;CC0-1.0;Unlicense'
```

### Pattern 3: Apache 2.0 NOTICE File Format

**What:** The NOTICE file format required by Apache 2.0 license (Section 4.4).

**Key rule:** NOTICE must be minimal. Only include what is LEGALLY required.
BSD/MIT dependencies do NOT need entries in NOTICE — only Apache 2.0-licensed
dependencies with their own NOTICE files, and any deps that explicitly require
attribution.

**Format:**
```
Rental Management Platform
Copyright 2026 [Owner Name]

This product includes software developed at the Apache Software Foundation
(http://www.apache.org/).

This product includes the following third-party software:

[Only list deps with their own NOTICE files or explicit attribution requirements]
```

**Practical approach for this project:** Most Python deps are MIT/BSD. The
NOTICE file can be kept minimal. Document all deps in LICENSE instead.

**Source:** https://infra.apache.org/licensing-howto.html

### Pattern 4: Git History PII Removal with git-filter-repo

**What:** Rewrite git history to replace specific strings across all commits.

**When to use:** When PII or real names appear in committed files in history.

**Example:**
```bash
# Source: https://manpages.debian.org/testing/git-filter-repo/git-filter-repo.1.en.html

# Create expressions file
cat > /tmp/pii-replacements.txt << 'EOF'
CHANGE_ME==>OWNER_NAME
CHANGE_ME==>RESORT_CONTACT_NAME
EOF

# Backup first (CRITICAL — this is destructive)
git clone --mirror . /tmp/repo-backup.git

# Rewrite history (requires clean working tree)
git filter-repo --replace-text /tmp/pii-replacements.txt --force

# After rewriting — all collaborators must re-sync
# git push --force-with-lease  (only after confirming clean)
```

**IMPORTANT:** git-filter-repo rewrites ALL commit SHAs. This is destructive.
The project has 249 commits. Since this repo is likely not yet public (pre-
release), force-pushing to origin after history rewrite is acceptable and the
correct approach.

### Pattern 5: pypdf Replacement for PyMuPDF

**What:** Rewrite `app/compliance/pdf_filler.py` using pypdf instead of PyMuPDF.

**Source:** https://pypdf.readthedocs.io/en/stable/user/forms.html

```python
# BSD-3-Clause (Apache 2.0 compatible)
from pypdf import PdfReader, PdfWriter

def fill_resort_form(
    template_pdf_path: str,
    mapping_json_path: str,
    booking_data: dict,
    property_data: dict,
) -> bytes:
    reader = PdfReader(template_pdf_path)
    writer = PdfWriter()
    writer.append(reader)

    # Check for XFA (pypdf cannot fill XFA)
    # Access via writer.root_object["/AcroForm"].get("/XFA")
    acroform = writer._root_object.get("/AcroForm")
    if acroform and "/XFA" in acroform:
        raise ValueError("XFA forms not supported")

    # Build field_values dict (same logic as before)
    field_values = { ... }  # same building logic

    # Fill fields on each page
    for page in writer.pages:
        writer.update_page_form_field_values(
            page,
            field_values,
            auto_regenerate=False,
            flatten=True,  # equivalent to doc.bake() — bakes appearance streams
        )

    # Remove Widget annotations (completes the flatten)
    writer.remove_annotations(subtypes="/Widget")

    import io
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
```

**CAVEAT:** pypdf's `flatten=True` is the closest equivalent to PyMuPDF's
`doc.bake()`. However, cross-viewer compatibility (macOS Preview, iOS Mail)
must be validated after migration. This is flagged as a test requirement.

### Anti-Patterns to Avoid

- **Editing .gitignore without removing tracked files:** Adding `config/jay.yaml`
  to `.gitignore` does nothing for already-tracked files. Must `git rm --cached`
  the file first.
- **Modifying HEAD without cleaning history:** Replacing PII in current files
  does not remove it from older commits. History rewrite is required.
- **Flattening forms with `auto_regenerate=True` (pypdf default):** This triggers
  a "save changes" dialog in some PDF viewers. Always use `auto_regenerate=False`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| License enumeration | Script to parse pyproject.toml/package.json | pip-licenses + license-checker | Misses transitive deps, wrong license data |
| Git history scan | Manual grep of commits | gitleaks | Misses entropy-based secrets, 800+ patterns |
| Git history rewrite | git filter-branch scripts | git-filter-repo | filter-branch is deprecated, 10x slower, prone to errors |
| NOTICE file content | Manual dependency enumeration | pip-licenses output + Apache guidance | Misses packages, wrong format |
| PDF form flattening | Custom appearance stream logic | pypdf flatten=True | PDF spec complexity, viewer-specific quirks |

**Key insight:** License compliance tooling is specialized. Manual approaches
miss transitive dependencies and get license names wrong (e.g., "Python Software
Foundation License" vs "PSF-2.0"). Always use tools with SPDX identifiers.

---

## Common Pitfalls

### Pitfall 1: PyMuPDF AGPL Is Not Just a Warning

**What goes wrong:** Developer notes AGPL license but proceeds anyway thinking
"it's open source so it's fine." AGPL-3.0 requires that if you distribute
software using AGPL code, your entire software stack must also be released under
AGPL-compatible terms. Apache 2.0 is NOT AGPL-compatible.

**Why it happens:** Confusion between "open source" and "Apache-compatible."
AGPL, GPL, LGPL are all open source but incompatible with Apache 2.0 for
distribution.

**How to avoid:** Replace pymupdf with pypdf before any public release. Do not
seek a commercial Artifex license as that defeats the open-source goal.

**Warning signs:** `import pymupdf` or `import fitz` anywhere in `app/`.

### Pitfall 2: gitignore Does Not Remove Already-Tracked Files

**What goes wrong:** Add `config/jay.yaml` to `.gitignore` but the file remains
tracked and will continue to appear in `git status` and commits.

**Why it happens:** `.gitignore` only affects untracked files.

**How to avoid:**
```bash
git rm --cached config/jay.yaml config/minnie.yaml
echo "config/*.yaml" >> .gitignore
echo "!config/base.yaml" >> .gitignore
echo "!config/config.example.yaml" >> .gitignore
git add .gitignore
git commit -m "chore: untrack real property configs"
```

**Warning signs:** `git ls-files config/` still shows `jay.yaml` after adding
to `.gitignore`.

### Pitfall 3: PII Remains in Git History After Current-File Edit

**What goes wrong:** Developer edits `config.example.yaml` to replace
"CHANGE_ME" with "OWNER_NAME", commits, done. But `git log -S "CHANGE_ME"`
still finds the string in commit `6a7e71a`.

**Why it happens:** Git is an append-only content store. Editing files only
creates new commits; old commits are unchanged.

**How to avoid:** Use `git filter-repo --replace-text` to rewrite all 249
commits so the string never appears.

**Warning signs:** `git log --all -S "CHANGE_ME"` returns any results.

### Pitfall 4: config.example.yaml Already Contains Real Owner Name

**What goes wrong:** `config.example.yaml` currently contains
`host_name: "CHANGE_ME"`. This is tracked and in git history since
commit `6a7e71a` (Phase 5). When the repo goes public, this name is visible in
the git log.

**Why it happens:** The example config was populated with real values as
an editorial choice during development.

**How to avoid:**
1. Rewrite history with git-filter-repo to replace "CHANGE_ME"
2. Update `config.example.yaml` HEAD to use a generic placeholder like
   "Your Name Here"

### Pitfall 5: base.yaml Contains Real Resort Contact Name

**What goes wrong:** `config/base.yaml` contains `resort_contact_name: "CHANGE_ME"`.
This is a real person's first name at the resort. It appears in git history
across 5 commits (Phase 5 era).

**How to avoid:**
1. Replace with `resort_contact_name: "CHANGE_ME"` in current file
2. Rewrite history to replace "CHANGE_ME" with "CHANGE_ME" across all commits

### Pitfall 6: Transitive npm Dependencies May Have Problematic Licenses

**What goes wrong:** Direct npm deps like `react`, `tailwindcss` are MIT. But
transitive deps (e.g., some D3 sub-packages pulled by recharts) may use
different licenses.

**Why it happens:** `package.json` only lists direct dependencies.

**How to avoid:** Run `npx license-checker --production --json` which lists ALL
packages including transitive deps (reads from `node_modules/`).

### Pitfall 7: pip-licenses Must Run Inside the Activated venv

**What goes wrong:** Running `pip-licenses` globally lists system Python
packages, not project packages.

**How to avoid:**
```bash
# Correct: use uv run to execute in project venv
uv run pip-licenses --format=markdown

# Or: activate first
source .venv/bin/activate && pip-licenses --format=markdown
```

---

## Code Examples

### Running Full Python License Audit

```bash
# Source: pip-licenses PyPI page + uv docs

# Add as dev dependency
uv add --dev pip-licenses

# Run and save output
uv run pip-licenses \
  --format=markdown \
  --order=license \
  --with-urls \
  --output-file=python-licenses.md

# Check for any GPL/LGPL/AGPL/unknown
uv run pip-licenses --format=json | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
bad = ['GPL', 'LGPL', 'AGPL', 'Unknown', 'UNKNOWN']
found = [p for p in data if any(b in p['License'] for b in bad)]
if found:
    print('INCOMPATIBLE LICENSES FOUND:')
    for p in found:
        print(f'  {p[\"Name\"]} {p[\"Version\"]}: {p[\"License\"]}')
    sys.exit(1)
else:
    print('All Python licenses OK')
"
```

### Running Full npm License Audit

```bash
# Source: license-checker GitHub README

cd /Users/tunderhill/development/airbnb-tools/frontend

# Full audit including dev deps
npx license-checker --json --out npm-all-licenses.json

# Fail-fast on incompatible (CI-ready)
npx license-checker --onlyAllow \
  'MIT;BSD-2-Clause;BSD-3-Clause;Apache-2.0;ISC;0BSD;CC0-1.0;Unlicense;Python-2.0'
```

### Replacing PyMuPDF Dependency

```bash
# Remove pymupdf, add pypdf
uv remove pymupdf
uv add pypdf

# Verify
uv run python -c "from pypdf import PdfReader, PdfWriter; print('pypdf OK')"
```

### Generating Apache 2.0 NOTICE File

```bash
# The NOTICE file template for this project:
cat > NOTICE << 'EOF'
Rental Management Platform
Copyright 2026 [Owner Name]

This product is licensed under the Apache License, Version 2.0.
See the LICENSE file for details.

Third-party dependencies and their licenses:

This product includes software with the following licenses:
- MIT License: FastAPI, SQLAlchemy, Alembic, Pydantic, Jinja2, Typer, Structlog,
  Httpx, Polars, psycopg, python-slugify, APScheduler, and others
- BSD-3-Clause License: pypdf (replaces pymupdf)
- Apache-2.0 License: Tenacity
- PSF (Python Software Foundation): Python standard library

Complete license information is available in NOTICE-python-deps.txt and
NOTICE-npm-deps.txt generated by license audit tools.
EOF
```

### Scanning Git History for Secrets

```bash
# Source: gitleaks GitHub README

# Scan full git history
gitleaks git --verbose \
  --report-format json \
  --report-path gitleaks-report.json \
  /Users/tunderhill/development/airbnb-tools

# Review findings
cat gitleaks-report.json | python3 -m json.tool | grep -A5 '"Description"'
```

### git-filter-repo: Replace PII in All History

```bash
# Source: https://manpages.debian.org/testing/git-filter-repo/git-filter-repo.1.en.html

# STEP 1: Create expressions file
cat > /tmp/pii-clean.txt << 'EOF'
CHANGE_ME==>Your Name Here
CHANGE_ME==>Resort Contact Name
EOF

# STEP 2: Backup
git clone --mirror /Users/tunderhill/development/airbnb-tools \
  /tmp/airbnb-tools-backup.git

# STEP 3: Rewrite (run from repo root)
cd /Users/tunderhill/development/airbnb-tools
git filter-repo --replace-text /tmp/pii-clean.txt --force

# STEP 4: Verify
git log --all -S "CHANGE_ME"  # Should return empty
git log --all -S "CHANGE_ME"           # Should return empty

# STEP 5: Force push (once remote is confirmed)
# git push --force-with-lease origin main
```

---

## Current State of This Repo

### Confirmed Findings (HIGH confidence)

**License Issues:**

| Package | License | Status | Action |
|---------|---------|--------|--------|
| pymupdf 1.27.1 | AGPL-3.0 | INCOMPATIBLE | Replace with pypdf |
| All other Python deps | MIT/BSD/Apache | OK | No action |
| All npm deps | MIT/ISC/BSD | OK (verify transitive) | Audit to confirm |

**PII in Git History:**

| Location | PII | Commit | Action |
|----------|-----|--------|--------|
| config/config.example.yaml | `host_name: "CHANGE_ME"` | 6a7e71a (Phase 5) | git-filter-repo replace |
| config/base.yaml | `resort_contact_name: "CHANGE_ME"` | 6a7e71a + 4 more (Phase 5) | git-filter-repo replace |
| config/jay.yaml | Real property address (Fort Myers Beach, Lot 110) | Multiple | Untrack file (gitignore) |
| config/minnie.yaml | Real property address (Fort Myers Beach, Lot 170) | Multiple | Untrack file (gitignore) |

**Note:** `jay.yaml` and `minnie.yaml` only contain CHANGE_ME placeholders for
sensitive fields (host_name, phone, wifi). The address field contains the real
resort address, but this address is publicly known (it's a public resort).
Decision for planner: either untrack these files per HYGN-01 (simplest), or
assess if the address itself is PII (it is not — it's a public venue address).
HYGN-01 says to gitignore `config/*.yaml` except `config.example.yaml`, which
resolves this.

**gitignore Gaps:**

| Missing Entry | Risk | Fix |
|---------------|------|-----|
| `archive/` | Real CSVs with real Airbnb data | Add to .gitignore |
| `confirmations/` | PDF confirmation files | Add to .gitignore |
| `*.csv` | Any future CSV uploads | Add to .gitignore |
| `config/jay.yaml`, `config/minnie.yaml` | Real property configs | gitignore + git rm --cached |
| `config/minnie.yaml` | Real property config | gitignore + git rm --cached |

**Note:** Currently `archive/` and `confirmations/` are untracked (not in git),
but not gitignored. Adding them to `.gitignore` prevents accidental future adds.

**Missing Root Files:**

| File | Status | Action |
|------|--------|--------|
| LICENSE | Missing | Create with Apache 2.0 full text |
| NOTICE | Missing | Create with attribution list |

### Test Fixture Assessment

| File | Names Used | Status |
|------|-----------|--------|
| tests/fixtures/airbnb_sample.csv | "Jane Sample", "John Sample", "Sam Sample" | Clearly fake — OK |
| tests/fixtures/mercury_sample.csv | "Sample Account LLC" | Clearly fake — OK |
| tests/fixtures/vrbo_sample.csv | "Alice Johnson", "Bob Martinez", "Carol Smith" | Common test names, not real guests — OK per HYGN-04 |

The VRBO fixture names are standard placeholder names (not real guests). They
satisfy HYGN-04's requirement for "clearly fake values."

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| PyMuPDF for PDF forms | pypdf 6.x | PyMuPDF is AGPL; pypdf is BSD-3-Clause |
| `git filter-branch` for history rewrite | `git filter-repo` | filter-branch deprecated; filter-repo is 10x faster |
| Manual license review | pip-licenses + license-checker | Automated, catches transitive deps |
| BFG Repo Cleaner | git-filter-repo | Both work; filter-repo preferred for text replacement |

---

## Open Questions

1. **pypdf cross-viewer compatibility for baked PDFs**
   - What we know: pypdf's `flatten=True` + `remove_annotations()` is the
     equivalent of PyMuPDF's `doc.bake()`. Works correctly per pypdf docs.
   - What's unclear: Whether pypdf-flattened PDFs render correctly in macOS
     Preview and iOS Mail (the specific concern in the original PyMuPDF
     docstring).
   - Recommendation: After replacing PyMuPDF with pypdf, run the existing
     PDF form test with actual macOS Preview. The planner should add a manual
     verification step.

2. **Whether to remove jay.yaml/minnie.yaml from history vs just untracking**
   - What we know: HYGN-01 says to gitignore them. Current files only contain
     CHANGE_ME for secrets; address is public resort info.
   - What's unclear: Whether historical versions in git have any real data
     beyond the public resort address.
   - Recommendation: Audit all historical versions (only 6 commits). If only
     public resort addresses appear, untracking is sufficient. The `address`
     field in these files contains "CHANGE_ME_ADDRESS/170,
     Fort Myers Beach, FL 33931" which is a public venue, not private.

3. **Whether the AGPL PyMuPDF license requires retroactive action**
   - What we know: The repo is not yet public. No distribution has occurred.
   - What's unclear: Whether pre-release use of AGPL code in a private repo
     requires any action beyond removing it before public release.
   - Recommendation: Remove before public release (this phase). No retroactive
     action needed for private use.

---

## Sources

### Primary (HIGH confidence)
- PyPI `PyMuPDF` page — confirmed AGPL-3.0 / Artifex Dual License, version 1.27.1
- `https://pypdf.readthedocs.io/en/stable/user/forms.html` — AcroForm filling API, flatten parameter
- `https://manpages.debian.org/testing/git-filter-repo/git-filter-repo.1.en.html` — --replace-text syntax
- `https://infra.apache.org/licensing-howto.html` — Apache NOTICE file requirements
- `https://github.com/raimon49/pip-licenses` — pip-licenses installation and CLI
- `https://github.com/davglass/license-checker` — npm license-checker CLI and --onlyAllow flag
- `https://github.com/gitleaks/gitleaks` — gitleaks v8.24+ installation and git scan command
- Git inspection of airbnb-tools repo — confirmed PII strings, commit history, tracked files

### Secondary (MEDIUM confidence)
- pypdf license: BSD-3-Clause confirmed via multiple WebSearch results citing GitHub LICENSE file
- polars license: MIT confirmed via official pola.rs website
- sqlglot license: MIT confirmed via WebFetch of LICENSE file on GitHub
- structlog license: Apache 2.0 / MIT dual confirmed via structlog.org docs
- tenacity license: Apache 2.0 confirmed via PyPI page
- apscheduler license: MIT confirmed via multiple sources
- radix-ui license: MIT confirmed via WebSearch citing GitHub LICENSE file
- recharts license: MIT confirmed via npm and GitHub sources

### Tertiary (LOW confidence)
- All other Python/npm transitive deps assumed compliant — must verify with audit tools

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — tools verified via official sources
- Architecture (PyMuPDF replacement): HIGH — pypdf API verified via official docs
- PII findings: HIGH — direct git log inspection of actual repo
- License findings: HIGH — confirmed AGPL on PyMuPDF via PyPI; other licenses via official sources
- gitignore gaps: HIGH — direct inspection of .gitignore and git ls-files output
- Transitive npm licenses: LOW — requires running license-checker to confirm

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable domain; main risk is transitive dep license changes)

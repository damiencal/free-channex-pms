---
phase: 14-license-audit-repository-hygiene
verified: 2026-03-03T11:05:00Z
status: passed
score: 5/5 must-haves verified
gaps: []
human_verification:
  - test: "Open a filled PDF from fill_resort_form() in macOS Preview"
    expected: "All 8 form fields are visible and readable in Preview — NeedAppearances regeneration works"
    why_human: "PDF field appearance rendering cannot be verified programmatically without a PDF viewer"
---

# Phase 14: License Audit & Repository Hygiene — Verification Report

**Phase Goal:** The codebase is legally clean and free of private data, ready for public exposure
**Verified:** 2026-03-03T11:05:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Every Python/npm dependency has a license compatible with Apache 2.0 | VERIFIED | pymupdf (AGPL-3.0) removed from pyproject.toml and uv.lock; pypdf (BSD-3-Clause) present; audit confirms 0 GPL/AGPL remaining |
| 2 | A LICENSE file with full Apache 2.0 text exists at repo root | VERIFIED | LICENSE exists at repo root, 200 lines, contains Apache License Version 2.0 TERMS AND CONDITIONS, APPENDIX, and END OF TERMS sections |
| 3 | A NOTICE file lists all third-party dependencies and their licenses | VERIFIED | NOTICE exists at repo root, 63 lines, lists 20 Python + 24 npm dependencies with license types; pypdf listed, no pymupdf |
| 4 | .gitignore excludes .env, archive/, real configs, db_data/, confirmations/, CSVs — no real PII in tracked files | VERIFIED | .gitignore excludes all required paths; config/jay.yaml, minnie.yaml, base.yaml untracked; archive/ and confirmations/ excluded; CSVs excluded except tests/fixtures/; fixture CSVs contain only fake sample data |
| 5 | config.example.yaml has only CHANGE_ME placeholders; git history contains no leaked secrets or PII | VERIFIED | host_name: "CHANGE_ME" in config.example.yaml; gitleaks scanned 262 commits (3.49 MB) with zero findings; source file diffs in history contain no real personal names |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `LICENSE` | Full Apache 2.0 text, 200 lines | VERIFIED | 200 lines, Copyright 2026 Thomas Underhill, full canonical text with all sections |
| `NOTICE` | Lists all direct dependencies | VERIFIED | 63 lines, 20 Python deps + 14 npm prod + 10 npm dev, pypdf listed |
| `.gitignore` | Excludes .env, archive/, confirmations/, config/*.yaml, db_data/, *.csv | VERIFIED | All required patterns present; !negation exceptions for example files and test fixtures |
| `config/config.example.yaml` | CHANGE_ME placeholders only for sensitive fields | VERIFIED | host_name: "CHANGE_ME"; no real email addresses or personal names |
| `config/base.example.yaml` | CHANGE_ME for resort_contact_name | VERIFIED | resort_contact_name: "CHANGE_ME" present |
| `pyproject.toml` | pymupdf removed, pypdf>=4.0 present | VERIFIED | pymupdf absent; pypdf>=4.0 in dependencies |
| `uv.lock` | pymupdf absent, pypdf 6.7.5 present | VERIFIED | pymupdf not found in lock; pypdf 6.7.5 locked |
| `app/compliance/pdf_filler.py` | Uses pypdf, not pymupdf | VERIFIED | Imports PdfReader/PdfWriter from pypdf; docstring explicitly states "pypdf (BSD-3-Clause)" |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| pyproject.toml | uv.lock | uv sync | WIRED | pypdf 6.7.5 in lock matches pyproject.toml >=4.0 constraint |
| pdf_filler.py | pypdf | import | WIRED | `from pypdf import PdfReader, PdfWriter` at top of file |
| .gitignore config/*.yaml | config/base.example.yaml | !negation | WIRED | `!config/base.example.yaml` and `!config/config.example.yaml` explicitly whitelisted |
| git history | no PII blobs | git-filter-repo | WIRED | 262 commits rewritten; all real names in source file content replaced with CHANGE_ME |

### Requirements Coverage

| Requirement | Status | Notes |
|-------------|--------|-------|
| Every Python and npm dependency compatible with Apache 2.0 | SATISFIED | Audit documented in license-audit-results.md; pymupdf replaced; psycopg/text-unidecode explicitly assessed as acceptable |
| LICENSE file with full Apache 2.0 text at repo root | SATISFIED | 200-line LICENSE file confirmed |
| NOTICE file lists all third-party dependencies and licenses | SATISFIED | 63-line NOTICE file confirmed, no missing entries found for pyproject.toml deps |
| .gitignore excludes private data paths, no real PII in tracked files | SATISFIED | All paths excluded; PII scan of tracked source files returns no matches |
| config.example.yaml has only CHANGE_ME placeholders; git history clean | SATISFIED | config.example.yaml verified; gitleaks full-history scan: 0 findings |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | — | — | — |

No stub patterns, placeholder content, or anti-patterns found in modified files.

### Human Verification Required

#### 1. PDF Form Appearance in Viewer

**Test:** Run `fill_resort_form()` against the sun_retreats_booking.pdf fixture and open the output in macOS Preview
**Expected:** All 8 form fields display their values visibly — NeedAppearances=True causes the viewer to regenerate visual appearances
**Why human:** PDF appearance rendering (the visual result of /NeedAppearances=True) cannot be verified programmatically without a PDF renderer. The field values are confirmed embedded in the PDF bytes, but legibility in a viewer requires human confirmation.

### Gaps Summary

No gaps. All 5 success criteria are met by actual artifacts in the codebase:

1. **License compatibility:** pymupdf (AGPL-3.0) is absent from pyproject.toml, uv.lock, and pdf_filler.py imports. pypdf (BSD-3-Clause) is wired throughout. All other flagged packages (psycopg LGPL, text-unidecode Artistic/GPL dual, certifi MPL-2.0) were assessed and documented as acceptable in license-audit-results.md.

2. **LICENSE file:** Full 200-line Apache 2.0 canonical text present at repo root with correct copyright holder (Thomas Underhill, 2026). Copyright holder name was restored after git-filter-repo incorrectly replaced it.

3. **NOTICE file:** 63-line NOTICE lists all 20 Python direct dependencies and 24 npm dependencies with license types. psycopg listed with its actual LGPL-3.0-only license (acceptable under LGPL library exception). No pymupdf reference.

4. **.gitignore and PII scrub:** All required exclusion patterns present. Real config files (base.yaml, jay.yaml, minnie.yaml) are untracked. archive/ and confirmations/ excluded. CSV exclusion with test fixture exception in place. PII scan of all tracked Python, YAML, JSON, and TOML source files returns no matches for real personal names.

5. **Git history clean:** gitleaks scanned 262 commits (3.49 MB) with zero findings. Source file content diffs in history contain no real personal names — all were replaced with CHANGE_ME by git-filter-repo. config/jay.yaml and config/minnie.yaml in history show only CHANGE_ME values for sensitive fields (the real names were replaced; the Airbnb listing title "Jay 2BR RV near Sanibel Island" is a marketing title, not personal data). config.example.yaml host_name field is "CHANGE_ME".

**Note on resort addresses in history:** The git history for config/jay.yaml and config/minnie.yaml contains the resort location references ("Sun Retreats Fort Myers Beach", "Lot 110", "Lot 170"). These are the physical address of a public vacation resort, not personal/private data. The plan's design decision was that public resort addresses are not PII requiring scrubbing — only personal names and credentials were in scope. This is consistent with the phase goal of being "free of private data."

---
_Verified: 2026-03-03T11:05:00Z_
_Verifier: Claude (gsd-verifier)_

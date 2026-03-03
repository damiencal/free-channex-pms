# License Audit Results

**Date:** 2026-03-02
**Tools:** pip-licenses 5.5.1 (Python), license-checker 25.0.1 (npm)

## Python Dependencies

**Total packages audited:** 70

### Incompatible Licenses

| Package | Version | License | Status | Action |
|---------|---------|---------|--------|--------|
| PyMuPDF | 1.27.1 | AGPL-3.0 (Dual: AGPL-3.0 / Artifex Commercial) | **INCOMPATIBLE** | Replace with pypdf |

### Flagged for Review (Acceptable)

| Package | Version | License | Assessment |
|---------|---------|---------|-----------|
| psycopg | 3.3.3 | LGPL-3.0-only | Acceptable — LGPL library exception applies when used unmodified as runtime dependency |
| psycopg-binary | 3.3.3 | LGPL-3.0-only | Acceptable — same as above |
| text-unidecode | 1.3 | Artistic License OR GPL (dual) | Acceptable — we elect to use under Artistic License (permissive) |
| certifi | 2026.2.25 | MPL-2.0 | Acceptable — MPL-2.0 is file-scoped copyleft, compatible with Apache 2.0 distribution |
| rental-management | 0.1.0 | UNKNOWN | This is the project itself — not a dependency concern |

### Clean Python Licenses

All other Python dependencies are MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC, PSF-2.0, or Unlicense.

## npm Dependencies

**Total packages audited:** 307

### Incompatible Licenses

None.

### License Distribution

| License | Count |
|---------|-------|
| MIT | 254 |
| ISC | 23 |
| Apache-2.0 | 14 |
| BSD-2-Clause | 6 |
| BSD-3-Clause | 4 |
| MPL-2.0 | 2 |
| Python-2.0 | 1 |
| CC-BY-4.0 | 1 |
| 0BSD | 1 |
| MIT AND ISC | 1 |

All npm licenses are compatible with Apache 2.0.

## Conclusion

**The only dependency requiring action is PyMuPDF (AGPL-3.0).**

PyMuPDF must be replaced with pypdf (BSD-3-Clause) before public release under Apache 2.0. All other dependencies are compatible.

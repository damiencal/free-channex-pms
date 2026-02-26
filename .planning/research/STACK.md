# Stack Research

**Domain:** Self-hosted vacation rental management suite (bookkeeping, PDF forms, multi-platform ingestion, LLM interface)
**Researched:** 2026-02-26
**Confidence:** HIGH (core stack verified via PyPI/official docs), MEDIUM (some supporting libraries), LOW (noted inline)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12+ | Runtime | Wide library support, async maturity, required by most libraries in this stack; 3.12 is current stable with best performance |
| FastAPI | 0.133.1 | Web framework + REST API | Async-native, auto-generates OpenAPI docs, integrates with Pydantic for config/validation, natural fit for LLM streaming; 40% YoY adoption growth in 2025 |
| Uvicorn | 0.41.0 | ASGI server | FastAPI's own recommendation; production-grade, handles async properly; run behind a reverse proxy in Docker |
| SQLAlchemy | 2.0.47 | ORM + query builder | Async-native in 2.x via `AsyncSession`; supports both SQLite (development/small) and PostgreSQL (if you scale); Alembic for migrations is first-class |
| Alembic | 1.18.4 | Database migrations | Part of the SQLAlchemy org; handles schema evolution without manual SQL; pairs perfectly with SQLAlchemy 2.x |
| SQLite (via aiosqlite) | aiosqlite 0.22.1 | Primary database | For a single-host, self-hosted, 2-property tool with one concurrent user, SQLite is the right call — no daemon, no network stack, no Docker dependency chain; aiosqlite provides async bridge |
| Pydantic | 2.12.5 | Data validation + schemas | FastAPI depends on it; also used for request/response models and typed settings |
| pydantic-settings | 2.13.1 | Config-driven settings | Reads from `.env` files, environment variables, YAML or TOML; critical for the "no hardcoded property data" requirement; supports multi-source merge |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ollama (Python) | 0.6.1 | Ollama LLM integration | Direct, official client for local Ollama; use for chat completions and streaming against the local Ollama server; no intermediate layer needed |
| polars | 1.38.1 | CSV ingestion + data wrangling | Airbnb, VRBO, RVshare, Mercury bank all export CSVs; Polars is 5-25x faster than pandas, uses 87% less memory, and handles messy exports well; use for the ingest pipeline |
| pandas | 3.0.1 | Fallback/compatibility | Polars interops with pandas; keep as a dependency for any libraries that expect pandas DataFrames; do not use as primary CSV tool |
| pypdf | 6.7.3 | PDF form filling (AcroForm) | Fills existing PDF AcroForms programmatically; use for resort compliance forms; supports `update_page_form_field_values()` and form flattening |
| pikepdf | 10.3.0 | PDF low-level manipulation | Use when pypdf is insufficient — merging overlays, handling non-standard PDFs; pairs with pypdf |
| fastapi-mail | 1.6.2 | Email sending | FastAPI-native email library built on aiosmtplib; supports templates, attachments, background sending; self-hosted SMTP (e.g., local Postfix or any external SMTP) |
| APScheduler | 3.11.2 | Task scheduling | Cron-style periodic tasks (nightly CSV ingests, report generation, calendar syncs); no external broker required; runs in-process; do NOT use 4.0.0 alpha |
| icalendar | 7.0.2 | iCal/ICS calendar parsing | Airbnb, VRBO, RVshare all expose iCal feeds for availability sync; parse and merge calendars without a broker |
| httpx | 0.28.1 | Async HTTP client | Mercury Bank REST API calls, platform API polling, webhook delivery; FastAPI's own test client also uses httpx; prefer over `requests` for async compatibility |
| aiosqlite | 0.22.1 | Async SQLite driver | Required for SQLAlchemy async with SQLite backend; transparent async bridge |

### Frontend / Dashboard

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| React | 18.x | Dashboard UI | Largest ecosystem, best Recharts integration, deep shadcn/ui component library support; justified for a financial dashboard with charts and tables |
| Vite | 6.x | Build tooling | Fastest dev server, minimal config, pairs with React for self-hosted SPA |
| shadcn/ui | current | Component library | Open-source, Tailwind-based, production-quality admin dashboard components; no licensing costs; works well with financial dashboards |
| Recharts | 2.x | Charts | Built into shadcn/ui chart primitives; declarative, React-native; used by most shadcn admin dashboard templates |
| TanStack Query | 5.x | Data fetching | Server state management for FastAPI REST calls; handles caching and background refresh for dashboard widgets |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Docker + Docker Compose | Containerization | Single `docker compose up` for the entire stack; one service for FastAPI+Uvicorn, one for the React SPA served via Nginx; Ollama runs outside the compose stack (pre-existing local install) |
| uv | Python package manager | Dramatically faster than pip; replacing pip/venv in modern Python projects; supports lockfiles; use for reproducible installs |
| Alembic | Schema migrations | Run migrations as a Docker entrypoint step before app start using `alembic upgrade head` |
| pytest + pytest-asyncio | Testing | Async-aware test runner; use `httpx.AsyncClient` for FastAPI endpoint tests |
| Ruff | Linting + formatting | Replaces flake8 + black + isort; extremely fast; single tool for code quality |

---

## Installation

```bash
# Core dependencies (requirements.txt / pyproject.toml)
fastapi==0.133.1
uvicorn[standard]==0.41.0
sqlalchemy==2.0.47
alembic==1.18.4
aiosqlite==0.22.1
pydantic==2.12.5
pydantic-settings==2.13.1

# Integrations
ollama==0.6.1
polars==1.38.1
pypdf==6.7.3
pikepdf==10.3.0
fastapi-mail==1.6.2
apscheduler==3.11.2
icalendar==7.0.2
httpx==0.28.1

# Dev dependencies
pytest
pytest-asyncio
ruff

# Install with uv
uv pip install -r requirements.txt
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FastAPI | Django | If you need Django Admin, a built-in ORM with batteries-included, or a team more familiar with Django patterns. Not recommended here: async story is worse, and the admin UI would be replaced by the React dashboard anyway. |
| FastAPI | Flask | Flask is simpler but lacks native async, auto-docs, and Pydantic integration. Only choose Flask for a trivial 1-route tool — not for this scope. |
| SQLite + aiosqlite | PostgreSQL | PostgreSQL if concurrent access from multiple users or machines is expected, or if analytics queries get complex. For a single-user, single-host self-hosted tool, SQLite is correct and simpler. |
| SQLAlchemy | Tortoise ORM | Tortoise is asyncio-first and simpler, but smaller ecosystem, fewer migration tools, and less battle-tested. SQLAlchemy 2.x async is now mature. |
| Polars | pandas | Use pandas if a dependency requires it or for small one-off scripts. Polars is the primary ingest tool. |
| pypdf | pdfrw | pdfrw works but is older and less maintained. pypdf (the successor to PyPDF2) is the current standard. |
| APScheduler 3.x | Celery | Celery requires a message broker (Redis or RabbitMQ), adding Docker complexity for a single-host deployment. APScheduler runs in-process with no external dependencies. Revisit if tasks become distributed. |
| APScheduler 3.x | APScheduler 4.0a | 4.0 is alpha as of April 2025 — not production ready. Stick with 3.11.2 stable. |
| ollama Python client | LangChain | LangChain adds significant complexity and abstraction for a use case that is primarily "send prompt, get response." Use the official ollama client directly; add LangChain only if building multi-step agent chains. |
| ollama Python client | LlamaIndex | Same argument as LangChain — justified only for RAG pipelines over large document sets. Out of scope for initial version. |
| fastapi-mail | direct smtplib | fastapi-mail handles async, templates, and attachments cleanly. Raw smtplib is synchronous and would block the event loop. |
| React + Vite | Next.js | Next.js SSR is unnecessary for a self-hosted, local-network admin dashboard. Vite SPA is faster to develop and simpler to containerize. |
| React + Vite | Svelte/SvelteKit | Svelte is excellent and smaller bundle, but React has a larger ecosystem and shadcn/ui (the recommended component library) is React-native. |
| icalendar | ics.py | Both work; icalendar 7.x is more actively maintained (8 maintainers, 7.0.2 released Feb 2026) and has broader RFC 5545 compliance. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| PyPDF2 | Deprecated; merged into `pypdf`; no longer maintained as a separate package | `pypdf` 6.7.3 |
| APScheduler 4.0.0a* | Alpha software, API-breaking changes still landing, not production-safe | APScheduler 3.11.2 |
| `requests` (sync) | Blocks the async event loop in FastAPI; causes performance degradation and potential deadlocks | `httpx` with `AsyncClient` |
| LangChain (for simple Ollama queries) | Heavyweight abstraction adds 20+ transitive dependencies and version conflicts for what is a single `ollama.chat()` call | `ollama` Python client directly |
| Flask | Synchronous by default, lacks native Pydantic integration, no auto-docs; wrong choice for a greenfield async project | FastAPI |
| Django | Overkill for an API backend where the admin UI is a custom React dashboard; async maturity still behind FastAPI | FastAPI |
| python-accounting | Only one release (1.0.0, "Initial Release"), appears dormant based on GitHub activity; 5 open issues, 1 stale PR | Implement double-entry bookkeeping directly in SQLAlchemy models (see Architecture section) |
| Celery + Redis/RabbitMQ | Adds two extra Docker services (broker + worker) for a single-host deployment; APScheduler in-process is simpler | APScheduler 3.11.2 |
| pdfrw | Less maintained than pypdf; quirky API for AcroForm field updates requires manual NeedAppearances flag manipulation | pypdf 6.7.3 + pikepdf for edge cases |

---

## Stack Patterns by Variant

**If Mercury Bank API access is available (preferred):**
- Use `httpx.AsyncClient` to poll Mercury's REST API for transaction history
- Mercury provides full account + transaction endpoints; no CSV parsing needed for banking data
- Implement with a nightly APScheduler job calling `GET /account/{id}/transactions`

**If Mercury Bank API is unavailable or rate-limited:**
- Fall back to CSV export ingestion (Mercury exports standard bank CSVs)
- Use Polars to parse and normalize CSV to the internal transaction schema

**For Airbnb / VRBO / RVshare data ingestion (no official public API for small hosts):**
- Primary path: Parse platform CSV exports (Airbnb provides booking history CSVs; VRBO similar)
- Secondary path: Parse iCal feeds via `icalendar` for availability/booking sync
- Do NOT attempt to scrape Airbnb/VRBO — terms of service violation; CSV exports are the sanctioned method

**For the Ollama LLM interface:**
- Use streaming responses (`stream=True` in `ollama.chat()`) for natural language queries
- Expose via a FastAPI WebSocket or SSE endpoint for real-time token streaming in the dashboard
- Use JSON mode for any structured queries that need to update or filter the database

**If PDF form structure is complex (non-AcroForm, XFA-based):**
- XFA forms are not supported by pypdf or pdfrw
- If resort compliance forms are XFA: investigate converting to AcroForm, or use a WKHTMLTOPDF/Playwright approach to generate fresh PDFs from HTML templates instead of filling existing forms
- Flag this for investigation before building the PDF pipeline

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| FastAPI 0.133.1 | Pydantic 2.x required | FastAPI dropped Pydantic v1 support; ensure all models use Pydantic v2 syntax |
| SQLAlchemy 2.0.x | aiosqlite 0.22.x | `asyncio` dialect: `sqlite+aiosqlite://` connection string |
| APScheduler 3.11.2 | Python 3.12 | Stable; no known incompatibilities with Python 3.12 |
| ollama 0.6.1 | Ollama server any recent version | Client is thin wrapper; API is stable; keep both updated together |
| pypdf 6.7.3 | Python 3.10+ | Pure Python; no binary dependencies |
| pikepdf 10.3.0 | Python 3.9+ | Requires libqpdf C library (included in wheels); works in Docker/Linux |
| icalendar 7.0.2 | Python 3.10+ | Updated to 7.x in Feb 2026; breaking changes from 6.x; use 7.x fresh |
| pandas 3.0.1 | Python 3.11+ | pandas 3.x dropped Python 3.10 support; pin Python 3.11+ in Docker image |
| polars 1.38.1 | Python 3.9+ | No numpy dependency by default; very lightweight |

---

## Sources

- FastAPI official site — version 0.133.1 confirmed via PyPI (Feb 25, 2026)
- Uvicorn PyPI — version 0.41.0 (Feb 16, 2026)
- SQLAlchemy PyPI — version 2.0.47 (Feb 24, 2026)
- Alembic PyPI — version 1.18.4 (Feb 10, 2026)
- Pydantic PyPI — version 2.12.5 (Nov 26, 2025)
- pydantic-settings PyPI — version 2.13.1 (Feb 19, 2026)
- ollama PyPI — version 0.6.1 (Nov 13, 2025); GitHub: github.com/ollama/ollama-python
- polars PyPI — version 1.38.1 (Feb 6, 2026)
- pandas PyPI — version 3.0.1 (Feb 17, 2026)
- pypdf official docs (readthedocs.io/en/stable) — version 6.7.3 confirmed
- pikepdf PyPI — version 10.3.0 (Jan 30, 2026)
- fastapi-mail PyPI — version 1.6.2 (Feb 17, 2026)
- APScheduler PyPI — version 3.11.2 stable (Dec 22, 2025); 4.0.0a6 pre-release only
- icalendar PyPI — version 7.0.2 (Feb 24, 2026)
- httpx PyPI — version 0.28.1 stable (Dec 6, 2024); 1.0.dev3 pre-release
- aiosqlite PyPI — version 0.22.1 (Dec 23, 2025)
- Mercury Bank API docs — docs.mercury.com; REST API with accounts + transactions endpoints confirmed
- python-accounting GitHub — single 1.0.0 release, dormant; NOT recommended
- WebSearch: "FastAPI vs Django vs Flask 2026" — multiple sources converge on FastAPI for async API development
- WebSearch: "Polars vs Pandas CSV 2025" — performance benchmarks confirm Polars 5-25x faster for CSV ingest
- WebSearch: "APScheduler vs Celery self-hosted 2025" — consensus: APScheduler for single-host, no-broker setups
- WebSearch: "React vs Svelte dashboard 2025 FastAPI" — React recommended for shadcn/ui ecosystem fit

---
*Stack research for: Self-hosted vacation rental management suite*
*Researched: 2026-02-26*

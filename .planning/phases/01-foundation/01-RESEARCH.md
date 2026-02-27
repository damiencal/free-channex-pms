# Phase 1: Foundation - Research

**Researched:** 2026-02-27
**Domain:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic Settings + Docker Compose + Python tooling
**Confidence:** HIGH

## Summary

Phase 1 establishes the entire stack: Docker deployment, config-driven startup, database with migrations, and a FastAPI skeleton with health check. The research covered five technical domains — package management (uv), web framework (FastAPI), database ORM (SQLAlchemy 2.0 + Alembic), configuration (pydantic-settings with YAML), and CLI tooling (Typer + Questionary).

The Python ecosystem has consolidated around uv as the modern package manager, SQLAlchemy 2.0's Mapped[] declarative style as the ORM pattern, and psycopg3 (sync) as the PostgreSQL driver. FastAPI's official docs now explicitly deprecate tiangolo/uvicorn-gunicorn-fastapi base images; build from official Python slim instead. Pydantic-settings 2.x has native YamlConfigSettingsSource support, enabling the config/base.yaml + per-property YAML pattern without a custom loader.

The property identifier design recommendation is: use a **slug** (string, e.g. "jay", "minnie") as the human-readable business key with a separate auto-increment internal integer PK. UUID primary keys add complexity without benefit at this scale and make config files harder to read. Jinja2 3.x is the correct template engine — it has a FileSystemLoader that maps naturally to the templates/default/ and templates/{property}/ override pattern, and its compile_templates() method enables startup validation.

**Primary recommendation:** Use uv + pyproject.toml for dependency management, FastAPI 0.133 + SQLAlchemy 2.0 (sync, psycopg3 driver) + Alembic 1.18 + pydantic-settings 2.13 (YamlConfigSettingsSource) + Jinja2 3.1 + Typer 0.24 + Questionary 2.1. Run Alembic migrations via Docker Compose command (not in lifespan) to avoid async complexity.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.133.1 | Web framework, health endpoint | ASGI, automatic OpenAPI, Pydantic-native; official Python recommendation |
| uvicorn | 0.41.0 | ASGI server | FastAPI's official runtime; required `python:3.12-slim` base |
| SQLAlchemy | 2.0.47 | ORM + core SQL | Industry standard; 2.0 adds typed Mapped[] style |
| Alembic | 1.18.4 | Database migrations | SQLAlchemy-native; autogenerate detects model changes |
| pydantic-settings | 2.13.1 | Config schema + .env loading | Built on Pydantic v2; YamlConfigSettingsSource for YAML |
| Jinja2 | 3.1.6 | Email/message templates | FastAPI dependency; FileSystemLoader for directory-based templates |
| Typer | 0.24.1 | CLI (`python manage.py setup`) | Based on Click + Rich; supports subcommands and prompts |
| Questionary | 2.1.1 | Interactive wizard prompts | Wraps prompt_toolkit; 8 prompt types including select, confirm, text |
| structlog | 25.5.0 | Structured startup logging | JSON-native; single config for FastAPI + uvicorn log unification |
| httpx | 0.28.1 | Ollama health check HTTP calls | Async-capable; used by FastAPI test client too |
| psycopg3 (psycopg) | 3.3.3 | PostgreSQL driver | New projects should start with psycopg3; psycopg2 receives no new features |
| PyYAML | 6.x | YAML parsing (config files) | Standard Python YAML library; required by pydantic-settings YAML extra |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-slugify | 8.0.4 | Generate property slugs from names | During CLI wizard when user types property name |
| python-dotenv | 1.x | .env loading fallback | pydantic-settings handles this, but useful for standalone scripts |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| psycopg3 | asyncpg | asyncpg is async-only; psycopg3 supports both sync and async — simpler for Phase 1 sync code |
| psycopg3 | psycopg2-binary | psycopg2 receives no new features; psycopg3 is forward-compatible |
| Typer + Questionary | Click + InquirerPy | Typer's type-hint approach reduces boilerplate; both are equally valid |
| structlog | Python stdlib logging | stdlib is fine; structlog adds request-scoped context binding at zero cost |
| Slug string PK | UUID PK | UUID adds complexity; slug-as-business-key + integer PK is simpler and SQL-friendly |
| slug + int PK | slug-only PK | Integer PK enables fast FK joins; slug is the user-facing identity |

**Installation:**
```bash
uv add fastapi[standard] sqlalchemy alembic "pydantic-settings[yaml]" jinja2 typer questionary structlog httpx "psycopg[binary]" python-slugify
uv add --dev pytest pytest-asyncio httpx
```

## Architecture Patterns

### Recommended Project Structure

```
airbnb-tools/
├── pyproject.toml           # uv-managed dependencies
├── uv.lock                  # locked dependency tree
├── Dockerfile               # python:3.12-slim, uv sync, uvicorn CMD
├── docker-compose.yml       # postgres + app services, named volumes
├── .env.example             # DB_URL, SECRET_KEY etc. (no actual secrets)
├── .env                     # gitignored real secrets
├── config/
│   ├── base.yaml            # system-wide defaults (email, resort contacts)
│   ├── config.example.yaml  # documented example for new deployments
│   ├── jay.yaml             # property-specific config (slug: jay)
│   └── minnie.yaml          # property-specific config (slug: minnie)
├── templates/
│   ├── default/
│   │   ├── welcome.txt      # default email templates
│   │   └── pre_arrival.txt
│   └── jay/
│       └── welcome.txt      # per-property template override
├── pdf_mappings/
│   └── sun_retreats_form.json  # PDF field mapping (Phase 5)
├── alembic/
│   ├── alembic.ini
│   ├── env.py               # connects to DB, imports Base metadata
│   └── versions/
│       └── 001_initial.py   # Phase 1 migration: properties table
├── app/
│   ├── main.py              # FastAPI app, lifespan, routes
│   ├── config.py            # AppConfig + PropertyConfig pydantic-settings classes
│   ├── db.py                # Engine, SessionLocal, Base = DeclarativeBase()
│   ├── models/
│   │   ├── __init__.py
│   │   └── property.py      # Property ORM model
│   └── api/
│       ├── __init__.py
│       └── health.py        # GET /health endpoint
└── manage.py                # Typer CLI entry point (python manage.py setup)
```

### Pattern 1: Pydantic Settings with YAML + .env Priority Stack

**What:** Config loads from multiple sources with explicit priority: env vars > .env file > property YAML > base YAML. Secrets (DB_URL, API keys) come from .env only. Everything else from YAML.

**When to use:** Always — this is the entire config subsystem.

```python
# Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from pathlib import Path

class PropertyConfig(BaseModel):
    slug: str                  # "jay" — used as business key and folder name
    display_name: str          # "Jay's Cabin"
    lock_code: str
    resort_contact_email: str

class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file="config/base.yaml",
    )

    # Secrets come from .env
    database_url: str

    # Structure comes from YAML
    properties: list[PropertyConfig] = []

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Priority: env > .env > YAML
        return (env_settings, dotenv_settings, YamlConfigSettingsSource(settings_cls))
```

The per-property YAML pattern requires loading each `config/{slug}.yaml` separately and merging into `AppConfig.properties`. This must be done in a startup function, not in the Settings class itself, since the list of slugs is dynamic.

### Pattern 2: Per-Property Config Loading

**What:** Discover all `config/*.yaml` (excluding `base.yaml`), parse each as `PropertyConfig`, validate all, then merge into the app config.

**When to use:** During startup — before the FastAPI app accepts requests.

```python
# Fail-fast config loader pattern
import yaml
from pathlib import Path

def load_all_properties(config_dir: Path) -> list[PropertyConfig]:
    errors = []
    properties = []
    for yaml_file in sorted(config_dir.glob("*.yaml")):
        if yaml_file.name == "base.yaml":
            continue
        try:
            data = yaml.safe_load(yaml_file.read_text())
            prop = PropertyConfig(**data)
            properties.append(prop)
        except Exception as e:
            errors.append(f"{yaml_file}: {e}")
    if errors:
        raise SystemExit("Config validation failed:\n" + "\n".join(errors))
    return properties
```

### Pattern 3: SQLAlchemy 2.0 Declarative Models with Mapped[]

**What:** Modern SQLAlchemy 2.0 style using DeclarativeBase + Mapped[] type annotations. Column constraints derived from type annotations.

**When to use:** All ORM models in the project.

```python
# Source: https://docs.sqlalchemy.org/en/20/orm/declarative_mapping.html
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        onupdate=datetime.utcnow
    )
```

### Pattern 4: Alembic Migrations via Docker Compose Command (Not Lifespan)

**What:** Run `alembic upgrade head` as the Docker Compose command before starting uvicorn. This avoids async complexity and keeps migrations out of the app server.

**When to use:** Always — do not run migrations inside FastAPI lifespan.

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config        # mount config directory
      - ./templates:/app/templates  # mount templates directory
    depends_on:
      db:
        condition: service_healthy

volumes:
  db_data:
```

### Pattern 5: FastAPI Lifespan for Startup Checks (Not Migrations)

**What:** Use lifespan context manager for startup validation: config loading, template validation, Ollama check, verbose status logging.

```python
# Source: FastAPI docs - lifespan events
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx
import structlog

log = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    config = load_app_config()          # fail-fast on invalid config
    log.info("Config loaded", properties=len(config.properties))

    validate_templates(config)          # fail-fast on bad template vars
    log.info("Templates validated")

    # DB check (non-fatal info logging)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("Database connected", status="ok")
    except Exception as e:
        log.error("Database connection failed", error=str(e))
        raise  # fatal — migrations must have run first

    # Ollama check (non-fatal — system starts with Ollama unavailable)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://localhost:11434/")
        ollama_status = "ok" if resp.status_code == 200 else "unavailable"
    except Exception:
        ollama_status = "unavailable"
    log.info("Ollama", status=ollama_status)

    yield  # app is running

    # --- Shutdown ---
    log.info("Shutting down")

app = FastAPI(lifespan=lifespan)
```

### Pattern 6: Jinja2 Template Override Resolution

**What:** Load templates from default/ first, then overlay per-property templates. Validate all templates render with sample data on startup.

```python
# Source: https://jinja.palletsprojects.com/en/3.1.x/api/
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

def build_template_env(property_slug: str, templates_dir: Path) -> Environment:
    """Priority: templates/{slug}/ overrides templates/default/"""
    loaders = []
    property_dir = templates_dir / property_slug
    if property_dir.exists():
        loaders.append(str(property_dir))
    loaders.append(str(templates_dir / "default"))
    return Environment(loader=FileSystemLoader(loaders))

SAMPLE_DATA = {
    "guest_name": "Test Guest",
    "property_name": "Test Property",
    "checkin_date": "2026-03-01",
    "checkout_date": "2026-03-05",
    "lock_code": "1234",
}

def validate_templates(property_slug: str, templates_dir: Path) -> None:
    env = build_template_env(property_slug, templates_dir)
    errors = []
    for template_name in ["welcome.txt", "pre_arrival.txt"]:
        try:
            template = env.get_template(template_name)
            template.render(**SAMPLE_DATA)  # catches undefined variable errors
        except Exception as e:
            errors.append(f"templates/{template_name}: {e}")
    if errors:
        raise SystemExit("Template validation failed:\n" + "\n".join(errors))
```

### Pattern 7: Typer + Questionary CLI Wizard

**What:** `python manage.py setup` runs an interactive wizard that collects property information, generates config YAML, and upserts the property into the database.

```python
# manage.py
import typer
import questionary
import yaml
from pathlib import Path
from slugify import slugify

app = typer.Typer()

@app.command()
def setup():
    """Interactive setup wizard — create a new property configuration."""
    typer.echo("Rental Management Setup Wizard")

    display_name = questionary.text("Property display name (e.g. 'Jay's Cabin'):").ask()
    slug = questionary.text(
        "Property slug (short identifier, e.g. 'jay'):",
        default=slugify(display_name)
    ).ask()
    lock_code = questionary.password("Door lock code:").ask()
    resort_email = questionary.text("Resort contact email:").ask()

    config = {
        "slug": slug,
        "display_name": display_name,
        "lock_code": lock_code,
        "resort_contact_email": resort_email,
    }

    config_path = Path("config") / f"{slug}.yaml"
    config_path.write_text(yaml.dump(config, default_flow_style=False))
    typer.echo(f"Written: {config_path}")
    typer.echo("Restart the container for the new property to take effect.")

if __name__ == "__main__":
    app()
```

### Anti-Patterns to Avoid

- **Running `alembic upgrade head` inside FastAPI lifespan:** Causes async complexity — Alembic's env.py runs synchronously; running it from async lifespan requires thread executors. Run it in the Docker Compose command before uvicorn starts.
- **Using `@app.on_event("startup")`:** Deprecated by FastAPI. Use `lifespan` parameter on FastAPI constructor instead.
- **Storing secrets in YAML config files:** Secrets (DB password, API keys, SMTP credentials) go in `.env` only. YAML files are for configuration, not secrets.
- **Hardcoding property slugs in source code:** The slug comes from config at runtime. Never import `"jay"` or `"minnie"` as string literals in application code.
- **Checking for Ollama in Alembic env.py:** env.py runs during migrations (before the app starts). Ollama check belongs in FastAPI lifespan only.
- **Using `tiangolo/uvicorn-gunicorn-fastapi` base image:** Officially deprecated. Build from `python:3.12-slim` directly.
- **Storing templates inline in YAML:** Templates as separate `.txt`/`.md` files (the decision is locked). Do not embed template content as multiline YAML strings.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config validation with error messages | Custom dict validator | pydantic-settings + Pydantic models | Automatic field-level error messages, type coercion, required/optional handling |
| Template variable typo detection | String scan for `{{...}}` | `template.render(**sample_data)` — Jinja2 raises UndefinedError | Jinja2's undefined variable detection is robust; custom scanning misses computed variables |
| Database migration tracking | Custom version table | Alembic | Alembic manages the `alembic_version` table, handles branching, merging, and rollback |
| PostgreSQL startup wait | `sleep 5` in Docker CMD | `depends_on: condition: service_healthy` with `pg_isready` healthcheck | Sleep is fragile; healthcheck is reliable and built into Docker Compose |
| Property slug generation | `name.lower().replace(" ", "-")` | `python-slugify` | Handles unicode, special characters, and collisions |
| Interactive CLI prompts | `input()` calls | Questionary | Handles arrow keys, tab completion, validation, and keyboard interrupt gracefully |
| Structured startup logging | `print()` statements | structlog | Context binding, JSON output, automatic timestamp, and log level filtering |

**Key insight:** In this domain, every "simple" piece of infrastructure has a battle-tested library. The cost of hand-rolling is subtle bugs (config that fails silently, templates that break in production, DB startup races). Use the libraries.

## Common Pitfalls

### Pitfall 1: Alembic Logging Hijack

**What goes wrong:** After running `alembic upgrade head`, all application logging is silenced because Alembic's `env.py` calls `fileConfig(config.config_file_name)` which reconfigures the root logger.

**Why it happens:** Alembic's default env.py template applies the logging config from alembic.ini, which resets all existing handlers.

**How to avoid:** Edit the generated `alembic/env.py` and change:
```python
# Change this:
fileConfig(config.config_file_name)
# To this:
fileConfig(config.config_file_name, disable_existing_loggers=False)
```

**Warning signs:** Application logs disappear after the first migration run.

### Pitfall 2: Config Directory Not Mounted in Docker

**What goes wrong:** Container starts, config/ and templates/ directories are not visible because they are baked into the image at build time rather than mounted as volumes.

**Why it happens:** Forgetting volume mounts in docker-compose.yml — the operator edits files on the host but the container sees the build-time snapshot.

**How to avoid:** Mount `./config:/app/config` and `./templates:/app/templates` as bind mounts in docker-compose.yml. Never COPY config/ in the Dockerfile.

**Warning signs:** Config changes don't take effect after container restart.

### Pitfall 3: Pydantic-settings YAML Extra Not Installed

**What goes wrong:** `YamlConfigSettingsSource` raises an ImportError at runtime because the yaml extra wasn't installed.

**Why it happens:** `pip install pydantic-settings` does not include YAML support. Must use `pydantic-settings[yaml]`.

**How to avoid:** Install as `uv add "pydantic-settings[yaml]"`. Verify with `python -c "from pydantic_settings import YamlConfigSettingsSource"`.

**Warning signs:** `ImportError: pydantic_settings requires PyYAML to use YamlConfigSettingsSource`.

### Pitfall 4: psycopg3 Connection String Uses `+psycopg` Not `+psycopg3`

**What goes wrong:** Using `postgresql+psycopg3://...` raises a SQLAlchemy "Could not load backend" error.

**Why it happens:** SQLAlchemy's dialect name for psycopg3 is `psycopg`, not `psycopg3`.

**How to avoid:** Use `postgresql+psycopg://user:pass@host/db` as the connection string. Verify at setup time.

**Warning signs:** `sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgresql.psycopg3`.

### Pitfall 5: Ollama Check Blocks Startup

**What goes wrong:** Startup hangs if Ollama is not running because the HTTP check has no timeout.

**Why it happens:** Default httpx timeout is none/very long.

**How to avoid:** Always use a short timeout for the Ollama check: `httpx.AsyncClient(timeout=3.0)`. Log "unavailable" and continue — never raise.

**Warning signs:** `docker-compose up` hangs indefinitely with no log output.

### Pitfall 6: Template Validation Fails with Missing Sample Data Keys

**What goes wrong:** Template validates at startup with sample data but fails in production because sample data doesn't cover all template variables.

**Why it happens:** SAMPLE_DATA dict is incomplete — template uses `{{ checkin_time }}` but sample only has `{{ checkin_date }}`.

**How to avoid:** Keep SAMPLE_DATA in a dedicated `tests/fixtures/sample_booking.py` file. Review it against all template variables whenever a template changes. Use Jinja2's `Undefined` tracking mode during validation to catch all missing keys.

**Warning signs:** Template validation passes but emails render with blank fields.

### Pitfall 7: Property Slug Collisions

**What goes wrong:** Two properties get the same slug (e.g., "jay-cabin" and "jay cabin" both slug to "jay-cabin").

**Why it happens:** No uniqueness check during CLI wizard.

**How to avoid:** After slug generation, check the database for existing slugs with `SELECT slug FROM properties WHERE slug = :slug`. If collision, prompt user to pick a different name. Enforce `UNIQUE` constraint on `properties.slug` at the database level.

**Warning signs:** Config loading raises "duplicate slug" key error.

## Code Examples

Verified patterns from official sources:

### Docker Compose with PostgreSQL Healthcheck and Named Volumes

```yaml
# Source: https://docs.docker.com/compose/how-tos/startup-order/
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  app:
    build: .
    restart: unless-stopped
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config:ro
      - ./templates:/app/templates:ro
    depends_on:
      db:
        condition: service_healthy

volumes:
  db_data:
```

### Dockerfile with uv and Python 3.12-slim

```dockerfile
# Source: https://docs.astral.sh/uv/guides/integration/fastapi/
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# Copy application code
COPY . .

# Run via uv-managed venv
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Alembic env.py — Programmatic Connection

```python
# Source: https://alembic.sqlalchemy.org/en/latest/cookbook.html
from alembic import context
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from app.db import Base  # import all models to register them

config = context.config
fileConfig(config.config_file_name, disable_existing_loggers=False)  # KEY: preserve app logs

target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # detect column type changes
        )
        with context.begin_transaction():
            context.run_migrations()
```

### Health Endpoint with Detailed Diagnostics

```python
# Source: based on FastAPI docs + Ollama issue #1378
from fastapi import APIRouter
from sqlalchemy import text
from app.db import engine
from app.config import get_config
import httpx
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health():
    config = get_config()
    result = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "properties": [p.slug for p in config.properties],
    }

    # DB check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["database"] = "connected"
    except Exception as e:
        result["database"] = f"error: {e}"
        result["status"] = "degraded"

    # Ollama check (GET / returns "Ollama is running")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://localhost:11434/")
        result["ollama"] = "available" if resp.status_code == 200 else "unavailable"
    except Exception:
        result["ollama"] = "unavailable"

    return result
```

### Alembic Initial Migration: Properties Table

```python
# alembic/versions/001_initial_properties.py
"""initial properties table

Revision ID: 001
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'properties',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('slug', sa.String(64), nullable=False, unique=True, index=True),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now()),
    )

def downgrade():
    op.drop_table('properties')
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pip + requirements.txt | uv + pyproject.toml | 2024-2025 | 10-100x faster installs; lockfile for reproducibility |
| tiangolo/uvicorn-gunicorn-fastapi Docker image | python:3.12-slim + uv | 2024 (deprecated) | Must build from scratch; no more process manager |
| psycopg2-binary | psycopg3 (`psycopg[binary]`) | 2023+ (for new projects) | psycopg2 receives no new features |
| SQLAlchemy Column() style | Mapped[] + mapped_column() style | SQLAlchemy 2.0 (2023) | Full Python type-checker support; IDE autocomplete |
| @app.on_event("startup") | @asynccontextmanager lifespan | FastAPI deprecation | Cleaner lifecycle; suppresses deprecation warning |
| Gunicorn as process manager | uvicorn --workers N | uvicorn 0.11+ | Uvicorn now has native worker support |

**Deprecated/outdated:**
- `tiangolo/uvicorn-gunicorn-fastapi`: Officially deprecated, no longer maintained. Do not use as Docker base image.
- `@app.on_event("startup")`: Deprecated in FastAPI. Use `lifespan` parameter.
- SQLAlchemy 1.x `Column()` style without `Mapped[]`: Still works but not type-checker compatible. Use 2.0 style.
- `psycopg2-binary`: Still maintained but no new features. Start new projects with `psycopg[binary]`.

## Claude's Discretion Recommendations

These were left to discretion in CONTEXT.md. Research-informed recommendations:

### Config synced to DB vs config-only for properties

**Recommendation: Sync properties to DB.** Downstream phases (Phase 2: bookings, Phase 3: accounting) will join booking records to properties by `property_id` FK. A `properties` table makes these joins trivial and correct. Without it, every query must join on a string slug column or embed property data in each row.

Implementation: CLI wizard writes config YAML AND upserts a row in `properties` table. The slug is the business key — if a property's YAML changes slug, that's an error, not a silent rename.

### Property identifier format

**Recommendation: Integer PK + slug string business key.**
- `id: int` — internal FK target, fast joins
- `slug: str(64)` — user-facing identity, used in config file names and template folder names
- No UUID — adds complexity without benefit at this scale (single-host deployment)

The slug is how everything else in the system refers to a property. It appears in config file names (`config/jay.yaml`), template directories (`templates/jay/`), and URL paths.

### Template variable syntax

**Recommendation: Jinja2.** It is already a FastAPI transitive dependency (FastAPI depends on Starlette which pulls in Jinja2). Using it avoids an extra dependency. The `FileSystemLoader` pattern maps directly to the `templates/default/` + `templates/{slug}/` override pattern. Jinja2's `UndefinedError` enables startup validation.

### Logging framework and format

**Recommendation: structlog 25.5.** Configure for console output (human-readable for self-hosted tool). JSON output only needed if log aggregation is added later. structlog enables the verbose startup log pattern (`"Database connected ✓"`) via context-bound loggers.

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),  # human-readable for self-hosted
    ]
)
```

### Docker base image selection

**Recommendation: `python:3.12-slim`.** Official FastAPI docs recommend building from the official Python image. Slim variant removes development tools (~150MB vs ~900MB full). Use uv for dependency installation inside the container.

## Open Questions

1. **Ollama host in Docker Compose**
   - What we know: Ollama health check hits `http://localhost:11434/`
   - What's unclear: When the app runs in Docker and Ollama runs on the Docker host, `localhost` from inside the container refers to the container, not the host. The correct URL may be `http://host.docker.internal:11434/` (works on Mac/Windows) or `http://172.17.0.1:11434/` (Linux).
   - Recommendation: Make the Ollama URL configurable via `.env` as `OLLAMA_URL=http://host.docker.internal:11434`. Default to `host.docker.internal` since this is self-hosted on Mac.

2. **PDF mappings scope in Phase 1**
   - What we know: `01-05` says "Config-driven email template storage and PDF field mapping schema." Phase 5 is where PDF filling is actually built.
   - What's unclear: How much PDF infrastructure to scaffold in Phase 1 vs. leave entirely to Phase 5.
   - Recommendation: In Phase 1, create only the `pdf_mappings/` directory with a `pdf_mappings/example_form.json` showing the expected schema (field name → value mappings). No Python code for PDF yet — that's Phase 5.

3. **Config validation error format**
   - What we know: App should "print exactly what's wrong" on config error.
   - What's unclear: Whether Pydantic's ValidationError output format is user-friendly enough, or whether a custom formatter is needed.
   - Recommendation: Catch `pydantic.ValidationError`, format each error as `config/{file}: {field}: {message}`, then call `sys.exit(1)`. Pydantic's raw ValidationError output is developer-friendly but includes JSON paths that non-technical users may find confusing.

## Sources

### Primary (HIGH confidence)

- https://pypi.org/project/fastapi/ — version 0.133.1 confirmed
- https://pypi.org/project/pydantic-settings/ — version 2.13.1 confirmed; Python >=3.10 required
- https://docs.pydantic.dev/latest/concepts/pydantic_settings/ — YamlConfigSettingsSource API, settings_customise_sources pattern
- https://pypi.org/project/Jinja2/ — version 3.1.6 confirmed
- https://jinja.palletsprojects.com/en/3.1.x/api/ — compile_templates(), FileSystemLoader, render() API
- https://docs.sqlalchemy.org/en/20/ — version 2.0.47 confirmed
- https://docs.sqlalchemy.org/en/20/orm/declarative_mapping.html — Mapped[], DeclarativeBase pattern
- https://alembic.sqlalchemy.org/en/latest/ — version 1.18.4 confirmed
- https://alembic.sqlalchemy.org/en/latest/cookbook.html — programmatic upgrade, stamp pattern
- https://pypi.org/project/uvicorn/ — version 0.41.0 confirmed
- https://pypi.org/project/structlog/ — version 25.5.0 confirmed
- https://pypi.org/project/httpx/ — version 0.28.1 confirmed
- https://pypi.org/project/psycopg/ — version 3.3.3 confirmed; psycopg2 receives no new features
- https://pypi.org/project/typer/ — version 0.24.1 confirmed
- https://pypi.org/project/questionary/ — version 2.1.1 confirmed
- https://docs.astral.sh/uv/guides/integration/fastapi/ — uv + FastAPI Dockerfile pattern
- https://fastapi.tiangolo.com/deployment/docker/ — python:3.12-slim recommended; tiangolo image deprecated
- https://docs.docker.com/compose/how-tos/startup-order/ — depends_on + service_healthy pattern
- https://github.com/ollama/ollama/issues/1378 — Ollama health endpoint: GET / returns "Ollama is running"

### Secondary (MEDIUM confidence)

- https://berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/ — project structure with alembic upgrade head in Docker CMD
- https://github.com/sqlalchemy/alembic/discussions/1100 — autorun migrations pattern discussion
- WebSearch: "psycopg3 vs psycopg2 SQLAlchemy FastAPI PostgreSQL 2025" — psycopg3 recommended for new projects, verified against psycopg PyPI page

### Tertiary (LOW confidence)

- WebSearch: "Python CLI wizard questionary prompt_toolkit typer 2025" — Typer + Questionary combination; verified against individual PyPI pages

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions confirmed via PyPI, all APIs confirmed via official docs
- Architecture: HIGH — project structure from official FastAPI docs and Alembic cookbook
- Pitfalls: MEDIUM — Alembic logging hijack confirmed via multiple sources; other pitfalls from common sense + verified patterns
- Open questions: LOW — Ollama Docker networking needs runtime validation; confirm on target system

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (stable libraries — FastAPI, SQLAlchemy, Alembic change infrequently)

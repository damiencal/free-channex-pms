# Rental Management Suite

Self-hosted vacation rental management platform. Automates booking operations from notification to accounting entry.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) Ollama running locally for natural language queries

### Setup

1. **Copy environment file:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set a secure `POSTGRES_PASSWORD` (update the password in `DATABASE_URL` to match).

2. **Configure properties:**

   Property configs live in `config/`. Two example properties (Jay and Minnie) are included.

   - Review and update `config/jay.yaml` and `config/minnie.yaml` with real values (lock codes, resort email, check-in instructions)
   - To add a new property, copy `config/config.example.yaml` to `config/{slug}.yaml` and fill in all fields
   - Or use the setup wizard: `python manage.py setup`

3. **Start the system:**

   ```bash
   docker compose up
   ```

   On first start, the database schema is created automatically via Alembic migration.

### Verify

Once running, check the health endpoint:

```bash
curl http://localhost:8000/health
```

The response shows status for database, Ollama, and configured properties.

## Configuration

| File | Purpose |
|------|---------|
| `.env` | Database credentials, Ollama URL (secrets) |
| `config/base.yaml` | System-wide settings (Ollama URL default) |
| `config/{slug}.yaml` | Per-property settings (one file per property) |
| `templates/default/` | Default message templates (Jinja2) |
| `templates/{slug}/` | Per-property template overrides (optional) |
| `pdf_mappings/` | PDF form field mapping schemas (JSON) |

Config changes require a container restart: `docker compose restart app`

## CLI

```bash
python manage.py setup            # Interactive property setup wizard
python manage.py list-properties   # List configured properties
```

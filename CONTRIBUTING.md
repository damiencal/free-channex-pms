# Contributing to Roost

Roost is open source under the [Apache 2.0 license](LICENSE). Contributions are welcome — bug fixes, features, documentation improvements, and new platform adapters.

---

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 16
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Clone the Repository

```bash
git clone https://github.com/captainarcher/roost.git
cd roost
```

### Backend Setup

**Install Python dependencies:**

```bash
uv sync
```

**Configure environment variables:**

```bash
cp .env.example .env
```

Edit `.env` and set `DATABASE_URL` to point to your local Postgres instance:

```
DATABASE_URL=postgresql+psycopg://rental:yourpassword@localhost:5432/rental_management
```

The SMTP variables are only needed if you are testing compliance or communication features locally.

**Configure base settings:**

```bash
cp config/base.example.yaml config/base.yaml
```

Edit `config/base.yaml` to match your local setup (Ollama URL, archive directory, etc.).

**Configure at least one property:**

```bash
cp config/config.example.yaml config/my-cabin.yaml
```

Edit `config/my-cabin.yaml` with your property details. All required fields are documented in the file.

Alternatively, use the interactive setup wizard:

```bash
python manage.py setup
```

**Run database migrations:**

```bash
alembic upgrade head
```

**Start the development server:**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API is now running at `http://localhost:8000`. Interactive API docs are at `http://localhost:8000/docs`.

### Frontend Setup

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs at `http://localhost:5173` and proxies API calls to `http://localhost:8000`. Hot module replacement (HMR) is enabled.

### Docker Setup (Alternative)

If you prefer to avoid local Postgres and Python setup, Docker Compose handles everything:

```bash
docker compose up
```

For development with hot-reload, create a `docker-compose.override.yml` that mounts source as a volume:

```yaml
services:
  roost-api:
    volumes:
      - .:/app
    command: >
      sh -c "/app/.venv/bin/alembic upgrade head &&
             /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
```

Then run `docker compose up` as usual.

---

## Project Structure

```
roost/
├── app/                    # Python backend (FastAPI)
│   ├── api/                # API route modules (health, ingestion, accounting, etc.)
│   ├── models/             # SQLAlchemy ORM models
│   ├── ingestion/          # CSV parsing adapters (Airbnb, VRBO, Mercury, RVshare)
│   ├── accounting/         # Revenue recognition and double-entry journal logic
│   ├── compliance/         # Resort form filling, submission, and urgency scheduling
│   └── communication/      # Guest messaging orchestration and pre-arrival scheduling
├── frontend/               # React SPA (Vite + TypeScript)
├── config/                 # YAML property configs (gitignored except examples)
│   ├── base.example.yaml   # System-wide settings template
│   └── config.example.yaml # Per-property settings template
├── templates/              # Jinja2 message templates
│   └── default/            # Default templates (override per-property in templates/{slug}/)
├── pdf_mappings/           # PDF form field mappings for resort booking forms
├── alembic/                # Database migrations
└── manage.py               # CLI commands (setup, list-properties)
```

---

## Code Style

### Python

- Follow the patterns established in the existing codebase
- Type hints on all function signatures
- Pydantic models for all request and response schemas
- `structlog` for structured logging (not `print` or `logging.info`)
- No linter or formatter is configured yet — match the style of the surrounding code

### TypeScript

- Follow the patterns in the existing frontend code
- Functional components with hooks (no class components)
- `shadcn/ui` for UI components
- No linter is configured yet — match the style of the surrounding code

---

## Making Changes

1. Fork the repository on GitHub
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```
3. Make your changes
4. Test locally — verify both backend startup and frontend build:
   ```bash
   # Backend: should start without errors
   uvicorn app.main:app --host 0.0.0.0 --port 8000

   # Frontend: should produce a build with no type errors
   cd frontend && npm run build
   ```
5. Write a clear commit message describing what changed and why
6. Open a pull request against `main` on GitHub

Pull requests should include a description of the change and the motivation behind it. If your PR fixes a bug, reference the issue number.

---

## Reporting Issues

Use [GitHub Issues](https://github.com/captainarcher/roost/issues) to report bugs or request features.

**For bug reports, include:**

- Steps to reproduce the issue
- Expected behavior
- Actual behavior (including any error messages or logs)
- Environment details (OS, Python version, Docker version if applicable)

**For feature requests:**

Describe the use case you are trying to solve, not just the feature you want. Understanding the problem helps evaluate whether the feature fits the project's scope.

---

## License

By contributing to Roost, you agree that your contributions will be licensed under the [Apache 2.0 license](LICENSE).

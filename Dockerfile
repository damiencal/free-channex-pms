FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies (cached layer — copy lock files first)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-install-project

# Copy application code (NOT config/ or templates/ — those are bind-mounted)
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY manage.py ./

# Default CMD (overridden by docker-compose command)
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

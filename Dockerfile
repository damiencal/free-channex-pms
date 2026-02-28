# Stage 1: Build the React frontend
FROM node:22-alpine AS frontend-build

WORKDIR /frontend

# Copy lock files first for layer caching
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy remaining frontend source and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Python application
FROM python:3.12-slim AS app

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

# Copy compiled frontend from build stage
COPY --from=frontend-build /frontend/dist ./frontend/dist

# Default CMD (overridden by docker-compose command)
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

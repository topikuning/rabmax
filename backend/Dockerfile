# --- Stage 1: build UI (Vite + React + AG Grid) → static ---
FROM node:20-alpine AS webbuild
WORKDIR /web
COPY webui-src/package*.json ./
RUN npm ci || npm install
COPY webui-src/ ./
RUN npm run build

# --- Stage 2: backend (Python 3.12) ---
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv (fast Python package installer)
RUN pip install uv

# Copy project files
COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
COPY seed_data ./seed_data

# Install dependencies
RUN uv pip install --system --no-cache .

# UI hasil build stage 1 → di-serve FastAPI di "/"
COPY --from=webbuild /web/dist ./webui

# Storage volume mount point
RUN mkdir -p /app/storage/uploads /app/storage/outputs /app/storage/master_data

ENV STORAGE_PATH=/app/storage

EXPOSE 8000

# Run migrations lalu start. Bind ke $PORT (Railway inject saat runtime); fallback
# 8000 untuk lokal/docker-compose. Shell-form WAJIB agar $PORT ter-expand.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

# -----------------------------------------------
# Stage 1: Base -- shared deps for API and workers
# -----------------------------------------------
FROM python:3.11-slim AS base

# System deps for lxml and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev libxslt1-dev libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Install Python dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

ENV DJANGO_SETTINGS_MODULE=config.settings.production
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

# -----------------------------------------------
# Stage 2: API -- lightweight, no Playwright
# -----------------------------------------------
FROM base AS api

EXPOSE 8000

CMD ["uv", "run", "gunicorn", "config.asgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-"]

# -----------------------------------------------
# Stage 3: Worker -- includes Playwright + browser
# -----------------------------------------------
FROM base AS worker

# Install Playwright browsers and all required system dependencies
RUN uv run playwright install --with-deps chromium

# Default: run as worker (override command in docker-compose/ECS)
CMD ["uv", "run", "celery", "-A", "config", "worker", \
     "--pool=prefork", "--concurrency=4", "-l", "info"]

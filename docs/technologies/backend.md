# Backend Technologies

## Core Framework

### Django 5.1

- **What**: Python web framework with ORM, admin, and middleware.
- **Why**: Mature, well-documented, excellent ORM for Job model persistence.
- **Our usage**: API views, ORM models, middleware (CORS, JWT auth), settings management.
- **Docs**: https://docs.djangoproject.com/en/5.1/

### Django REST Framework (DRF)

- **What**: Toolkit for building Web APIs on Django.
- **Why**: Serializers for request/response validation, content negotiation, exception handling.
- **Our usage**: `CreateJobSerializer` validates input, `JobSerializer` serializes output. `APIView` for class-based views.
- **Docs**: https://www.django-rest-framework.org/

### Celery 5.4

- **What**: Distributed task queue for asynchronous processing.
- **Why**: Decouples long-running generation from API response time. Supports multiple pool types.
- **Our usage**: Single `generate` task (prefork pool, concurrency=4). Redis as broker. Both Default and Detailed modes share the same pipeline.
- **Docs**: https://docs.celeryq.dev/en/stable/

## Data Validation

### Pydantic 2

- **What**: Data validation and settings management using Python type hints.
- **Why**: Type-safe pipeline data, clear contracts between pipeline stages, JSON serialization.
- **Our usage**: All internal pipeline models (`ExtractedPage`, `ProgressEvent`, `SiteInfo`, etc.) in `apps/core/models.py`.
- **Docs**: https://docs.pydantic.dev/latest/

## HTTP & Scraping

### httpx

- **What**: Async-capable HTTP client for Python.
- **Why**: Async support for concurrent page fetching, connection pooling, timeout control.
- **Our usage**: `HttpClient` wrapper in `apps/core/http_client.py` for all outbound HTTP.
- **Docs**: https://www.python-httpx.org/

### BeautifulSoup4

- **What**: HTML/XML parser.
- **Why**: Robust HTML parsing for metadata extraction from static pages.
- **Our usage**: `MetaExtractor` in `apps/extractor/meta_extractor.py`.
- **Docs**: https://www.crummy.com/software/BeautifulSoup/bs4/doc/

### Playwright

- **What**: Browser automation library.
- **Why**: Renders JavaScript-heavy sites that httpx + BS4 cannot parse. Native Python support.
- **Our usage**: `PlaywrightProvider` in `apps/extractor/playwright_provider.py`. Headless Chromium.
- **Docs**: https://playwright.dev/python/

## Database & Cache

### Redis (via redis-py)

- **What**: In-memory key-value store.
- **Why**: Celery broker, caching (sitemaps, progress), rate limiting (sorted sets), SSE pub/sub.
- **Our usage**: `CacheService` wrapper, `RateLimiter`, pub/sub for `JobStreamView`.
- **Docs**: https://redis-py.readthedocs.io/en/stable/

### Supabase (via supabase-py)

- **What**: Open-source Firebase alternative (PostgreSQL + Auth + Storage).
- **Why**: Managed PostgreSQL, built-in auth, file storage for `llms-full.txt`.
- **Our usage**: `SupabaseService` in `apps/core/supabase_client.py`.
- **Docs**: https://supabase.com/docs

### dj-database-url

- **What**: Utility for configuring Django databases from a URL string.
- **Why**: Single `DATABASE_URL` env var for both local and production databases.
- **Docs**: https://github.com/jazzband/dj-database-url

## Server

### Gunicorn + Uvicorn

- **What**: Gunicorn is a WSGI/ASGI server. Uvicorn is an ASGI server built on uvloop.
- **Why**: Gunicorn manages worker processes; Uvicorn workers handle async (required for SSE).
- **Our usage**: `gunicorn config.asgi:application --worker-class uvicorn.workers.UvicornWorker`
- **Docs**: https://docs.gunicorn.org/ / https://www.uvicorn.org/

## Error Tracking

### Sentry

- **What**: Application error monitoring and performance tracking.
- **Why**: Auto-captures unhandled exceptions with full stack traces, request context, and breadcrumbs. Celery task failures are captured automatically.
- **Our usage**: `sentry-sdk` in `config/settings/base.py`. DSN via `SENTRY_DSN` env var (empty = disabled). Frontend uses `@sentry/nextjs`.
- **Docs**: https://docs.sentry.io/platforms/python/integrations/django/

## Dev Tooling

### uv

- **What**: Fast Python package manager and resolver.
- **Why**: 10-100x faster than pip. Lock file support. Replaces pip + virtualenv.
- **Our usage**: `uv sync --dev`, `uv run pytest`, `uv run ruff check .`
- **Docs**: https://docs.astral.sh/uv/

### ruff

- **What**: Python linter and formatter (replaces flake8 + black + isort).
- **Why**: Extremely fast, comprehensive rule set, single tool for linting and formatting.
- **Our usage**: Configured in `backend/ruff.toml`. Line length 100, double quotes.
- **Docs**: https://docs.astral.sh/ruff/

### pytest

- **What**: Python testing framework.
- **Why**: Fixtures, parametrize, rich assertions, Django integration via pytest-django.
- **Our usage**: 96 tests across core, generator, extractor, and views.
- **Docs**: https://docs.pytest.org/

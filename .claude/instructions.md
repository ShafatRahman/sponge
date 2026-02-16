# Sponge - Claude Code Instructions

## Project Overview

Sponge is an automated llms.txt generator. Users input a website URL, and Sponge crawls it, extracts content, categorizes pages, and produces spec-compliant llms.txt files (per llmstxt.org).

## Architecture

- **Monorepo**: `frontend/` (Next.js 16, Vercel), `backend/` (Django 5.1 + Celery 5.4, AWS ECS Fargate), `infrastructure/` (Terraform)
- **Two generation modes**: Default (httpx + BS4 + LLM, Playwright fallback for CSR) and Detailed (same pipeline + llms-full.txt)
- **Data stores**: PostgreSQL via `DATABASE_URL` (required; Supabase Cloud -- separate dev and prod projects), Supabase Auth + Storage, Upstash Redis (Celery broker, cache, rate limiting, SSE pub/sub)
- **Real-time updates**: Server-Sent Events (SSE) via `GET /api/jobs/{id}/stream/`. No polling. Redis pub/sub delivers events from Celery workers to Django streaming views.
- **ASGI server**: Gunicorn with UvicornWorker for async SSE support (`config/asgi.py`)
- **Secrets**: AWS SSM Parameter Store (SecureString). ECS containers fetch secrets at startup via `secrets` block. Terraform `modules/ssm/` manages parameter creation.

## Code Conventions

- Never use emojis in code, logs, or print statements.
- Backend: class-based modules with dependency injection, Pydantic for internal data, DRF serializers for API boundaries.
- Frontend: functional React components, class-based services/API clients, Zod for runtime validation.
- API boundary: Django sends snake_case JSON, frontend converts to camelCase via Axios interceptors.

## Tooling

- **Backend**: `uv` for deps (not pip), `ruff` for lint/format, `mypy` for types, `pytest` for tests.
- **Frontend**: `npm`, Prettier + ESLint 9 + TypeScript strict mode, Husky + lint-staged for pre-commit.
- **Error tracking**: Sentry on both backend (sentry-sdk, auto-detects Django + Celery) and frontend (@sentry/nextjs). DSN via `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` env vars. Disabled when empty.
- **Error handling**: Custom DRF exception handler (`config/exception_handler.py`) returns clean `{"error": "..."}` JSON for all errors. Error messages from tasks are sanitized before reaching the client. Frontend uses `ApiError` class for friendly user-facing messages and sonner toasts for notifications.
- **Infra**: Terraform modules (vpc, ecr, ecs, alb, iam, ssm), GitHub Actions CI/CD.

## Testing

- **96+ backend tests** across core, generator, extractor, and views.
- Shared fixtures in `backend/conftest.py`: `fake_redis` (fakeredis), `cache_service`, `job_factory`.
- External services mocked with `unittest.mock.patch`. Redis mocked with `fakeredis`.
- Run: `uv run pytest` from `backend/`.

## Key Commands

```bash
# Backend (from backend/)
uv sync --dev              # Install deps
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run pytest              # Test (96+ tests)

# Frontend (from frontend/)
npm run check              # Typecheck + lint + format check
npm run build              # Build

# Local dev (from root)
docker-compose up -d       # Start API + workers + Redis (connects to cloud Supabase Postgres)
```

## Documentation

Project documentation lives in `docs/` with the following sections:
- `setup/` -- local development, environment variables, Docker
- `architecture/` -- system design, backend pipeline, data flow, SSE streaming
- `technologies/` -- every major library/service with learning links
- `deployment/` -- AWS ECS, Vercel, CI/CD, SSM secrets
- `testing/` -- test structure, running tests, writing new tests
- `api/` -- REST endpoints, authentication, SSE protocol
- `contributing/` -- code style, git workflow, docs maintenance

**Before making changes**: Check relevant docs in `docs/` to understand the current design.
**After making changes**: Update relevant docs if you changed architecture, APIs, dependencies, or deployment. See `docs/contributing/docs-maintenance.md` for guidance.

## File Layout

- Pydantic pipeline models: `backend/apps/core/models.py`
- Django Job ORM model: `backend/apps/jobs/models.py`
- Celery tasks (pipeline orchestration): `backend/apps/jobs/tasks.py`
- API views + SSE streaming: `backend/apps/jobs/views.py`
- SSE React hook: `frontend/lib/hooks/use-job-stream.ts`
- Frontend Zod schemas: `frontend/lib/models/job.ts`
- API client singleton: `frontend/lib/api/api-client.ts`
- Supabase auth: `frontend/lib/supabase/`, `frontend/lib/api/auth-service.ts`
- Terraform: `infrastructure/modules/{vpc,ecr,ecs,alb,iam,ssm}/`
- Test fixtures: `backend/conftest.py`
- Project docs: `docs/`

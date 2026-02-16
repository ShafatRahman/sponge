# Local Development Setup

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| [uv](https://docs.astral.sh/uv/) | Latest | Python package manager (replaces pip) |
| Node.js | 20+ | Frontend runtime |
| npm | 10+ | Frontend package manager |
| Docker & Docker Compose | Latest | Local services (Redis, API, workers) |

You also need accounts on:
- [Supabase](https://supabase.com) (free tier) -- Postgres, Auth, Storage. Use **Settings > API Keys** for publishable/secret keys and **Settings > Database** for the connection pooler URI.
- [OpenAI](https://platform.openai.com) -- required for both Default and Detailed modes (LLM-enhanced descriptions)

Optional:
- [Terraform](https://www.terraform.io/) 1.5+ for infrastructure changes
- [Langfuse](https://langfuse.com) for LLM observability (use `LANGFUSE_HOST`, not `LANGFUSE_BASE_URL`)
- [Sentry](https://sentry.io) for error tracking (leave `SENTRY_DSN` empty in local dev)

## Option A: Docker Compose (Recommended)

This starts Redis, the Django API, and Celery workers in containers. They connect to your cloud Supabase project for Postgres.

```bash
# 1. Clone and configure
git clone https://github.com/ShafatRahman/sponge.git
cd sponge
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# Edit both files with your credentials (see environment-variables.md)
#
# IMPORTANT for DATABASE_URL: use the Supabase **connection pooler** URI
# (port 6543), NOT the direct connection (port 5432).
# Direct connections resolve to IPv6 which Docker containers cannot reach.
# Go to supabase.com > Settings > Database > Connection string > "Connection pooling"

# 2. Enable dev-friendly volume mounts (one-time)
cp docker-compose.override.example.yml docker-compose.override.yml

# 3. Start backend stack (Redis + API + workers)
docker-compose up -d

# 4. Run migrations against your Supabase Postgres
docker-compose exec api uv run python manage.py migrate

# 5. Start frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000.

The API runs on http://localhost:8000. Next.js proxies `/api/*` requests to the backend automatically via `next.config.ts` rewrites.

## Option B: Docker for Redis, local backend (Fastest Iteration)

Run only Redis in Docker, everything else locally. Best for rapid backend development.

```bash
# Start Redis only
docker-compose up -d redis

# Backend setup (one-time)
cd backend
uv sync --dev

# Terminal 1: Django API
uv run python manage.py migrate
uv run python manage.py runserver

# Terminal 2: Worker
uv run celery -A config worker --pool=prefork --concurrency=4 -l info

# Terminal 3: Frontend
cd frontend
npm install
npm run dev
```

## When Do I Need to Rebuild Docker?

| Change | Rebuild needed? | Command |
|--------|----------------|---------|
| Python code (any `.py` file) | No (if using override) | `docker-compose restart api` (gunicorn `--reload` catches most changes) |
| Added/changed a dependency in `pyproject.toml` | **Yes** | `docker-compose build api && docker-compose up -d api` |
| Changed `Dockerfile` | **Yes** | `docker-compose build && docker-compose up -d` |
| Changed `docker-compose.yml` | No | `docker-compose up -d` (re-reads config) |
| Frontend code | Never | Turbopack hot-reloads automatically |
| Environment variables in `.env` | No | `docker-compose up -d` (re-reads env) |

## Useful Commands

| Command | Location | Purpose |
|---------|----------|---------|
| `docker-compose logs -f api` | Root | Tail API logs |
| `docker-compose logs -f worker` | Root | Tail worker logs |
| `docker-compose exec api uv run python manage.py shell` | Root | Django shell |
| `uv run ruff check . && uv run ruff format .` | `backend/` | Lint + format |
| `uv run pytest` | `backend/` | Run test suite |
| `npm run check` | `frontend/` | Typecheck + lint + format check |
| `npm run dev` | `frontend/` | Start dev server with hot reload |
| `docker-compose exec redis redis-cli KEYS "ratelimit:*" \| xargs docker-compose exec -T redis redis-cli DEL` | Root | Reset all rate limits |
| `docker-compose exec redis redis-cli FLUSHDB` | Root | Clear all Redis data (cache, rate limits, progress) |

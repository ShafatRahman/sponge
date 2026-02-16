# Docker Configuration

## docker-compose.yml Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `redis` | `redis:7-alpine` | 6379 | Celery broker, cache, SSE pub/sub |
| `api` | Backend Dockerfile (`api` target) | 8000 | Django API (gunicorn + uvicorn workers) |
| `worker` | Backend Dockerfile (`worker` target) | -- | Celery worker for both Default and Detailed modes (prefork pool, Playwright fallback) |

**Note**: PostgreSQL is hosted on Supabase Cloud (dev and prod projects). Docker Compose services connect to it via the `DATABASE_URL` in `backend/.env`. You **must** use the Supabase **connection pooler** URI (port 6543), not the direct connection (port 5432). Direct connections resolve to IPv6 addresses that Docker containers cannot reach.

## Multi-Stage Dockerfile

The backend uses a multi-stage Dockerfile (`backend/Dockerfile`):

- **`base`** stage: Python 3.11, uv, system deps, project dependencies
- **`api`** target: Lightweight image for the Django API server. No Playwright.
- **`worker`** target: Extends base with Playwright and Chromium for browser-based rendering.

This keeps the API image small (~400MB) while the worker image includes the browser (~1.2GB).

## Volumes

- `redis-data`: Persists Redis data (optional, not critical)

## ASGI Server

The API service runs gunicorn with `uvicorn.workers.UvicornWorker` for async support. This is required for Server-Sent Events (SSE) streaming on `GET /api/jobs/<id>/stream/`.

```yaml
command: >
  uv run gunicorn config.asgi:application
  --bind 0.0.0.0:8000
  --worker-class uvicorn.workers.UvicornWorker
  --workers 2
  --timeout 120
  --access-logfile -
```

## Common Operations

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Run migrations
docker-compose exec api uv run python manage.py migrate

# Run backend tests inside container
docker-compose exec api uv run pytest

# Rebuild after Dockerfile changes
docker-compose build --no-cache api

# Reset rate limits (useful during development/testing)
docker-compose exec redis redis-cli KEYS "ratelimit:*" | xargs docker-compose exec -T redis redis-cli DEL

# Clear all Redis data (cache, rate limits, progress)
docker-compose exec redis redis-cli FLUSHDB

# Stop everything
docker-compose down

# Stop and destroy volumes (resets Redis data)
docker-compose down -v
```

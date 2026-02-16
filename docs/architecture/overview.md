# Architecture Overview

Sponge is a monorepo with three primary components:

```
                   +-------------------+
                   |   Frontend        |
                   |   Next.js 16      |
                   |   (Vercel)        |
                   +---------+---------+
                             |
                       SSE / REST
                             |
                   +---------+---------+
                   |   Django API      |
                   |   (ECS Fargate)   |
                   +---------+---------+
                             |
                   +---------+---------+
                   |   Celery Workers  |
                   |   (ECS Fargate)   |
                   +---------+---------+
                       /     |     \
                      /      |      \
              +------+  +----+----+  +----------+
              |Redis |  |Supabase |  |OpenAI    |
              |Upstash| |PG+Auth  |  |Langfuse  |
              |      |  |+Storage |  |          |
              +------+  +---------+  +----------+
```

## Components

### Frontend (`frontend/`)

- **Framework**: Next.js 16 with App Router, React 19
- **UI**: shadcn/ui + Tailwind CSS v4, dark theme (Profound-inspired)
- **State**: React hooks. No global state library needed.
- **API integration**: Axios with interceptors for auth token injection and snake_case/camelCase transformation
- **Real-time updates**: Server-Sent Events (SSE) via `useJobStream` hook
- **Auth**: Supabase Auth (OAuth + email). Optional -- anonymous usage supported.
- **Deployment**: Vercel (auto-deploy on push to main)

### Backend (`backend/`)

- **Framework**: Django 5.1 + Django REST Framework
- **Task queue**: Celery 5.4 with Redis broker
- **Server**: Gunicorn with Uvicorn async workers (ASGI) for SSE support
- **Worker pool**: Single `prefork` pool with `--concurrency=4`. Uses httpx + BeautifulSoup4 for extraction. Playwright (headless Chromium) is a fallback for client-side rendered sites. OpenAI GPT-4o-mini via Langfuse for LLM descriptions in both Default and Detailed modes.
- **Deployment**: AWS ECS Fargate (containerized)

### Infrastructure (`infrastructure/`)

- **IaC**: Terraform with modular structure (`modules/vpc`, `modules/ecr`, `modules/ecs`, `modules/alb`, `modules/iam`, `modules/ssm`)
- **Secrets**: AWS SSM Parameter Store (SecureString) -- secrets are never plain-text in ECS task definitions
- **CI/CD**: GitHub Actions for backend deploy (ECR + ECS) and Terraform plan/apply

## Data Stores

| Store | Service | Purpose |
|-------|---------|---------|
| PostgreSQL | Supabase Cloud (separate dev + prod projects) | Job records, user associations |
| Redis | Upstash (prod) / Docker Compose (local) | Celery broker, cache, rate limiting, SSE pub/sub |
| Object Storage | Supabase Storage | `llms-full.txt` files (Detailed mode) |
| Auth | Supabase Auth | User authentication (OAuth, email/password) |

## Key Design Decisions

1. **ASGI over WSGI**: Required for SSE streaming. Gunicorn with UvicornWorker handles both sync Django views and async streaming.
2. **Redis pub/sub for SSE**: Progress events are published to a Redis channel per job. The SSE view subscribes and streams to the client. Cache is also updated for reconnection support.
3. **SSM over env vars**: Secrets in ECS are fetched from SSM Parameter Store at container startup, not embedded in task definitions.
4. **Single worker pool**: Prefork pool with concurrency=4 handles both Default and Detailed modes. Both modes share the same pipeline (httpx + BS4 + LLM); Detailed mode additionally produces `llms-full.txt`.
5. **Pydantic for pipeline, DRF serializers for API**: Internal data integrity vs. API boundary validation are separate concerns.

# Sponge -- Automated llms.txt Generator

Sponge is a web application that automatically generates spec-compliant [llms.txt](https://llmstxt.org/) files for any website. It crawls a site, extracts metadata and content, categorizes pages, and produces structured markdown files that help LLMs understand your website.

## Architecture

```
Frontend (Next.js)  -->  Django API (ECS)  -->  Celery Workers (ECS)
     |                       |                       |
   Vercel               Supabase (Auth/DB)      Playwright
                        Upstash Redis           OpenAI API
                                                Langfuse
```

- **Frontend**: Next.js 16 with App Router, shadcn/ui, Tailwind CSS v4. Dark theme. Deployed on Vercel.
- **Backend**: Django REST Framework + Celery. Deployed on AWS ECS Fargate.
- **Workers**: Single Celery worker pool (prefork). HTTP-first with Playwright fallback for CSR sites.
- **Infrastructure**: Terraform IaC, GitHub Actions CI/CD.

## Output Modes

| Mode | Output | Browser | LLM | Speed |
|------|--------|---------|-----|-------|
| Default | `llms.txt` (AI-enhanced index with titles + descriptions) | CSR fallback only | GPT-4o-mini | 15-45s |
| Detailed | `llms.txt` + `llms-full.txt` (full page content) | CSR fallback only | GPT-4o-mini | 30s-2min |

## Project Structure

```
sponge/
  frontend/                  # Next.js application (Vercel)
    app/                     # Pages (landing, job detail, auth)
    components/              # UI components (shadcn + custom)
    lib/                     # API clients, Zod models, Supabase, utilities
  backend/                   # Django + Celery (ECS Fargate)
    config/                  # Settings (base/dev/prod), Celery, ASGI, URLs
    apps/
      core/                  # Pydantic models, SSRF guard, rate limiter, cache, auth
      crawler/               # Robots parser, sitemap parser, BFS crawler, page fetcher
      extractor/             # Meta extraction (BS4), content extraction, Playwright provider
      generator/             # URL categorizer, llms.txt builder
      ai/                    # LLM client (OpenAI + Langfuse), description enhancer
      jobs/                  # Django ORM models, DRF serializers/views, Celery tasks, SSE
  infrastructure/            # Terraform IaC (VPC, ECR, ECS, ALB, IAM, SSM)
  docs/                      # Engineering documentation (setup, architecture, tech, API, etc.)
  .github/workflows/         # CI/CD pipelines
  docker-compose.yml         # Local development
```

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 20+
- Docker & Docker Compose
- [Supabase](https://supabase.com) account (free tier)

### 1. Clone and configure

```bash
git clone https://github.com/ShafatRahman/sponge.git
cd sponge
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# Edit both .env files with your Supabase project credentials
# (see docs/setup/environment-variables.md for details)
```

### 2. Start backend services

```bash
docker-compose up -d
```

This starts Redis, Django API, and Celery Worker. They connect to your Supabase Cloud Postgres via `DATABASE_URL`.

Run migrations:

```bash
docker-compose exec api uv run python manage.py migrate
```

### 4. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000

### 5. Run backend without Docker (alternative)

```bash
cd backend
uv sync --dev          # Install all dependencies (creates .venv automatically)
uv run playwright install chromium

# Terminal 1: Django API
uv run python manage.py migrate
uv run python manage.py runserver

# Terminal 2: Worker
uv run celery -A config worker --pool=prefork --concurrency=4 -l info

# (No separate detailed worker needed -- both modes use the same worker)
```

### 6. Code quality checks

**Backend** (from `backend/`):
```bash
uv run ruff check .         # Lint
uv run ruff format .        # Format
uv run mypy apps/           # Type check
uv run pytest               # Test
```

**Frontend** (from `frontend/`):
```bash
npm run check               # Typecheck + lint + format check (all-in-one)
npm run lint:fix             # Auto-fix lint issues
npm run format              # Auto-format with Prettier
```

Pre-commit hooks (via Husky + lint-staged) automatically lint and format staged files on each commit.

## Deployment

### Frontend (Vercel)

Connect the repo to Vercel. Set root directory to `frontend/`. Environment variables are configured in the Vercel dashboard.

### Backend (AWS ECS)

```bash
cd infrastructure
terraform init
terraform plan -var-file=environments/prod/terraform.tfvars
terraform apply -var-file=environments/prod/terraform.tfvars
```

CI/CD is handled by GitHub Actions:
- **Backend CI**: Runs ruff lint/format check on every PR touching `backend/`
- **Frontend CI**: Runs typecheck + lint + format check + build on every PR touching `frontend/`
- **Deploy Backend**: Builds Docker image, pushes to ECR, updates ECS on merge to `main`
- **Terraform**: Plans on PR, applies on merge to `main`

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Supabase Postgres connection string (required). Get from supabase.com > Settings > Database. |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SECRET_KEY` | Supabase secret key (`sb_secret_...`) for server-side access |
| `REDIS_URL` | Upstash Redis connection string |
| `OPENAI_API_KEY` | OpenAI API key (for Detailed mode) |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key |
| `LANGFUSE_HOST` | Langfuse host URL |
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` or `config.settings.production` |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Django API URL (e.g., `http://localhost:8000`) |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key (`sb_publishable_...`) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health/` | Health check (used by ALB) |
| `POST` | `/api/jobs/` | Create a new generation job |
| `GET` | `/api/jobs/<id>/` | Get job status, progress, and results |
| `GET` | `/api/jobs/<id>/stream/` | SSE stream of real-time progress events |
| `GET` | `/api/jobs/history/` | List authenticated user's job history |

See [`docs/api/`](docs/api/) for detailed API reference, authentication guide, and SSE protocol spec.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, shadcn/ui, Tailwind CSS v4, Zod, Axios |
| Backend | Django 5.1, DRF, Celery 5.4, Pydantic 2 |
| Crawler | httpx, BeautifulSoup4, Playwright |
| AI | OpenAI GPT-4o-mini, Langfuse |
| Database | Supabase (PostgreSQL + Auth + Storage) |
| Cache/Queue | Upstash Redis |
| Infrastructure | AWS ECS Fargate, ALB, Terraform |
| CI/CD | GitHub Actions |
| DX | uv, ruff, mypy, Prettier, ESLint 9, Husky, lint-staged |

## Documentation

Full engineering documentation is in [`docs/`](docs/):

| Section | Contents |
|---------|----------|
| [Setup](docs/setup/) | Local development, environment variables, Docker |
| [Architecture](docs/architecture/) | System design, backend pipeline, data flow, SSE streaming |
| [Technologies](docs/technologies/) | Every package/service with learning links |
| [Deployment](docs/deployment/) | AWS ECS, Vercel, CI/CD, SSM secrets |
| [Testing](docs/testing/) | Test structure, running tests, writing new tests |
| [API](docs/api/) | REST endpoints, authentication, SSE protocol |
| [Contributing](docs/contributing/) | Code style, git workflow, docs maintenance |

## License

MIT

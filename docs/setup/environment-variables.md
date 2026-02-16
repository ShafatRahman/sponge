# Environment Variables

All secrets are loaded from `.env` files locally and from AWS SSM Parameter Store in production (see [SSM Secrets](../deployment/ssm-secrets.md)).

## Backend (`backend/.env`)

Copy from `backend/.env.example`:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Supabase Postgres **connection pooler** URI (port 6543). Get from supabase.com > Settings > Database > Connection string, and select **"Connection pooling"** mode. Do NOT use the direct connection (port 5432) -- it resolves to IPv6 which Docker containers cannot reach. |
| `REDIS_URL` | Yes | Redis connection string (e.g. `redis://localhost:6379/0`). Celery broker and progress pub/sub. |
| `SUPABASE_URL` | Yes | Supabase project URL (e.g. `https://xxxx.supabase.co`). |
| `SUPABASE_SECRET_KEY` | Yes | Supabase secret key (`sb_secret_...`) for server-side access (storage uploads, admin operations). |
| `OPENAI_API_KEY` | Yes | GPT-4.1-nano powers description enhancement, site summaries, and polish passes in **both** Default and Detailed modes. Task fails fast with a clear error if missing. |
| `LANGFUSE_PUBLIC_KEY` | No | Langfuse observability. Optional but recommended. |
| `LANGFUSE_SECRET_KEY` | No | Langfuse secret key. |
| `LANGFUSE_HOST` | No | Defaults to `https://cloud.langfuse.com` (EU). Set to `https://us.cloud.langfuse.com` for US region. |
| `SENTRY_DSN` | No | Sentry error tracking DSN. **Leave empty in local dev** to avoid noise. Required in production. |
| `DJANGO_SECRET_KEY` | No | Defaults to insecure dev key. Must set in production. |
| `DJANGO_SETTINGS_MODULE` | No | Defaults to `config.settings.development`. Set to `config.settings.production` in prod. |

## Frontend (`frontend/.env.local`)

Copy from `frontend/.env.example`:

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | No | Backend API URL. Defaults to `http://localhost:8000`. Not needed if using Next.js rewrites (dev). |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL (same as backend). |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Yes | Supabase publishable key (`sb_publishable_...`) for client-side auth. |
| `NEXT_PUBLIC_SENTRY_DSN` | No | Sentry DSN for frontend error tracking. Leave empty to disable. |

## Getting Credentials

1. **Supabase**: Create a project at [supabase.com](https://supabase.com). Find the publishable and secret keys in **Settings > API Keys** (click "Create new API Keys" if you don't see them). For the database URL, go to **Settings > Database > Connection string**, select **"Connection pooling"** mode, copy the URI, and replace `[YOUR-PASSWORD]` with your DB password. Important: use the pooler URL (port 6543), not the direct connection (port 5432).
2. **Upstash Redis** (production): Create a free database at [upstash.com](https://upstash.com). Use the `redis://` connection string.
3. **OpenAI**: Get an API key at [platform.openai.com](https://platform.openai.com/api-keys). Required for both Default and Detailed modes.
4. **Langfuse**: Sign up at [langfuse.com](https://langfuse.com). Create a project and copy the keys.
5. **Sentry**: Create a free project at [sentry.io](https://sentry.io). Copy the DSN from Settings > Client Keys.

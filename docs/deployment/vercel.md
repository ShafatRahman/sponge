# Vercel Deployment (Frontend)

## Setup

1. Connect the GitHub repository to Vercel
2. Set **Root Directory** to `frontend/`
3. Framework preset: **Next.js** (auto-detected)
4. Add environment variables in the Vercel dashboard:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Backend ALB URL (e.g. `https://api.sponge.dev`) |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key (`sb_publishable_...`) |

## Auto-Deploy

Vercel automatically deploys on every push to `main`. Preview deployments are created for pull requests.

## API Proxy

In development, `next.config.ts` rewrites `/api/*` requests to the backend URL to avoid CORS issues. In production, the frontend calls the backend directly (CORS is configured via `CORS_ALLOWED_ORIGINS`).

## Build Command

Default Next.js build: `npm run build`. No custom configuration needed.

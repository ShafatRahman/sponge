# Authentication

## Overview

Sponge supports both authenticated and anonymous usage. Authentication is via Supabase JWT tokens, verified using the JWKS discovery endpoint.

## How It Works

1. **Frontend**: User signs in via Supabase Auth (OAuth or email/password). The Supabase client stores a JWT session.
2. **API requests**: The `ApiClient` Axios interceptor reads the session token and attaches it as `Authorization: Bearer <token>`.
3. **Backend middleware**: `SupabaseJWTAuthMiddleware` intercepts every request:
   - No `Authorization` header: request passes through with `request.user_id = None` (anonymous).
   - Valid Bearer token: verified via the JWKS endpoint (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`). `request.user_id` set to the `sub` claim.
   - Invalid/expired token: returns `401`.

## Token Verification

Supabase Auth issues JWTs signed with asymmetric keys (ES256 by default for new projects). The backend verifies tokens using:

- **JWKS endpoint**: Public keys are fetched from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` and cached for 10 minutes.
- **PyJWKClient**: The `pyjwt` library's `PyJWKClient` handles key fetching, caching, and rotation automatically.
- **Supported algorithms**: ES256, RS256, EdDSA, HS256 (for backward compatibility).
- **Audience**: `authenticated`
- **Subject (`sub`)**: Supabase user UUID

No shared secret or `JWT_SECRET` is needed -- the middleware only requires `SUPABASE_URL` to be set.

## Anonymous Access

Anonymous users can:
- Create generation jobs (rate-limited to 10/day by IP)
- View job status and results (by job ID)

Anonymous users cannot:
- View job history
- Have jobs associated with their account

## Authenticated Benefits

- Higher rate limit (25 jobs/day)
- Job history (GET /api/jobs/history/)
- Jobs are associated with user ID for future features

## SSE Authentication

The SSE endpoint (`GET /api/jobs/{id}/stream/`) does not use Bearer tokens because `EventSource` does not support custom headers. Instead:

- Ownership is checked by comparing `job.user_id` with the request's auth state
- Anonymous users can access any job they created (identified by job ID)
- Authenticated users can only access their own jobs

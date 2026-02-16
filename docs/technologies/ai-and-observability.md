# AI & Observability Technologies

## AI / LLM

### OpenAI API (GPT-4.1-nano)

- **What**: Large Language Model API.
- **Why**: Generates high-quality page descriptions from extracted content. GPT-4.1-nano is the fastest and cheapest non-reasoning model, outperforming GPT-4o-mini on benchmarks.
- **Our usage**: `LLMClient` in `apps/ai/llm_client.py`. Four LLM tasks:
  1. **Description enhancement** (both modes): batch-by-section titles and descriptions
  2. **Site summary** (both modes): blockquote + key notes from homepage
  3. **Content cleaning** (Detailed only): per-page removal of marketing noise (CTAs, logos, testimonials) to produce clean informational markdown for `llms-full.txt`
  4. **Polish pass** (Default only): final consistency refinement of `llms.txt`
- **Cost estimate**: ~$0.15/1M input tokens, ~$0.60/1M output tokens. Default mode: ~$0.001/job. Detailed mode: ~$0.005/job (additional per-page content cleaning).
- **Docs**: https://platform.openai.com/docs/api-reference

### Langfuse

- **What**: Open-source LLM observability platform.
- **Why**: Prompt management, tracing, latency/cost tracking. Essential for debugging LLM behavior.
- **Our usage**: `LLMClient` creates Langfuse traces and generations. Prompts are managed in Langfuse dashboard. Cost estimation stored in job metadata.
- **Docs**: https://langfuse.com/docs

## Auth

### Supabase Auth

- **What**: Authentication service with JWT tokens.
- **Why**: Managed auth with OAuth providers, email/password, and JWT validation.
- **Our usage**:
  - **Frontend**: `@supabase/supabase-js` for login/signup/OAuth. Session stored client-side.
  - **Backend**: `SupabaseJWTAuthMiddleware` validates JWT tokens. Extracts `user_id` from `sub` claim.
- **Docs**: https://supabase.com/docs/guides/auth

### PyJWT

- **What**: Python library for encoding/decoding JWTs.
- **Why**: Validates Supabase JWT tokens in Django middleware.
- **Our usage**: `apps/core/auth_middleware.py` decodes tokens with `HS256` algorithm and `authenticated` audience.
- **Docs**: https://pyjwt.readthedocs.io/

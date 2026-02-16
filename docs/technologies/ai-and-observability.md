# AI & Observability Technologies

## AI / LLM

### OpenAI API (GPT-4o-mini)

- **What**: Large Language Model API.
- **Why**: Generates high-quality page descriptions from extracted content. GPT-4o-mini balances quality and cost.
- **Our usage**: `LLMClient` in `apps/ai/llm_client.py`. Used only in Detailed mode for `DescriptionEnhancer`.
- **Cost estimate**: ~$0.15/1M input tokens, ~$0.60/1M output tokens. Roughly $0.0003 per page.
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

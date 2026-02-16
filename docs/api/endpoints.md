# API Endpoints

Base URL: `http://localhost:8000` (dev) or your ALB domain (prod).

All endpoints accept and return JSON unless otherwise noted. Snake_case is used for all JSON keys.

## Health Check

### `GET /api/health/`

Returns `{"status": "ok"}`. Used by ALB target group health checks.

No authentication required. No rate limiting.

## Jobs

### `POST /api/jobs/`

Create a new llms.txt generation job.

**Request body:**
```json
{
  "url": "https://example.com",
  "mode": "default",
  "max_urls": 50
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | Yes | -- | Website URL to generate llms.txt for. Must pass SSRF validation. |
| `mode` | string | No | `"default"` | `"default"` or `"detailed"`. |
| `max_urls` | integer | No | 50 | Maximum pages to crawl (1-100). |

**Response (201 Created):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "url": "https://example.com",
  "mode": "default",
  "status": "pending",
  "created_at": "2026-02-15T10:30:00Z",
  "updated_at": "2026-02-15T10:30:00Z",
  "completed_at": null
}
```

**Error responses:**
- `400`: Invalid URL, bad mode, or SSRF violation
- `429`: Rate limit exceeded (includes `remaining` and `reset_at`)

### `GET /api/jobs/{id}/`

Get current job status, progress, and results.

**Response (200 OK):**
```json
{
  "id": "a1b2c3d4-...",
  "status": "extracting",
  "progress": {
    "phase": "extracting",
    "message": "Extracting metadata (5/10)",
    "urls_found": 10,
    "completed": 5,
    "total": 10,
    "current_url": "https://example.com/docs/intro"
  },
  "result": null,
  "error": null
}
```

When completed:
```json
{
  "id": "a1b2c3d4-...",
  "status": "completed",
  "progress": null,
  "result": {
    "llms_txt": "# Example\n\n> A great website\n\n## Documentation\n...",
    "llms_full_txt_url": "https://storage.supabase.co/...",
    "total_pages": 10,
    "pages_processed": 9,
    "pages_failed": 1,
    "generation_time_seconds": 12.5,
    "llm_calls_made": 9,
    "llm_cost_usd": 0.0027
  },
  "error": null
}
```

**Error responses:**
- `404`: Job not found or ownership mismatch

### `GET /api/jobs/{id}/stream/`

**SSE stream** of real-time progress events. See [SSE Protocol](./sse-protocol.md) for full details.

**Response**: `Content-Type: text/event-stream`

### `GET /api/jobs/history/`

List authenticated user's recent jobs (most recent first, max 50).

**Requires authentication** (Supabase JWT token).

**Response (200 OK):**
```json
{
  "results": [
    {
      "id": "a1b2c3d4-...",
      "url": "https://example.com",
      "mode": "default",
      "status": "completed",
      "created_at": "2026-02-15T10:30:00Z",
      "updated_at": "2026-02-15T10:32:00Z",
      "completed_at": "2026-02-15T10:32:00Z"
    }
  ]
}
```

**Error responses:**
- `401`: No valid auth token

## Rate Limiting

| User Type | Daily Limit |
|-----------|------------|
| Anonymous (by IP) | 10 requests |
| Authenticated (by user ID) | 25 requests |

Rate limiting uses a sliding window algorithm backed by Redis sorted sets. When the limit is exceeded, the response includes:

```json
{
  "error": "Rate limit exceeded",
  "remaining": 0,
  "reset_at": "2026-02-16T00:00:00Z"
}
```

Defaults are configured in `backend/apps/core/models.py` (`RateLimitConfig`).

### Resetting Rate Limits

To clear all rate limits during development:

```bash
# Docker Compose
docker-compose exec redis redis-cli KEYS "ratelimit:*" | xargs docker-compose exec -T redis redis-cli DEL

# Or clear everything in Redis (also clears cache, progress, etc.)
docker-compose exec redis redis-cli FLUSHDB
```

# Data Flow

## Job Lifecycle

```
User submits URL
       |
       v
POST /api/jobs/
       |
       +---> SSRF validation (SSRFGuard)
       +---> Rate limiting (RateLimiter via Redis sorted sets)
       +---> Create Job record (PostgreSQL)
       +---> Dispatch Celery task (generate)
       |
       v
Return job ID immediately (HTTP 201)
       |
       v
Frontend opens SSE connection: GET /api/jobs/{id}/stream/
       |
       v
Celery worker picks up task:
  1. DISCOVERING -> publish progress to Redis pub/sub
  2. EXTRACTING  -> publish progress to Redis pub/sub
  3. ENHANCING   -> publish progress to Redis pub/sub (both Default and Detailed modes)
  4. GENERATING  -> publish progress to Redis pub/sub
  5. COMPLETED   -> save result to DB, publish final event
       |
       v
SSE view receives pub/sub message -> streams to frontend
       |
       v
Frontend renders result (llms.txt preview + download)
```

## Progress Events

Progress flows through two channels simultaneously:

1. **Redis cache** (`SET job:{id}:progress`): Latest state snapshot. Used when SSE clients reconnect mid-job.
2. **Redis pub/sub** (`PUBLISH job:{id}:events`): Real-time event stream. SSE view subscribes to this channel.

Each progress event is a `ProgressEvent` Pydantic model:

```python
class ProgressEvent(BaseModel):
    job_id: str
    phase: JobStatus       # pending, discovering, extracting, enhancing, generating, completed, failed
    message: str           # Human-readable status message
    urls_found: int | None
    completed: int | None  # Pages processed so far
    total: int | None      # Total pages to process
    current_url: str | None
    timestamp: datetime
```

## Job States

```
PENDING -> DISCOVERING -> EXTRACTING -> [ENHANCING] -> GENERATING -> COMPLETED
    \          \              \              \              \
     +----------+---------- --+--------------+--------------+-----> FAILED
```

Both Default and Detailed modes use LLM enhancement. The ENHANCING phase occurs in both modes.

## API Boundary Serialization

Django sends JSON in `snake_case`. The frontend receives it in `camelCase`:

1. **Request**: Axios request interceptor transforms `camelCase` body -> `snake_case` via `CaseTransformer`
2. **Response**: Axios response interceptor transforms `snake_case` response -> `camelCase` via `CaseTransformer`
3. **SSE events**: The `useJobStream` hook manually applies `CaseTransformer.snakeToCamel()` to each event
4. **Validation**: Zod schemas validate the transformed `camelCase` data at runtime

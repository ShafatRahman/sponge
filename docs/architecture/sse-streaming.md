# Server-Sent Events (SSE) Streaming

Sponge uses SSE for real-time job progress updates. This replaces traditional polling entirely.

## How It Works

### Backend (Django)

The SSE endpoint is `GET /api/jobs/{id}/stream/` (`JobStreamView`).

1. **Initial state**: On connect, the view reads the cached progress from Redis (`GET job:{id}:progress`) and sends it as the first `progress` event. This handles reconnections.
2. **Subscription**: The view subscribes to Redis pub/sub channel `job:{id}:events`.
3. **Streaming**: Each message on the channel is forwarded as an SSE `progress` event.
4. **Terminal state**: When a `completed`, `failed`, or `cancelled` phase arrives, the view fetches the full job snapshot from the database (including result data) and sends it as a `complete` event, then closes the stream.
5. **Heartbeat**: A `: heartbeat` comment is sent every 15 seconds to keep the connection alive through proxies and load balancers.
6. **DB fallback polling**: Every 30 seconds, the view checks the job's status directly in the database. If the job reached a terminal state but the Redis pub/sub event was lost, the stream still closes properly.
7. **Server-side timeout**: If no terminal event is received within 5 minutes, the stream marks the job as failed and closes. This prevents indefinite hanging.
8. **Cleanup**: On client disconnect (`GeneratorExit`), the pub/sub subscription is cleaned up.

### Frontend (React)

The `useJobStream(jobId)` hook manages the `EventSource` lifecycle:

```typescript
const { data, error, isConnected, isTimedOut } = useJobStream(jobId);
```

- Creates an `EventSource` to `/api/jobs/{id}/stream/`
- Listens for `progress` events (updates job status and progress)
- Listens for `complete` events (updates with full result data, closes connection)
- Listens for `error` events (sets error state, closes connection)
- Transforms `snake_case` to `camelCase` using `CaseTransformer`
- Validates with Zod's `JobStatusResponseSchema`
- **Stall detection**: If no progress event is received for 5 minutes, the hook sets `isTimedOut=true` and closes the connection with an error message
- Cleans up on component unmount

## SSE Event Format

```
event: progress
data: {"job_id":"abc","phase":"extracting","message":"Extracting 5/10","completed":5,"total":10}

event: progress
data: {"job_id":"abc","phase":"generating","message":"Building llms.txt..."}

event: complete
data: {"id":"abc","status":"completed","progress":null,"result":{"llms_txt":"# Site\n...","total_pages":10},"error":null}
```

Heartbeat (keeps connection alive, ignored by EventSource):
```
: heartbeat
```

## ASGI Requirement

SSE requires long-lived HTTP connections. Django's default WSGI mode (sync workers) would block a thread per SSE connection. The solution:

- **ASGI application**: `config/asgi.py` using `django.core.asgi.get_asgi_application()`
- **Uvicorn workers**: Gunicorn runs with `--worker-class uvicorn.workers.UvicornWorker`
- **StreamingHttpResponse**: Django's `StreamingHttpResponse` with a generator function that yields SSE-formatted strings

The same ASGI application handles both regular REST requests and SSE streams.

## Redis Pub/Sub Architecture

```
Celery Worker                    Django API                     Browser
     |                              |                              |
     | PUBLISH job:123:events       |                              |
     |----------------------------->|                              |
     |                              | SUBSCRIBE job:123:events     |
     | SET job:123:progress         |<-------(on connect)          |
     |----------------------------->|                              |
     |                              | event: progress              |
     |                              |----------------------------->|
     |                              |                              |
     | PUBLISH (completed)          |                              |
     |----------------------------->|                              |
     |                              | event: complete              |
     |                              |----------------------------->|
     |                              | (close stream)               |
     |                              |---X                          |
```

## Error Handling & Timeouts

- **Connection drop**: `EventSource` natively reconnects on transient errors. The initial cached progress is re-sent on reconnect.
- **Job already complete**: If the job is in a terminal state when SSE connects, the view immediately sends the `complete` event and closes.
- **Redis unavailable**: The `CacheService.publish()` method silently logs errors. The DB fallback polling (every 30s) ensures the frontend still gets notified.
- **Missing API key**: The `generate` task checks for `OPENAI_API_KEY` immediately and fails fast with a descriptive error message before any work begins.
- **Celery task timeout**: Tasks have explicit time limits (soft: 4 min, hard: 5 min). `SoftTimeLimitExceeded` triggers `on_failure` which publishes a failed event.
- **Server-side SSE timeout**: The stream closes after 5 minutes regardless, marking the job as failed if still running.
- **Client-side stall detection**: The frontend hook closes the connection after 5 minutes without progress and shows a "stalled" message.

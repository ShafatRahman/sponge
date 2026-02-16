# SSE Protocol Reference

## Endpoint

```
GET /api/jobs/{id}/stream/
```

Returns `Content-Type: text/event-stream` with `Cache-Control: no-cache` and `X-Accel-Buffering: no`.

## Event Types

### `progress`

Sent during job execution for each phase transition and periodic progress updates.

```
event: progress
data: {"job_id":"abc-123","phase":"extracting","message":"Extracting metadata (5/10)","urls_found":10,"completed":5,"total":10,"current_url":"https://example.com/docs","timestamp":"2026-02-15T10:30:05Z"}
```

Fields in `data`:
| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Job UUID |
| `phase` | string | Current phase: `pending`, `discovering`, `extracting`, `enhancing`, `generating` |
| `message` | string | Human-readable status |
| `urls_found` | int/null | Total pages discovered (set during discovery) |
| `completed` | int/null | Pages processed so far |
| `total` | int/null | Total pages to process |
| `current_url` | string/null | URL currently being processed |
| `timestamp` | string | ISO 8601 timestamp |

### `complete`

Sent when the job reaches a terminal state. Contains the full job snapshot including results. The stream closes after this event.

```
event: complete
data: {"id":"abc-123","status":"completed","progress":null,"result":{"llms_txt":"# Site\n...","llms_full_txt_url":null,"total_pages":10,"pages_processed":9,"pages_failed":1,"generation_time_seconds":12.5,"llm_calls_made":0,"llm_cost_usd":0},"error":null}
```

### `error`

Sent when the SSE connection encounters a problem (e.g., job not found).

```
event: error
data: {"error":"Job not found"}
```

### Heartbeat

A comment line sent every 15 seconds to keep the connection alive. Not a named event -- `EventSource` ignores it.

```
: heartbeat
```

## Connection Lifecycle

1. Client opens `EventSource` to `/api/jobs/{id}/stream/`
2. Server sends initial cached progress (if any) as a `progress` event
3. If job is already terminal, server sends `complete` and closes
4. Otherwise, server subscribes to Redis pub/sub `job:{id}:events`
5. Each published message is streamed as a `progress` or `complete` event
6. Every 30 seconds, the server also polls the DB as a fallback (in case a Redis event was missed)
7. On `complete`, the stream closes
8. If 5 minutes pass without a terminal event, the server marks the job as failed and closes
9. On client disconnect, pub/sub subscription is cleaned up

## Reconnection

`EventSource` natively reconnects on transient errors. On reconnection:
- The server re-reads the cached progress from Redis and sends it as the initial event
- The client picks up from the current state (no duplicate processing)

## Frontend Usage

```typescript
import { useJobStream } from "@/lib/hooks/use-job-stream";

function JobPage({ jobId }: { jobId: string }) {
  const { data, error, isConnected, isTimedOut } = useJobStream(jobId);

  if (isTimedOut) return <StalledMessage />;
  if (!data) return <LoadingSkeleton />;
  if (data.status === "failed") return <ErrorMessage error={data.error ?? error} />;
  if (data.status === "completed") return <ResultPreview result={data.result} />;
  return <GenerationProgress status={data.status} progress={data.progress} />;
}
```

## Timeouts

| Layer | Timeout | Behavior |
|-------|---------|----------|
| Celery task (default) | 2 min soft / 2.5 min hard | `SoftTimeLimitExceeded` -> `on_failure` publishes failed event |
| Celery task (detailed) | 4 min soft / 5 min hard | Same as above |
| SSE server stream | 5 min | Marks job as failed and closes stream |
| SSE DB fallback poll | Every 30s | Catches terminal states missed by Redis |
| Frontend stall detection | 5 min no progress | Closes connection, shows "stalled" message |

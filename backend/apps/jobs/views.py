"""Django REST Framework views for the Jobs API."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING, Any

import redis as redis_lib
from django.conf import settings
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from rest_framework.request import Request

from apps.core.models import JobMode, JobStatus, RateLimitConfig
from apps.core.rate_limiter import RateLimiter
from apps.core.supabase_client import SupabaseService
from apps.jobs.models import Job
from apps.jobs.serializers import (
    CreateJobSerializer,
    JobSerializer,
)

logger = logging.getLogger(__name__)

# User-facing fallback for error messages that look like internal exceptions.
_GENERIC_USER_ERROR = "Something went wrong during generation. Please try again."

# Substrings that indicate a message is safe to show to the user.
_SAFE_ERROR_SUBSTRINGS = [
    "rate limit",
    "timed out",
    "timeout",
    "not found",
    "not set",
    "api key",
    "ssrf",
    "security",
    "exceeded",
    "please try",
    "too many",
    "unavailable",
]


def _safe_error_message(raw: str | None) -> str | None:
    """Return a user-safe error message, replacing internal details with a generic one."""
    if not raw:
        return None
    lower = raw.lower()
    for safe in _SAFE_ERROR_SUBSTRINGS:
        if safe in lower:
            return raw[:300]
    # Looks like a raw traceback or internal error -- hide it.
    return _GENERIC_USER_ERROR


def _get_redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL)


def _get_client_ip(request: Request) -> str:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


class JobCreateView(APIView):
    """POST /api/jobs/ -- Create a new generation job."""

    def post(self, request: Request) -> Response:
        serializer = CreateJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Rate limiting
        rate_config = RateLimitConfig()
        rate_limiter = RateLimiter(_get_redis())
        user_id = getattr(request, "user_id", None)
        ip_address = _get_client_ip(request)

        if user_id:
            rate_result = rate_limiter.check_user(
                str(user_id), rate_config.authenticated_daily_limit
            )
        else:
            rate_result = rate_limiter.check_ip(ip_address, rate_config.anonymous_daily_limit)

        if not rate_result.allowed:
            return Response(
                {
                    "error": "Rate limit exceeded",
                    "remaining": rate_result.remaining,
                    "reset_at": rate_result.reset_at.isoformat() if rate_result.reset_at else None,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Create the job
        url = serializer.validated_data["url"]
        mode = serializer.validated_data["mode"]
        max_urls = serializer.validated_data.get("max_urls", 50)

        job = Job.objects.create(
            url=url,
            mode=mode,
            status=JobStatus.PENDING.value,
            config={"crawl": {"max_urls": max_urls}},
            user_id=user_id,
            ip_address=ip_address,
        )

        # Dispatch Celery task
        config_dict = {"mode": mode, "crawl": {"max_urls": max_urls}}
        from apps.jobs.tasks import generate

        generate.delay(str(job.id), url, config_dict)

        logger.info("Job %s created: %s [%s]", job.id, url, mode)
        return Response(
            JobSerializer(job).data,
            status=status.HTTP_201_CREATED,
        )


class JobDetailView(APIView):
    """GET /api/jobs/<id>/ -- Get job status, progress, and results."""

    def get(self, request: Request, job_id: str) -> Response:
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check ownership for authenticated users
        user_id = getattr(request, "user_id", None)
        if job.user_id and user_id and str(job.user_id) != str(user_id):
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        # Fetch progress from Redis
        progress_data = None
        try:
            r = _get_redis()
            raw = r.get(f"job:{job_id}:progress")
            if raw:
                progress_data = json.loads(raw)
        except Exception:
            logger.debug("Could not fetch progress from Redis for job %s", job_id)

        # Build result if completed
        result_data = None
        if job.status == JobStatus.COMPLETED.value and job.result_llms_txt:
            meta = job.result_meta or {}
            llms_full_txt_url = None
            if job.llms_full_txt_key:
                try:
                    supa = SupabaseService()
                    llms_full_txt_url = supa.get_public_url(job.llms_full_txt_key)
                except Exception:
                    logger.debug("Could not get storage URL for job %s", job_id)

            result_data = {
                "llms_txt": job.result_llms_txt,
                "llms_full_txt_url": llms_full_txt_url,
                "total_pages": meta.get("total_pages", 0),
                "pages_processed": meta.get("pages_processed", 0),
                "pages_failed": meta.get("pages_failed", 0),
                "generation_time_seconds": meta.get("generation_time_seconds", 0),
                "llm_calls_made": meta.get("llm_calls_made", 0),
                "llm_cost_usd": meta.get("llm_cost_usd", 0),
            }

        response_data = {
            "id": str(job.id),
            "status": job.status,
            "progress": progress_data,
            "result": result_data,
            "error": _safe_error_message(job.error_message),
        }

        return Response(response_data)


class JobListView(APIView):
    """GET /api/jobs/ -- List user's job history."""

    def get(self, request: Request) -> Response:
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "Authentication required for job history"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        jobs = Job.objects.filter(user_id=user_id).order_by("-created_at")[:50]
        serializer = JobSerializer(jobs, many=True)
        return Response({"results": serializer.data})


TERMINAL_STATUSES = {
    JobStatus.COMPLETED.value,
    JobStatus.FAILED.value,
    JobStatus.CANCELLED.value,
}

SSE_HEARTBEAT_SECONDS = 15
SSE_STREAM_TIMEOUT_SECONDS = 300  # 5 minutes: give up if no terminal event
SSE_DB_POLL_SECONDS = 30  # Fallback: check DB status every 30s in case Redis event was lost


class _EventStreamRenderer(BaseRenderer):
    """Dummy renderer so DRF content negotiation accepts text/event-stream."""

    media_type = "text/event-stream"
    format = "txt"

    def render(self, data, accepted_media_type=None, renderer_context=None):  # type: ignore[override]
        return data


class JobStreamView(APIView):
    """GET /api/jobs/<id>/stream/ -- SSE stream of job progress events.

    Uses Redis pub/sub to push real-time updates. On connect, the current
    cached progress is sent as the initial event so reconnections pick up
    where they left off. A heartbeat comment is sent every 15 seconds to
    keep the connection alive through proxies/load balancers.
    """

    # EventSource sends Accept: text/event-stream which doesn't match
    # JSONRenderer. Add a renderer so DRF's content negotiation passes.
    # The renderer is never actually used -- this view returns
    # StreamingHttpResponse directly, bypassing DRF's rendering pipeline.
    renderer_classes = [JSONRenderer, _EventStreamRenderer]

    def get(self, request: Request, job_id: str) -> StreamingHttpResponse:
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return StreamingHttpResponse(
                _sse_error("Job not found"),
                content_type="text/event-stream",
                status=404,
            )

        # Ownership check
        user_id = getattr(request, "user_id", None)
        if job.user_id and user_id and str(job.user_id) != str(user_id):
            return StreamingHttpResponse(
                _sse_error("Job not found"),
                content_type="text/event-stream",
                status=404,
            )

        response = StreamingHttpResponse(
            _stream_events(job_id, job.status),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


def _sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a single SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _sse_error(message: str) -> str:
    """Format an SSE error event."""
    return _sse_event("error", {"error": message})


async def _build_job_snapshot(job_id: str) -> dict[str, Any] | None:
    """Build a full job status snapshot from the DB, including result data."""
    from asgiref.sync import sync_to_async

    try:
        job = await sync_to_async(Job.objects.get)(id=job_id)
    except Job.DoesNotExist:
        return None

    result_data = None
    if job.status == JobStatus.COMPLETED.value and job.result_llms_txt:
        meta = job.result_meta or {}
        llms_full_txt_url = None
        if job.llms_full_txt_key:
            try:
                supa = SupabaseService()
                llms_full_txt_url = supa.get_public_url(job.llms_full_txt_key)
            except Exception:
                logger.debug("Could not get storage URL for job %s", job_id)

        result_data = {
            "llms_txt": job.result_llms_txt,
            "llms_full_txt_url": llms_full_txt_url,
            "total_pages": meta.get("total_pages", 0),
            "pages_processed": meta.get("pages_processed", 0),
            "pages_failed": meta.get("pages_failed", 0),
            "generation_time_seconds": meta.get("generation_time_seconds", 0),
            "llm_calls_made": meta.get("llm_calls_made", 0),
            "llm_cost_usd": meta.get("llm_cost_usd", 0),
        }

    return {
        "id": str(job.id),
        "status": job.status,
        "progress": None,
        "result": result_data,
        "error": _safe_error_message(job.error_message),
    }


async def _stream_events(job_id: str, initial_status: str) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE events from Redis pub/sub.

    1. Send the current cached progress as the initial event.
    2. If the job is already terminal, send the final snapshot and return.
    3. Otherwise subscribe to the Redis pub/sub channel and stream events.
    4. Send heartbeat comments every 15 seconds to keep the connection alive.
    5. Any unexpected error sends a safe error event and closes the stream.
    """
    from asgiref.sync import sync_to_async

    pubsub = None
    try:
        r = _get_redis()

        # Send initial cached progress
        cached_raw = r.get(f"job:{job_id}:progress")
        if cached_raw:
            try:
                cached = json.loads(cached_raw)
                yield _sse_event("progress", cached)
            except json.JSONDecodeError:
                pass

        # If already terminal, send the final snapshot and close
        if initial_status in TERMINAL_STATUSES:
            snapshot = await _build_job_snapshot(job_id)
            if snapshot:
                yield _sse_event("complete", snapshot)
            return

        # Subscribe to real-time events
        pubsub = r.pubsub()
        channel = f"job:{job_id}:events"
        pubsub.subscribe(channel)

        start_time = time.monotonic()
        last_heartbeat = time.monotonic()
        last_db_poll = time.monotonic()

        while True:
            now = time.monotonic()

            # Hard timeout: close the stream after SSE_STREAM_TIMEOUT_SECONDS
            if now - start_time >= SSE_STREAM_TIMEOUT_SECONDS:
                logger.warning("SSE stream timed out for job %s after %ds", job_id, SSE_STREAM_TIMEOUT_SECONDS)
                # Mark the job as failed if it is still running
                await sync_to_async(
                    Job.objects.filter(id=job_id)
                    .exclude(status__in=[s for s in TERMINAL_STATUSES])
                    .update
                )(
                    status=JobStatus.FAILED.value,
                    error_message="Job timed out after exceeding the maximum allowed duration.",
                    updated_at=timezone.now(),
                )
                timeout_snapshot = await _build_job_snapshot(job_id)
                if timeout_snapshot:
                    yield _sse_event("complete", timeout_snapshot)
                else:
                    yield _sse_event("error", {"error": "Generation timed out. Please try again."})
                return

            # Non-blocking pub/sub check: run in thread to avoid blocking the event loop
            message = await asyncio.to_thread(pubsub.get_message, timeout=1.0)

            if message and message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    phase = data.get("phase", "")

                    if phase in TERMINAL_STATUSES:
                        snapshot = await _build_job_snapshot(job_id)
                        if snapshot:
                            yield _sse_event("complete", snapshot)
                        else:
                            yield _sse_event("complete", data)
                        return

                    yield _sse_event("progress", data)
                except json.JSONDecodeError:
                    logger.debug("Invalid JSON on channel %s", channel)

            # Fallback: periodically poll the DB in case the Redis event was missed
            if now - last_db_poll >= SSE_DB_POLL_SECONDS:
                last_db_poll = now
                try:
                    job_status = await sync_to_async(
                        Job.objects.filter(id=job_id).values_list("status", flat=True).first
                    )()
                    if job_status and job_status in TERMINAL_STATUSES:
                        logger.info("DB poll detected terminal status for job %s", job_id)
                        snapshot = await _build_job_snapshot(job_id)
                        if snapshot:
                            yield _sse_event("complete", snapshot)
                        return
                except Exception:
                    logger.debug("DB poll failed for job %s", job_id, exc_info=True)

            # Heartbeat to keep connection alive
            if now - last_heartbeat >= SSE_HEARTBEAT_SECONDS:
                yield ": heartbeat\n\n"
                last_heartbeat = now

    except GeneratorExit:
        logger.debug("SSE client disconnected for job %s", job_id)
    except Exception:
        logger.exception("Unexpected error in SSE stream for job %s", job_id)
        yield _sse_event("error", {"error": "Something went wrong. Please try again."})
    finally:
        if pubsub is not None:
            try:
                pubsub.unsubscribe()
                pubsub.close()
            except Exception:
                logger.debug("Error closing pubsub for job %s", job_id, exc_info=True)

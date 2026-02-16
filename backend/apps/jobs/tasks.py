"""Celery task definitions for llms.txt generation."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any
from urllib.parse import urlparse

# Celery workers run async pipelines via asyncio.run() inside prefork
# processes. This env var bypasses Django's SynchronousOnlyOperation check
# which is a false positive in worker processes (they don't serve ASGI).
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

import redis as redis_lib
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.utils import timezone

from apps.core.cache import CacheService
from apps.core.http_client import HttpClient
from apps.core.models import (
    DiscoveredPage,
    ExtractedPage,
    GenerationConfig,
    JobMode,
    JobStatus,
    LlmsTxtResult,
    ProgressEvent,
    SiteInfo,
)
from apps.core.ssrf_protection import SSRFGuard
from apps.core.supabase_client import SupabaseService
from apps.crawler.link_crawler import LinkCrawler
from apps.crawler.page_fetcher import SmartPageFetcher
from apps.crawler.robots_parser import RobotsParser
from apps.crawler.sitemap_parser import SitemapParser
from apps.extractor.content_extractor import ContentExtractor
from apps.extractor.meta_extractor import MetaExtractor
from apps.generator.llms_txt_builder import LlmsTxtBuilder
from apps.generator.url_categorizer import URLCategorizer
from apps.jobs.models import Job
from config.celery import app

logger = logging.getLogger(__name__)

# Map known exception types to user-friendly error messages.
_FRIENDLY_ERRORS: dict[str, str] = {
    "ConnectionError": "Could not connect to a required service. Please try again.",
    "ConnectionRefusedError": "Could not connect to a required service. Please try again.",
    "TimeoutError": "The operation took too long and was stopped. Please try again.",
    "AuthenticationError": "API authentication failed. Please check your API keys.",
    "RateLimitError": "An external API rate limit was hit. Please try again in a moment.",
    "OperationalError": "A database error occurred. Please try again.",
    "SSRFError": "The URL could not be accessed for security reasons.",
}

# Substrings in error messages that indicate a known, safe-to-expose issue.
_SAFE_SUBSTRINGS = [
    "SSRF",
    "OPENAI_API_KEY",
    "rate limit",
    "timed out",
    "timeout",
    "DNS",
    "Name or service not known",
]

GENERIC_ERROR = "Something went wrong during generation. Please try again."


def _sanitize_error(exc: Exception) -> str:
    """Return a user-safe error message.

    Known exception types get a friendly message. If the raw message contains
    a safe substring it is kept. Everything else becomes a generic message.
    The full exception is always logged separately.
    """
    exc_type = type(exc).__name__
    if exc_type in _FRIENDLY_ERRORS:
        return _FRIENDLY_ERRORS[exc_type]

    raw = str(exc)
    for safe in _SAFE_SUBSTRINGS:
        if safe.lower() in raw.lower():
            return raw[:200]

    return GENERIC_ERROR


class BaseGenerationTask(Task):
    """Base class for generation tasks with shared infrastructure."""

    abstract = True
    max_retries = 2
    default_retry_delay = 30

    def __init__(self) -> None:
        super().__init__()
        self._redis: redis_lib.Redis | None = None
        self._cache: CacheService | None = None
        self._supabase: SupabaseService | None = None

    @property
    def redis(self) -> redis_lib.Redis:
        if self._redis is None:
            self._redis = redis_lib.from_url(settings.REDIS_URL)
        return self._redis

    @property
    def cache(self) -> CacheService:
        if self._cache is None:
            self._cache = CacheService(self.redis)
        return self._cache

    @property
    def supabase(self) -> SupabaseService:
        if self._supabase is None:
            self._supabase = SupabaseService()
        return self._supabase

    def publish_progress(self, job_id: str, phase: JobStatus, message: str, **kwargs: Any) -> None:
        """Publish a progress event to Redis cache and pub/sub for SSE streaming."""
        event = ProgressEvent(
            job_id=job_id,
            phase=phase,
            message=message,
            **kwargs,
        )
        payload = event.model_dump_json()
        self.cache.set(f"job:{job_id}:progress", payload, ttl_seconds=300)
        self.cache.publish(f"job:{job_id}:events", payload)

    def update_job_status(self, job_id: str, status: JobStatus) -> None:
        """Update job status in the database."""
        Job.objects.filter(id=job_id).update(status=status.value, updated_at=timezone.now())

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: Any,
        kwargs: Any,
        einfo: Any,
    ) -> None:
        """Handle task failure: update job status and publish a safe error message."""
        job_id = args[0] if args else kwargs.get("job_id")
        if job_id:
            if isinstance(exc, SoftTimeLimitExceeded):
                error_msg = "Job exceeded the maximum allowed duration and was terminated."
            else:
                error_msg = _sanitize_error(exc)

            Job.objects.filter(id=job_id).update(
                status=JobStatus.FAILED.value,
                error_message=error_msg,
                updated_at=timezone.now(),
            )
            self.publish_progress(job_id, JobStatus.FAILED, error_msg)
        logger.exception("Task %s failed for job %s", task_id, job_id)


@app.task(
    bind=True,
    base=BaseGenerationTask,
    name="apps.jobs.tasks.generate",
    soft_time_limit=240,
    time_limit=300,
)
def generate(self: BaseGenerationTask, job_id: str, url: str, config_dict: dict) -> dict:
    """Unified generation task for both Default and Detailed modes.

    Both modes share the same pipeline:
    1. Discovery (robots.txt, sitemap, BFS fallback)
    2. Smart extraction (HTTP-first, Playwright fallback for CSR)
    3. LLM description enhancement
    4. Categorization and assembly

    The only difference: Detailed mode additionally produces llms-full.txt.
    """
    # Fail fast if OpenAI key is missing -- both modes now require LLM
    openai_key = getattr(settings, "OPENAI_API_KEY", None) or os.environ.get("OPENAI_API_KEY", "")
    if not openai_key.strip():
        error_msg = "OPENAI_API_KEY is not set. Generation requires an OpenAI API key."
        logger.error(error_msg)
        Job.objects.filter(id=job_id).update(
            status=JobStatus.FAILED.value,
            error_message=error_msg,
            updated_at=timezone.now(),
        )
        self.publish_progress(job_id, JobStatus.FAILED, error_msg)
        return {"error": error_msg}

    start_time = time.time()
    gen_config = GenerationConfig(**config_dict)

    self.update_job_status(job_id, JobStatus.DISCOVERING)
    self.publish_progress(job_id, JobStatus.DISCOVERING, "Analyzing website structure...")

    result = asyncio.run(_run_pipeline(self, job_id, url, gen_config))

    elapsed = time.time() - start_time
    result.generation_time_seconds = elapsed

    # Upload llms-full.txt to storage (Detailed mode only)
    storage_key = ""
    if result.llms_full_txt:
        storage_key = f"jobs/{job_id}/llms-full.txt"
        self.supabase.upload_file(storage_key, result.llms_full_txt.encode("utf-8"))

    Job.objects.filter(id=job_id).update(
        status=JobStatus.COMPLETED.value,
        result_llms_txt=result.llms_txt,
        result_meta=result.model_dump(exclude={"llms_txt", "llms_full_txt"}),
        llms_full_txt_key=storage_key,
        completed_at=timezone.now(),
        updated_at=timezone.now(),
    )

    self.publish_progress(job_id, JobStatus.COMPLETED, "Generation complete")
    logger.info("Generation complete for job %s [%s] in %.1fs", job_id, gen_config.mode, elapsed)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Unified pipeline
# ---------------------------------------------------------------------------


async def _discover_pages(
    task: BaseGenerationTask,
    job_id: str,
    url: str,
    config: GenerationConfig,
    http_client: HttpClient,
    ssrf_guard: SSRFGuard,
) -> list[DiscoveredPage]:
    """Shared discovery phase: robots.txt -> sitemap -> BFS fallback."""
    robots_parser = RobotsParser(http_client)
    robots_result = await robots_parser.parse(url)

    sitemap_parser = SitemapParser(http_client, task.cache)
    sitemap_result = await sitemap_parser.parse(url, robots_result.sitemap_urls)

    if sitemap_result.entries:
        pages = [DiscoveredPage(url=e.url, source="sitemap") for e in sitemap_result.entries]
    else:
        link_crawler = LinkCrawler(http_client, ssrf_guard, config.crawl)
        pages = await link_crawler.crawl(url, robots_result.disallowed_paths)

    pages = pages[: config.crawl.max_urls]
    task.publish_progress(
        job_id,
        JobStatus.DISCOVERING,
        f"Found {len(pages)} pages",
        urls_found=len(pages),
    )
    return pages


async def _run_pipeline(
    task: BaseGenerationTask,
    job_id: str,
    url: str,
    config: GenerationConfig,
) -> LlmsTxtResult:
    """Execute the unified generation pipeline for both modes."""
    ssrf_guard = SSRFGuard()
    ssrf_guard.validate_url(url)

    http_client = HttpClient(config.crawl)
    meta_extractor = MetaExtractor()
    content_extractor = ContentExtractor()

    try:
        # Phase 1: Discovery
        pages = await _discover_pages(task, job_id, url, config, http_client, ssrf_guard)

        # Phase 2: Smart extraction (HTTP-first, Playwright fallback for CSR)
        task.update_job_status(job_id, JobStatus.EXTRACTING)

        async def on_extract_progress(completed: int, total: int, current_url: str) -> None:
            task.publish_progress(
                job_id,
                JobStatus.EXTRACTING,
                f"Extracting pages ({completed}/{total})",
                completed=completed,
                total=total,
                current_url=current_url,
            )

        fetcher = SmartPageFetcher(
            http_client,
            meta_extractor,
            content_extractor,
            config.browser,
            concurrency=10,
            delay_ms=config.crawl.crawl_delay_ms,
        )
        extracted_pages = await fetcher.fetch_all(pages, on_progress=on_extract_progress)

        # Phase 3: Categorization (moved before enhancement for section-aware batching)
        categorizer = URLCategorizer()
        pages_with_content = [p for p in extracted_pages if not p.error]
        sections_extracted = categorizer.categorize(pages_with_content)

        # Phase 4: LLM Enhancement (batch by section for cross-page awareness)
        task.update_job_status(job_id, JobStatus.ENHANCING)
        task.publish_progress(
            job_id,
            JobStatus.ENHANCING,
            "Enhancing descriptions with AI...",
        )

        from apps.ai.description_enhancer import DescriptionEnhancer
        from apps.ai.llm_client import LLMClient

        llm_client = LLMClient(config.ai)
        enhancer = DescriptionEnhancer(llm_client, config.ai)

        async def on_enhance_progress(completed: int, total: int, section_name: str) -> None:
            task.publish_progress(
                job_id,
                JobStatus.ENHANCING,
                f"Enhancing descriptions ({completed}/{total})",
                completed=completed,
                total=total,
                current_url=section_name,
            )

        enhanced_sections = await enhancer.enhance_sections(
            sections_extracted, job_id, on_progress=on_enhance_progress
        )

        # Generate LLM-powered site summary from homepage content
        site_info = await asyncio.to_thread(
            _build_site_info, url, extracted_pages, llm_client, job_id
        )

        # Phase 5: Assembly
        task.update_job_status(job_id, JobStatus.GENERATING)
        task.publish_progress(
            job_id,
            JobStatus.GENERATING,
            "Building llms.txt...",
        )

        builder = LlmsTxtBuilder()

        if config.mode == JobMode.DETAILED:
            # Detailed mode: build llms-full.txt (full page content) as the main output
            sections_raw = categorizer.categorize(extracted_pages)
            llms_txt = builder.build_full(site_info, sections_raw)
            structured_sections = {name: [] for name in sections_raw}
        else:
            # Default mode: build curated index (max 5 entries/section)
            llms_txt, structured_sections = builder.build_index(
                site_info, enhanced_sections, max_per_section=5
            )

        # Phase 6: Polish pass (both modes)
        task.publish_progress(
            job_id,
            JobStatus.GENERATING,
            "Polishing final output...",
        )

        try:
            llms_txt = await asyncio.to_thread(llm_client.polish_llms_txt, llms_txt, job_id)
        except Exception:
            logger.warning("LLM polish pass failed, using unpolished output", exc_info=True)

        successful = pages_with_content
        failed = [p for p in extracted_pages if p.error]

        # LLM calls: 1 per section (batch) + 1 site summary + 1 polish
        section_count = len([s for s in sections_extracted.values() if s])
        llm_calls = section_count + 2
        estimated_cost = llm_calls * 0.0005

        return LlmsTxtResult(
            llms_txt=llms_txt,
            llms_full_txt=None,
            site_info=site_info,
            sections=structured_sections,
            total_pages=len(pages),
            pages_processed=len(successful),
            pages_failed=len(failed),
            llm_calls_made=llm_calls,
            llm_cost_usd=estimated_cost,
        )
    finally:
        await http_client.close()


def _build_site_info(
    url: str,
    pages: list[ExtractedPage],
    llm_client: Any,
    trace_id: str,
) -> SiteInfo:
    """Build SiteInfo using LLM to generate summary and notes from homepage content."""
    from apps.ai.llm_client import LLMClient

    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    name = domain.split(".")[0].title()

    # Find homepage content for the summary
    homepage_content = ""
    fallback_description = None
    for page in pages:
        if page.url.rstrip("/") == url.rstrip("/"):
            homepage_content = page.content_text or ""
            fallback_description = page.description or page.og_description
            break

    if not homepage_content:
        for page in pages:
            if page.content_text:
                homepage_content = page.content_text
                fallback_description = page.description or page.og_description
                break

    # Use LLM if we have content; otherwise fall back to meta description
    if homepage_content and isinstance(llm_client, LLMClient):
        try:
            return llm_client.generate_site_summary(url, name, homepage_content, trace_id)
        except Exception:
            logger.warning("LLM site summary failed, using fallback", exc_info=True)

    return SiteInfo(name=name, url=url, description=fallback_description)

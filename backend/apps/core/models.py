"""Pydantic data models for the generation pipeline.

All internal data passing uses these models -- never raw dicts.
Django ORM models are in apps/jobs/models.py.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class JobMode(enum.StrEnum):
    DEFAULT = "default"
    DETAILED = "detailed"


class JobStatus(enum.StrEnum):
    PENDING = "pending"
    DISCOVERING = "discovering"
    EXTRACTING = "extracting"
    ENHANCING = "enhancing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Configuration models
# ---------------------------------------------------------------------------


class CrawlConfig(BaseModel):
    max_urls: int = Field(default=50, ge=1, le=100)
    max_depth: int = Field(default=2, ge=1, le=3)
    crawl_delay_ms: int = Field(default=300, ge=0)
    timeout_seconds: int = Field(default=30, ge=5, le=60)
    respect_robots_txt: bool = True


class BrowserConfig(BaseModel):
    headless: bool = True
    block_images: bool = True
    block_fonts: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: str = "SpongeBot/1.0 (+https://sponge.dev/bot)"


class AIConfig(BaseModel):
    model: str = "gpt-4o-mini"
    max_content_chars: int = 3000
    temperature: float = 0.3
    max_tokens: int = 150
    max_concurrent_llm_calls: int = 10


class RateLimitConfig(BaseModel):
    anonymous_daily_limit: int = 10
    authenticated_daily_limit: int = 25
    per_domain_requests_per_second: float = 2.0


class GenerationConfig(BaseModel):
    mode: JobMode
    crawl: CrawlConfig = CrawlConfig()
    browser: BrowserConfig = BrowserConfig()
    ai: AIConfig = AIConfig()


# ---------------------------------------------------------------------------
# Pipeline data models -- what flows between stages
# ---------------------------------------------------------------------------


class RobotsResult(BaseModel):
    sitemap_urls: list[str] = []
    crawl_delay: float | None = None
    disallowed_paths: list[str] = []


class SitemapEntry(BaseModel):
    url: str
    lastmod: datetime | None = None
    priority: float | None = None


class SitemapResult(BaseModel):
    entries: list[SitemapEntry] = []
    source: str  # "robots.txt", "/sitemap.xml", "crawled"


class DiscoveredPage(BaseModel):
    url: str
    source: str  # "sitemap" | "crawl" | "homepage"
    depth: int = 0


class CSRDetection(BaseModel):
    """Result of client-side rendering detection."""

    is_csr: bool = False
    has_useful_meta: bool = False


class ExtractedPage(BaseModel):
    url: str
    title: str | None = None
    description: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_type: str | None = None
    og_image: str | None = None
    content_text: str | None = None
    is_js_rendered: bool = False
    fetch_status: int = 200
    error: str | None = None


class EnhancedPage(BaseModel):
    """An ExtractedPage after AI enhancement."""

    url: str
    title: str
    description: str
    section_hint: str | None = None


class EnhancedPageDescription(BaseModel):
    """Raw LLM output for a single page."""

    title: str
    description: str


class RenderedPage(BaseModel):
    """Output from a BrowserProvider."""

    url: str
    html: str
    title: str | None = None
    status: int = 200
    error: str | None = None


class ValidatedURL(BaseModel):
    """A URL that has passed SSRF validation."""

    url: str
    resolved_ip: str


# ---------------------------------------------------------------------------
# Categorization models
# ---------------------------------------------------------------------------


class CategorizationRule(BaseModel):
    section_name: str
    path_patterns: list[str]
    priority: int = 0


class LlmsTxtEntry(BaseModel):
    title: str
    url: str
    description: str | None = None


class LlmsTxtSection(BaseModel):
    name: str
    entries: list[LlmsTxtEntry] = []
    is_optional: bool = False


class SiteInfo(BaseModel):
    name: str
    url: str
    description: str | None = None
    notes: list[str] | None = None


class LlmsTxtResult(BaseModel):
    llms_txt: str
    llms_full_txt: str | None = None
    site_info: SiteInfo
    sections: list[LlmsTxtSection] = []
    total_pages: int = 0
    pages_processed: int = 0
    pages_failed: int = 0
    generation_time_seconds: float = 0.0
    llm_calls_made: int = 0
    llm_cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Progress events -- published to Redis
# ---------------------------------------------------------------------------


class ProgressEvent(BaseModel):
    job_id: str
    phase: JobStatus
    message: str
    urls_found: int | None = None
    completed: int | None = None
    total: int | None = None
    current_url: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RateLimitResult(BaseModel):
    allowed: bool
    remaining: int = 0
    reset_at: datetime | None = None

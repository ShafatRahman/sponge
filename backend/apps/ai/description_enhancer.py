"""Batch LLM description enhancement with concurrency control and fallback."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from apps.core.models import EnhancedPage, ExtractedPage

if TYPE_CHECKING:
    from apps.ai.llm_client import LLMClient
    from apps.core.models import AIConfig

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], Coroutine[Any, Any, None]]


class DescriptionEnhancer:
    """Enhances page descriptions using LLM with concurrency control.

    Features:
    - Section-aware batch processing (one LLM call per section)
    - Per-page content cleaning for Detailed mode
    - Graceful degradation: falls back to raw meta tags on LLM failure
    - Progress tracking via callback
    """

    def __init__(self, llm_client: LLMClient, config: AIConfig) -> None:
        self._llm_client = llm_client
        self._config = config

    async def enhance_sections(
        self,
        sections: dict[str, list[ExtractedPage]],
        job_id: str,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, list[EnhancedPage]]:
        """Enhance descriptions for pages grouped by section.

        Each section is processed as a single LLM call, giving the model
        cross-page awareness to differentiate similar pages. Sections are
        processed in parallel.

        Args:
            sections: Mapping of section name to pages in that section.
            job_id: Job ID for Langfuse tracing.
            on_progress: Optional callback(completed, total, section_name).

        Returns:
            Mapping of section name to enhanced pages.
        """
        completed = 0
        total = sum(len(pages) for pages in sections.values())

        async def enhance_section(
            section_name: str, pages: list[ExtractedPage]
        ) -> tuple[str, list[EnhancedPage]]:
            nonlocal completed
            try:
                enhanced = await asyncio.to_thread(
                    self._llm_client.generate_section_descriptions,
                    section_name=section_name,
                    pages=pages,
                    trace_id=job_id,
                )
            except Exception as exc:
                logger.warning(
                    "LLM batch enhancement failed for section '%s': %s",
                    section_name,
                    exc,
                )
                enhanced = [
                    EnhancedPage(
                        url=p.url,
                        title=p.title or p.og_title or "Untitled",
                        description=p.description or p.og_description or "",
                    )
                    for p in pages
                ]

            completed += len(pages)
            if on_progress:
                await on_progress(completed, total, section_name)

            return section_name, enhanced

        tasks = [enhance_section(name, pages) for name, pages in sections.items() if pages]
        results = await asyncio.gather(*tasks)
        self._llm_client.flush()

        return dict(results)

    async def clean_page_contents(
        self,
        pages: list[ExtractedPage],
        job_id: str,
        on_progress: ProgressCallback | None = None,
        concurrency: int = 5,
    ) -> dict[str, str]:
        """Clean raw page content using LLM for Detailed mode.

        Each page's raw ``content_text`` is sent through an LLM to strip
        marketing noise, CTAs, logo grids, and testimonials, keeping only
        substantive informational content.

        Args:
            pages: Extracted pages with content_text populated.
            job_id: Job ID for Langfuse tracing.
            on_progress: Optional callback(completed, total, url).
            concurrency: Max parallel LLM calls.

        Returns:
            Mapping of URL -> cleaned content markdown.
        """
        pages_with_content = [p for p in pages if p.content_text]
        sem = asyncio.Semaphore(concurrency)
        completed = 0
        total = len(pages_with_content)

        async def clean_one(page: ExtractedPage) -> tuple[str, str]:
            nonlocal completed
            async with sem:
                try:
                    cleaned = await asyncio.to_thread(
                        self._llm_client.clean_page_content,
                        url=page.url,
                        title=page.title or page.og_title or "Untitled",
                        raw_content=page.content_text or "",
                        trace_id=job_id,
                    )
                except Exception as exc:
                    logger.warning("Content clean failed for %s: %s", page.url, exc)
                    cleaned = page.content_text or ""

                completed += 1
                if on_progress:
                    await on_progress(completed, total, page.url)

                return page.url, cleaned

        tasks = [clean_one(p) for p in pages_with_content]
        task_results = await asyncio.gather(*tasks)
        self._llm_client.flush()

        return dict(task_results)

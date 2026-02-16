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
        total_sections = len(sections)

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

        tasks = [
            enhance_section(name, pages) for name, pages in sections.items() if pages
        ]
        results = await asyncio.gather(*tasks)
        self._llm_client.flush()

        return dict(results)

    async def enhance_batch(
        self,
        pages: list[ExtractedPage],
        job_id: str,
        on_progress: ProgressCallback | None = None,
    ) -> list[EnhancedPage]:
        """Enhance descriptions for a batch of pages with concurrency control.

        Args:
            pages: Pages to enhance.
            job_id: Job ID for Langfuse tracing.
            on_progress: Optional callback(completed, total, url).

        Returns:
            List of EnhancedPage with LLM-generated or fallback descriptions.
        """
        semaphore = asyncio.Semaphore(self._config.max_concurrent_llm_calls)
        completed = 0
        total = len(pages)

        async def enhance_one(page: ExtractedPage) -> EnhancedPage:
            nonlocal completed
            async with semaphore:
                result = await self._enhance_single(page, job_id)
                completed += 1
                if on_progress:
                    await on_progress(completed, total, page.url)
                return result

        results = await asyncio.gather(*[enhance_one(p) for p in pages])
        self._llm_client.flush()
        return list(results)

    async def _enhance_single(
        self,
        page: ExtractedPage,
        job_id: str,
    ) -> EnhancedPage:
        """Enhance a single page, with fallback on error."""
        try:
            desc = await asyncio.to_thread(
                self._llm_client.generate_description,
                url=page.url,
                content=page.content_text or "",
                trace_id=job_id,
            )
            return EnhancedPage(
                url=page.url,
                title=desc.title,
                description=desc.description,
            )
        except Exception as exc:
            logger.warning("LLM enhancement failed for %s: %s", page.url, exc)
            return EnhancedPage(
                url=page.url,
                title=page.title or page.og_title or "Untitled",
                description=page.description or page.og_description or "",
            )

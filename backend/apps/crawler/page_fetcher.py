"""Smart page fetcher: HTTP-first with automatic Playwright fallback for CSR pages."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from apps.core.models import BrowserConfig, DiscoveredPage, ExtractedPage

if TYPE_CHECKING:
    from apps.core.http_client import HttpClient
    from apps.extractor.content_extractor import ContentExtractor
    from apps.extractor.meta_extractor import MetaExtractor

logger = logging.getLogger(__name__)

DEFAULT_CONCURRENCY = 10
DEFAULT_DELAY_MS = 300
BROWSER_CONCURRENCY = 3

ProgressCallback = Callable[[int, int, str], Coroutine[Any, Any, None]]

# Titles/phrases that indicate a soft-404 or error page
_SOFT_404_SIGNALS = [
    "page not found",
    "404 not found",
    "404 error",
    "not found",
    "page doesn't exist",
    "page does not exist",
    "nothing here",
    "this page isn't available",
    "this page could not be found",
    "we couldn't find",
    "no longer available",
    "has been removed",
    "has been moved",
    "does not exist",
    "access denied",
    "forbidden",
    "403 forbidden",
    "you don't have permission",
    "blocked",
    "just a moment",
    "error 404",
    "error 403",
    "error 500",
    "internal server error",
    "service unavailable",
]


def _is_soft_404(page: ExtractedPage) -> bool:
    """Detect pages that returned 200 but are actually error/not-found pages.

    Checks title, description, and a prefix of the body content for known
    error-page phrases.
    """
    fields_to_check = [
        (page.title or "").lower().strip(),
        (page.description or "").lower().strip(),
        (page.content_text or "")[:500].lower(),
    ]
    return any(signal in field for field in fields_to_check for signal in _SOFT_404_SIGNALS)


class SmartPageFetcher:
    """Fetches pages via HTTP first, then falls back to Playwright for CSR pages.

    Pipeline for each page:
    1. HTTP GET via httpx
    2. MetaExtractor: extract title, description, OG tags, detect CSR
    3. ContentExtractor: extract main content as markdown
    4. If CSR detected: re-fetch with Playwright, re-extract meta + content
    """

    def __init__(
        self,
        http_client: HttpClient,
        meta_extractor: MetaExtractor,
        content_extractor: ContentExtractor,
        browser_config: BrowserConfig,
        *,
        concurrency: int = DEFAULT_CONCURRENCY,
        delay_ms: int = DEFAULT_DELAY_MS,
    ) -> None:
        self._http_client = http_client
        self._meta_extractor = meta_extractor
        self._content_extractor = content_extractor
        self._browser_config = browser_config
        self._concurrency = concurrency
        self._delay_ms = delay_ms

    async def fetch_all(
        self,
        pages: list[DiscoveredPage],
        on_progress: ProgressCallback | None = None,
    ) -> list[ExtractedPage]:
        """Fetch and extract all pages with smart CSR fallback.

        1. HTTP-fetch all pages concurrently.
        2. Run meta + content extraction on each response.
        3. Identify CSR pages (is_js_rendered=True).
        4. Re-fetch CSR pages with Playwright and re-extract.
        5. Return merged results.
        """
        total = len(pages)
        completed = 0

        # Step 1 & 2: HTTP fetch + extraction
        semaphore = asyncio.Semaphore(self._concurrency)
        results: list[ExtractedPage] = []

        async def fetch_one(page: DiscoveredPage) -> ExtractedPage:
            nonlocal completed
            async with semaphore:
                extracted = await self._http_fetch_and_extract(page)
                completed += 1

                if on_progress:
                    await on_progress(completed, total, page.url)

                if self._delay_ms > 0:
                    await asyncio.sleep(self._delay_ms / 1000.0)

                return extracted

        tasks = [fetch_one(page) for page in pages]
        results = list(await asyncio.gather(*tasks))

        # Step 3: Identify pages that need browser rendering
        # - CSR pages (detected via meta heuristics)
        # - Pages blocked by the server (403/429 likely means bot detection)
        retry_statuses = {403, 429}
        csr_indices: list[int] = []
        for i, result in enumerate(results):
            needs_browser = (result.is_js_rendered and not result.error) or (
                result.fetch_status in retry_statuses
            )
            if needs_browser:
                csr_indices.append(i)

        if not csr_indices:
            return results

        # Step 4: Re-fetch CSR pages with Playwright
        logger.info(
            "%d of %d pages detected as CSR -- falling back to Playwright",
            len(csr_indices),
            total,
        )

        csr_pages = [pages[i] for i in csr_indices]
        rendered_results = await self._playwright_fetch_batch(
            csr_pages, on_progress, completed, total
        )

        # Step 5: Merge results
        for idx, rendered in zip(csr_indices, rendered_results, strict=False):
            if not rendered.error:
                results[idx] = rendered

        return results

    async def _http_fetch_and_extract(self, page: DiscoveredPage) -> ExtractedPage:
        """HTTP-fetch a single page and extract meta + content."""
        try:
            response = await self._http_client.get(page.url)
            content_type = response.headers.get("content-type", "")

            if "text/html" not in content_type:
                return ExtractedPage(
                    url=page.url,
                    fetch_status=response.status_code,
                    error=f"Non-HTML content type: {content_type}",
                )

            if response.status_code >= 400:
                return ExtractedPage(
                    url=page.url,
                    fetch_status=response.status_code,
                    error=f"HTTP {response.status_code}",
                )

            html = response.text
            extracted = self._meta_extractor.extract(page.url, html)
            extracted.fetch_status = response.status_code

            # Detect soft-404 pages (server returns 200 but content is an error page)
            if _is_soft_404(extracted):
                return ExtractedPage(
                    url=page.url,
                    fetch_status=response.status_code,
                    error="Soft 404: page content indicates an error page",
                )

            # Extract content for both modes (cheap BS4 operation)
            content_text = self._content_extractor.extract(html)
            if content_text:
                extracted.content_text = content_text

            return extracted

        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", page.url, exc)
            return ExtractedPage(
                url=page.url,
                fetch_status=0,
                error=str(exc),
            )

    async def _playwright_fetch_batch(
        self,
        pages: list[DiscoveredPage],
        on_progress: ProgressCallback | None,
        already_completed: int,
        total: int,
    ) -> list[ExtractedPage]:
        """Re-fetch a batch of CSR pages using Playwright."""
        from apps.extractor.playwright_provider import PlaywrightProvider

        browser_provider = PlaywrightProvider(self._browser_config)
        semaphore = asyncio.Semaphore(BROWSER_CONCURRENCY)
        completed = already_completed

        async def render_one(page: DiscoveredPage) -> ExtractedPage:
            nonlocal completed
            async with semaphore:
                try:
                    rendered = await browser_provider.get_page_content(page.url)

                    if rendered.error:
                        logger.warning(
                            "Playwright render failed for %s: %s", page.url, rendered.error
                        )
                        return ExtractedPage(
                            url=page.url,
                            error=rendered.error,
                            fetch_status=rendered.status,
                        )

                    # Re-extract meta and content from rendered HTML
                    extracted = self._meta_extractor.extract(page.url, rendered.html)
                    extracted.is_js_rendered = True
                    extracted.fetch_status = rendered.status

                    content_text = self._content_extractor.extract(rendered.html)
                    if content_text:
                        extracted.content_text = content_text

                    # Check for soft-404 on rendered content too
                    if _is_soft_404(extracted):
                        return ExtractedPage(
                            url=page.url,
                            fetch_status=rendered.status,
                            error="Soft 404: rendered page content indicates an error page",
                        )

                    return extracted

                except Exception as exc:
                    logger.warning("Playwright failed for %s: %s", page.url, exc)
                    return ExtractedPage(
                        url=page.url,
                        error=str(exc),
                        fetch_status=0,
                    )
                finally:
                    completed += 1
                    if on_progress:
                        await on_progress(completed, total, page.url)

        render_tasks = [render_one(p) for p in pages]
        results = await asyncio.gather(*render_tasks, return_exceptions=True)

        extracted: list[ExtractedPage] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Render exception for %s: %s", pages[i].url, result)
                extracted.append(ExtractedPage(url=pages[i].url, error=str(result), fetch_status=0))
            else:
                extracted.append(result)

        await browser_provider.close()
        return extracted

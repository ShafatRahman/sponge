"""BFS link crawler as a fallback when no sitemap is available."""

from __future__ import annotations

import asyncio
import logging
import re
from collections import deque
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from apps.core.models import BrowserConfig, CrawlConfig, DiscoveredPage

if TYPE_CHECKING:
    from apps.core.http_client import HttpClient
    from apps.core.ssrf_protection import SSRFGuard

logger = logging.getLogger(__name__)

SKIP_EXTENSIONS = re.compile(
    r"\.(jpg|jpeg|png|gif|svg|webp|ico|pdf|zip|tar|gz|mp3|mp4|avi|mov|"
    r"woff|woff2|ttf|eot|css|js|xml|rss|atom)$",
    re.IGNORECASE,
)

SKIP_PATH_PATTERNS = re.compile(
    r"(login|signin|signup|register|logout|admin|cart|checkout|account|password|oauth)",
    re.IGNORECASE,
)


def _strip_www(domain: str) -> str:
    """Normalize domain by stripping 'www.' prefix for comparison."""
    return domain.removeprefix("www.")


def _same_site(netloc: str, base_domain: str) -> bool:
    """Check if two domains belong to the same site (www-agnostic)."""
    return _strip_www(netloc) == _strip_www(base_domain)


class LinkCrawler:
    """BFS link crawler that discovers pages by following <a> tags.

    Used as a fallback when no sitemap is available.
    Respects max depth, max URLs, and disallowed paths from robots.txt.
    Falls back to Playwright when HTTP fetches fail (e.g. bot-blocking sites).
    """

    def __init__(
        self,
        http_client: HttpClient,
        ssrf_guard: SSRFGuard,
        config: CrawlConfig,
        browser_config: BrowserConfig | None = None,
    ) -> None:
        self._http_client = http_client
        self._ssrf_guard = ssrf_guard
        self._config = config
        self._browser_config = browser_config

    async def crawl(
        self,
        start_url: str,
        disallowed_paths: list[str] | None = None,
    ) -> list[DiscoveredPage]:
        """BFS crawl from start_url up to max_depth and max_urls."""
        disallowed = disallowed_paths or []
        base_parsed = urlparse(start_url)
        base_domain = base_parsed.netloc

        visited: set[str] = set()
        discovered: list[DiscoveredPage] = []
        queue: deque[tuple[str, int]] = deque()
        queue.append((start_url, 0))

        while queue and len(discovered) < self._config.max_urls:
            url, depth = queue.popleft()

            normalized = self._normalize_url(url)
            if normalized in visited:
                continue
            visited.add(normalized)

            if self._should_skip(normalized, base_domain, disallowed):
                continue

            discovered.append(DiscoveredPage(url=normalized, source="crawl", depth=depth))
            logger.debug("Discovered: %s (depth=%d)", normalized, depth)

            if depth < self._config.max_depth:
                child_urls = await self._extract_links(normalized, base_domain)
                for child_url in child_urls:
                    if child_url not in visited:
                        queue.append((child_url, depth + 1))

            if self._config.crawl_delay_ms > 0:
                await asyncio.sleep(self._config.crawl_delay_ms / 1000.0)

        logger.info("BFS crawl complete: %d pages discovered", len(discovered))
        return discovered

    async def _extract_links(self, url: str, base_domain: str) -> list[str]:
        """Fetch a page and extract same-domain links.

        Tries HTTP first. Falls back to Playwright if HTTP fails and a
        browser config is available (handles bot-blocking and CSR sites).
        """
        html = await self._fetch_html(url)
        if html is None:
            return []

        return self._parse_links(html, url, base_domain)

    async def _fetch_html(self, url: str) -> str | None:
        """Fetch page HTML via HTTP, falling back to Playwright on failure."""
        try:
            text = await self._http_client.get_text(url)
            # If the page has very few links, it might be CSR -- check content
            if self._looks_like_csr(text):
                logger.info("Page looks like CSR, trying Playwright: %s", url)
                rendered = await self._playwright_fetch(url)
                return rendered if rendered else text
            return text
        except Exception:
            logger.debug("HTTP failed for link extraction: %s", url)

        # Playwright fallback for bot-blocked or CSR sites
        rendered = await self._playwright_fetch(url)
        if rendered:
            return rendered

        logger.debug("All fetch methods failed for %s", url)
        return None

    async def _playwright_fetch(self, url: str) -> str | None:
        """Render a page with Playwright and return the HTML."""
        if not self._browser_config:
            return None

        try:
            from apps.extractor.playwright_provider import PlaywrightProvider

            provider = PlaywrightProvider(self._browser_config)
            try:
                result = await provider.get_page_content(url)
                if result.error:
                    logger.debug("Playwright render failed for %s: %s", url, result.error)
                    return None
                logger.info("Playwright rendered %s for link extraction", url)
                return result.html
            finally:
                await provider.close()
        except Exception:
            logger.debug("Playwright unavailable for %s", url, exc_info=True)
            return None

    def _parse_links(self, html: str, base_url: str, base_domain: str) -> list[str]:
        """Parse <a> tags from HTML and return normalized same-domain URLs."""
        soup = BeautifulSoup(html, "html.parser")
        all_anchors = soup.find_all("a", href=True)
        links: list[str] = []

        for tag in all_anchors:
            href = tag["href"]
            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)

            if _same_site(parsed.netloc, base_domain) and parsed.scheme in (
                "http",
                "https",
            ):
                normalized = self._normalize_url(absolute)
                if not SKIP_EXTENSIONS.search(parsed.path):
                    links.append(normalized)

        logger.debug(
            "Parsed %d same-site links from %d <a> tags on %s",
            len(links),
            len(all_anchors),
            base_url,
        )
        return links

    @staticmethod
    def _looks_like_csr(html: str) -> bool:
        """Heuristic: page is likely CSR if the body has very little content."""
        soup = BeautifulSoup(html, "html.parser")
        body = soup.find("body")
        if not body:
            return False
        links = body.find_all("a", href=True)
        text_len = len(body.get_text(strip=True))
        return len(links) < 3 and text_len < 500

    def _normalize_url(self, url: str) -> str:
        """Strip fragments and trailing slashes for deduplication."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized

    def _should_skip(self, url: str, base_domain: str, disallowed: list[str]) -> bool:
        """Check if a URL should be skipped."""
        parsed = urlparse(url)

        if not _same_site(parsed.netloc, base_domain):
            return True

        if SKIP_EXTENSIONS.search(parsed.path):
            return True

        if SKIP_PATH_PATTERNS.search(parsed.path):
            return True

        return any(parsed.path.startswith(path) for path in disallowed)

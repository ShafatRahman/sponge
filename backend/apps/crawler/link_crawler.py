"""BFS link crawler as a fallback when no sitemap is available."""

from __future__ import annotations

import asyncio
import logging
import re
from collections import deque
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from apps.core.models import CrawlConfig, DiscoveredPage

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


class LinkCrawler:
    """BFS link crawler that discovers pages by following <a> tags.

    Used as a fallback when no sitemap is available.
    Respects max depth, max URLs, and disallowed paths from robots.txt.
    """

    def __init__(
        self,
        http_client: HttpClient,
        ssrf_guard: SSRFGuard,
        config: CrawlConfig,
    ) -> None:
        self._http_client = http_client
        self._ssrf_guard = ssrf_guard
        self._config = config

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
        """Fetch a page and extract same-domain links."""
        try:
            text = await self._http_client.get_text(url)
        except Exception:
            logger.debug("Failed to fetch for link extraction: %s", url)
            return []

        soup = BeautifulSoup(text, "html.parser")
        links: list[str] = []

        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            absolute = urljoin(url, href)
            parsed = urlparse(absolute)

            if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
                normalized = self._normalize_url(absolute)
                if not SKIP_EXTENSIONS.search(parsed.path):
                    links.append(normalized)

        return links

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

        if parsed.netloc != base_domain:
            return True

        if SKIP_EXTENSIONS.search(parsed.path):
            return True

        if SKIP_PATH_PATTERNS.search(parsed.path):
            return True

        return any(parsed.path.startswith(path) for path in disallowed)

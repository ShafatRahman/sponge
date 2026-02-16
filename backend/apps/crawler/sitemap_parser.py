"""Recursive sitemap.xml parser supporting sitemap indexes."""

from __future__ import annotations

import contextlib
import json
import logging
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from apps.core.models import SitemapEntry, SitemapResult

if TYPE_CHECKING:
    from apps.core.cache import CacheService
    from apps.core.http_client import HttpClient

logger = logging.getLogger(__name__)

MAX_SITEMAP_ENTRIES = 500
MAX_RECURSION_DEPTH = 3
SITEMAP_CACHE_TTL = 3600


class SitemapParser:
    """Fetches and recursively parses sitemaps (including sitemap indexes).

    Handles:
    - Standard sitemap.xml with <url><loc> entries
    - Sitemap index files with <sitemap><loc> sub-sitemaps
    - Recursive parsing up to MAX_RECURSION_DEPTH levels
    - Caching parsed results in Redis for 1 hour
    """

    def __init__(self, http_client: HttpClient, cache: CacheService | None = None) -> None:
        self._http_client = http_client
        self._cache = cache

    async def parse(
        self,
        base_url: str,
        sitemap_urls: list[str] | None = None,
    ) -> SitemapResult:
        """Parse sitemaps for a base URL.

        Args:
            base_url: The website's base URL.
            sitemap_urls: Explicit sitemap URLs from robots.txt. If empty,
                         tries common paths.

        Returns:
            SitemapResult with discovered page entries.
        """
        # Check cache first
        cache_key = f"sitemap:{base_url}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.info("Using cached sitemap for %s (%d entries)", base_url, len(cached.entries))
            return cached

        urls_to_try = sitemap_urls or []

        if not urls_to_try:
            urls_to_try = [
                urljoin(base_url, "/sitemap.xml"),
                urljoin(base_url, "/sitemap_index.xml"),
            ]

        all_entries: list[SitemapEntry] = []
        source = "sitemap"

        for sitemap_url in urls_to_try:
            entries = await self._parse_sitemap(sitemap_url, depth=0)
            all_entries.extend(entries)
            if all_entries:
                source = sitemap_url
                break

        unique_entries = list({e.url: e for e in all_entries}.values())
        capped = unique_entries[:MAX_SITEMAP_ENTRIES]

        result = SitemapResult(entries=capped, source=source)

        # Cache the result
        self._set_cached(cache_key, result)

        logger.info(
            "Sitemap parsing complete: %d entries from %s",
            len(capped),
            source,
        )
        return result

    def _get_cached(self, key: str) -> SitemapResult | None:
        """Try to get a cached SitemapResult."""
        if self._cache is None:
            return None
        raw = self._cache.get_json(key)
        if raw is None:
            return None
        with contextlib.suppress(Exception):
            return SitemapResult.model_validate(raw)
        return None

    def _set_cached(self, key: str, result: SitemapResult) -> None:
        """Cache a SitemapResult."""
        if self._cache is None:
            return
        with contextlib.suppress(Exception):
            data = json.loads(result.model_dump_json())
            self._cache.set_json(key, data, ttl_seconds=SITEMAP_CACHE_TTL)

    async def _parse_sitemap(self, url: str, depth: int) -> list[SitemapEntry]:
        """Fetch and parse a single sitemap URL, recursing into indexes."""
        if depth >= MAX_RECURSION_DEPTH:
            logger.warning("Max sitemap recursion depth reached at %s", url)
            return []

        logger.debug("Fetching sitemap: %s (depth=%d)", url, depth)
        text = await self._http_client.get_text_safe(url)
        if text is None:
            return []

        soup = BeautifulSoup(text, "lxml-xml")

        # Check if this is a sitemap index
        sitemapindex = soup.find("sitemapindex")
        if sitemapindex:
            return await self._parse_index(soup, depth)

        # Standard sitemap with <url> entries
        return self._parse_urlset(soup)

    async def _parse_index(self, soup: BeautifulSoup, depth: int) -> list[SitemapEntry]:
        """Parse a sitemap index and recursively fetch sub-sitemaps."""
        entries: list[SitemapEntry] = []
        sitemap_tags = soup.find_all("sitemap")

        for tag in sitemap_tags:
            loc = tag.find("loc")
            if loc and loc.text:
                sub_entries = await self._parse_sitemap(loc.text.strip(), depth + 1)
                entries.extend(sub_entries)
                if len(entries) >= MAX_SITEMAP_ENTRIES:
                    break

        return entries

    def _parse_urlset(self, soup: BeautifulSoup) -> list[SitemapEntry]:
        """Parse a standard sitemap <urlset> into SitemapEntry list."""
        entries: list[SitemapEntry] = []
        url_tags = soup.find_all("url")

        for tag in url_tags:
            loc = tag.find("loc")
            if not loc or not loc.text:
                continue

            url = loc.text.strip()
            if not url.startswith(("http://", "https://")):
                continue

            priority_tag = tag.find("priority")
            priority = None
            if priority_tag and priority_tag.text:
                with contextlib.suppress(ValueError):
                    priority = float(priority_tag.text.strip())

            entries.append(SitemapEntry(url=url, priority=priority))

        return entries

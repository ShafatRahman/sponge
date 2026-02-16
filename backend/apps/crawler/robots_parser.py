"""Parse robots.txt to extract sitemap URLs and crawl directives."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from apps.core.models import RobotsResult

if TYPE_CHECKING:
    from apps.core.http_client import HttpClient

logger = logging.getLogger(__name__)


class RobotsParser:
    """Fetches and parses robots.txt for a given domain.

    Extracts:
    - Sitemap URLs (for sitemap discovery)
    - Crawl-delay directive (to respect rate limits)
    - Disallowed paths (for our user-agent or *)
    """

    def __init__(self, http_client: HttpClient) -> None:
        self._http_client = http_client

    async def parse(self, base_url: str) -> RobotsResult:
        """Fetch and parse robots.txt for the given base URL."""
        robots_url = urljoin(base_url, "/robots.txt")
        logger.info("Fetching robots.txt: %s", robots_url)

        text = await self._http_client.get_text_safe(robots_url)
        if text is None:
            logger.info("No robots.txt found for %s", base_url)
            return RobotsResult()

        return self._parse_content(text)

    def _parse_content(self, content: str) -> RobotsResult:
        """Parse robots.txt content into a RobotsResult."""
        sitemap_urls: list[str] = []
        disallowed_paths: list[str] = []
        crawl_delay: float | None = None

        current_agent = None
        applies_to_us = False

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Sitemap directives are global (not agent-specific)
            sitemap_match = re.match(r"^Sitemap:\s*(.+)$", line, re.IGNORECASE)
            if sitemap_match:
                url = sitemap_match.group(1).strip()
                if url:
                    sitemap_urls.append(url)
                continue

            agent_match = re.match(r"^User-agent:\s*(.+)$", line, re.IGNORECASE)
            if agent_match:
                current_agent = agent_match.group(1).strip().lower()
                applies_to_us = current_agent in ("*", "spongebot")
                continue

            if not applies_to_us:
                continue

            disallow_match = re.match(r"^Disallow:\s*(.*)$", line, re.IGNORECASE)
            if disallow_match:
                path = disallow_match.group(1).strip()
                if path:
                    disallowed_paths.append(path)
                continue

            delay_match = re.match(r"^Crawl-delay:\s*(\d+\.?\d*)$", line, re.IGNORECASE)
            if delay_match and crawl_delay is None:
                crawl_delay = float(delay_match.group(1))

        logger.info(
            "Parsed robots.txt: %d sitemaps, %d disallowed, delay=%s",
            len(sitemap_urls),
            len(disallowed_paths),
            crawl_delay,
        )
        return RobotsResult(
            sitemap_urls=sitemap_urls,
            crawl_delay=crawl_delay,
            disallowed_paths=disallowed_paths,
        )

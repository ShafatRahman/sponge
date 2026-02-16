"""HTTP client wrapper with rate limiting and timeouts."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from apps.core.models import CrawlConfig

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "SpongeBot/1.0 (+https://sponge.dev/bot)"
DEFAULT_TIMEOUT = 30


class HttpClient:
    """Async HTTP client with configurable timeouts and rate-limit awareness.

    Wraps httpx.AsyncClient for all outbound requests in the crawler pipeline.
    """

    def __init__(self, config: CrawlConfig | None = None) -> None:
        timeout = config.timeout_seconds if config else DEFAULT_TIMEOUT
        self._timeout = httpx.Timeout(timeout, connect=10.0)
        self._headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=self._headers,
                follow_redirects=True,
                max_redirects=5,
            )
        return self._client

    async def get(self, url: str) -> httpx.Response:
        """Perform a GET request."""
        client = await self._get_client()
        logger.debug("GET %s", url)
        return await client.get(url)

    async def get_text(self, url: str) -> str:
        """Fetch URL and return response text. Raises on HTTP errors."""
        response = await self.get(url)
        response.raise_for_status()
        return response.text

    async def get_text_safe(self, url: str) -> str | None:
        """Fetch URL text, returning None on any error."""
        try:
            return await self.get_text(url)
        except Exception:
            logger.debug("Failed to fetch %s", url, exc_info=True)
            return None

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

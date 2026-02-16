"""Playwright-based headless browser provider."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from playwright.async_api import async_playwright

from apps.core.models import RenderedPage
from apps.extractor.browser_provider import BrowserProvider

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Playwright

    from apps.core.models import BrowserConfig

logger = logging.getLogger(__name__)


class PlaywrightProvider(BrowserProvider):
    """Headless browser rendering using Playwright (Chromium).

    Features:
    - Blocks images and fonts for faster page loads
    - Configurable viewport and user agent
    - Proper cleanup of browser contexts
    """

    def __init__(self, config: BrowserConfig) -> None:
        self._config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def _ensure_browser(self) -> Browser:
        """Lazily initialize Playwright and launch the browser."""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self._config.headless,
            )
            logger.info("Playwright browser launched")
        return self._browser

    async def _create_context(self) -> BrowserContext:
        """Create a new browser context with configured viewport and user agent."""
        browser = await self._ensure_browser()
        context = await browser.new_context(
            viewport={
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            },
            user_agent=self._config.user_agent,
        )

        if self._config.block_images or self._config.block_fonts:
            await context.route(
                "**/*",
                lambda route: self._handle_route(route),
            )

        return context

    async def _handle_route(self, route: object) -> None:
        """Block images and fonts via network interception."""
        request = route.request  # type: ignore[attr-defined]
        resource_type = request.resource_type

        blocked_types = set()
        if self._config.block_images:
            blocked_types.update({"image", "media"})
        if self._config.block_fonts:
            blocked_types.add("font")

        if resource_type in blocked_types:
            await route.abort()  # type: ignore[attr-defined]
        else:
            await route.continue_()  # type: ignore[attr-defined]

    async def get_page_content(self, url: str, timeout: int = 30) -> RenderedPage:
        """Navigate to a URL and return the fully rendered HTML."""
        context = await self._create_context()
        page = await context.new_page()

        try:
            response = await page.goto(
                url,
                wait_until="networkidle",
                timeout=timeout * 1000,
            )

            status = response.status if response else 0
            title = await page.title()
            html = await page.content()

            return RenderedPage(
                url=url,
                html=html,
                title=title if title else None,
                status=status,
            )

        except Exception as exc:
            logger.warning("Playwright failed for %s: %s", url, exc)
            return RenderedPage(
                url=url,
                html="",
                status=0,
                error=str(exc),
            )

        finally:
            await page.close()
            await context.close()

    async def close(self) -> None:
        """Shut down the browser and Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            logger.info("Playwright browser closed")

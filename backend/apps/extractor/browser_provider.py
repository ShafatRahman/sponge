"""Abstract browser provider interface for headless rendering."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.core.models import RenderedPage


class BrowserProvider(ABC):
    """Abstract interface for headless browser rendering.

    Concrete implementations: PlaywrightProvider (local), BrowserlessProvider (future).
    """

    @abstractmethod
    async def get_page_content(self, url: str, timeout: int = 30) -> RenderedPage:
        """Navigate to a URL and return the rendered HTML.

        Args:
            url: The URL to render.
            timeout: Maximum time to wait for page load in seconds.

        Returns:
            RenderedPage with rendered HTML content.
        """

    @abstractmethod
    async def close(self) -> None:
        """Clean up browser resources."""

    async def __aenter__(self) -> BrowserProvider:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

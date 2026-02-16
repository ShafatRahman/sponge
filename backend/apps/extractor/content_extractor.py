"""Content extraction with readability heuristics and markdown conversion."""

from __future__ import annotations

import logging
import re

import html2text
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 5000

REMOVE_SELECTORS = [
    "nav",
    "header",
    "footer",
    "aside",
    "script",
    "style",
    "noscript",
    "iframe",
    "[role='navigation']",
    "[role='banner']",
    "[role='contentinfo']",
    ".nav",
    ".navbar",
    ".header",
    ".footer",
    ".sidebar",
    ".cookie-banner",
    ".cookie-consent",
    ".popup",
    ".modal",
    ".ad",
    ".advertisement",
    "#cookie-banner",
    "#cookie-consent",
]

CONTENT_SELECTORS = [
    "main",
    "article",
    "[role='main']",
    ".content",
    ".post-content",
    ".article-content",
    ".entry-content",
    ".page-content",
    "#content",
    "#main-content",
]


class ContentExtractor:
    """Extracts main content from HTML and converts to clean markdown.

    Uses readability heuristics: looks for <main>, <article>, or common
    content class names. Strips navigation, headers, footers, ads.
    """

    def __init__(self) -> None:
        self._converter = html2text.HTML2Text()
        self._converter.ignore_links = False
        self._converter.ignore_images = True
        self._converter.ignore_emphasis = False
        self._converter.body_width = 0
        self._converter.skip_internal_links = True
        self._converter.single_line_break = True

    def extract(self, html: str) -> str:
        """Extract main content from HTML and return clean markdown.

        Returns:
            Markdown text, capped at MAX_CONTENT_LENGTH characters.
        """
        soup = BeautifulSoup(html, "html.parser")

        self._remove_noise(soup)

        content_element = self._find_content(soup)
        if content_element is None:
            body = soup.find("body")
            content_element = body if body else soup

        html_str = str(content_element)
        markdown = self._converter.handle(html_str)
        cleaned = self._clean_markdown(markdown)

        if len(cleaned) > MAX_CONTENT_LENGTH:
            cleaned = cleaned[:MAX_CONTENT_LENGTH].rsplit("\n", 1)[0]

        return cleaned.strip()

    def _remove_noise(self, soup: BeautifulSoup) -> None:
        """Remove non-content elements from the soup."""
        for selector in REMOVE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()

    def _find_content(self, soup: BeautifulSoup) -> Tag | None:
        """Find the main content element using readability heuristics."""
        for selector in CONTENT_SELECTORS:
            element = soup.select_one(selector)
            if element and len(element.get_text(strip=True)) > 100:
                return element
        return None

    def _clean_markdown(self, text: str) -> str:
        """Clean up markdown output."""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\[edit\]\s*$", "", text, flags=re.MULTILINE | re.IGNORECASE)
        return text.strip()

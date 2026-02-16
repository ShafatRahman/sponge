"""Content extraction with readability heuristics and markdown conversion."""

from __future__ import annotations

import logging
import re

import html2text
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 5000

REMOVE_SELECTORS = [
    # Layout chrome
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
    # Overlays and ads
    ".cookie-banner",
    ".cookie-consent",
    ".popup",
    ".modal",
    ".ad",
    ".advertisement",
    "#cookie-banner",
    "#cookie-consent",
    # CTA / marketing elements
    "button",
    "[type='submit']",
    "[class*='cta']",
    "[class*='social-proof']",
    "[class*='logo-cloud']",
    "[class*='logo-grid']",
    "[class*='logo-bar']",
    "[class*='logo-wall']",
    "[class*='client-logo']",
    "[class*='partner-logo']",
    "[class*='customer-logo']",
    "[class*='trust-badge']",
    "[class*='testimonial']",
    "[class*='banner']",
    "[class*='announcement']",
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

# CTA phrases: lines consisting entirely of one of these are stripped.
_CTA_PHRASES = frozenset(
    {
        "get a demo",
        "get started",
        "sign up",
        "sign in",
        "log in",
        "contact us",
        "learn more",
        "try free",
        "start free",
        "book a demo",
        "request a demo",
        "start now",
        "try now",
        "get in touch",
        "schedule a demo",
        "talk to sales",
        "contact sales",
        "request access",
        "join now",
        "subscribe",
        "try it free",
        "start your free trial",
        "create account",
        "sign up free",
        "get early access",
        "join the waitlist",
        "see pricing",
        "view pricing",
        "read more",
        "see all",
        "see more",
        "show more",
        "see all stories",
        "try agents",
        "watch demo",
        "watch video",
    }
)

# Regex for "Company Logo" lines (e.g. "MongoDB Logo")
_LOGO_LINE_RE = re.compile(r"^[\w\s.&'-]+\s+Logo\s*$", re.IGNORECASE)

# Regex for standalone CTA markdown links: [CTA text](/path)
_CTA_LINK_RE = re.compile(r"^\[([^\]]+)\]\([^)]+\)\s*$")

# Social-proof header patterns ("Used by...", "Trusted by...", etc.)
_SOCIAL_PROOF_RE = re.compile(
    r"^#{0,3}\s*(used|trusted|loved|relied on|chosen|preferred) by\b",
    re.IGNORECASE,
)


class ContentExtractor:
    """Extracts main content from HTML and converts to clean markdown.

    Uses readability heuristics: looks for <main>, <article>, or common
    content class names. Strips navigation, headers, footers, ads.
    Post-processes markdown to remove CTA lines, logo grids, and
    social-proof boilerplate.
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
        cleaned = self._strip_boilerplate(cleaned)

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

    @staticmethod
    def _strip_boilerplate(text: str) -> str:
        """Remove CTA lines, logo lines, and social-proof boilerplate from markdown."""
        lines = text.split("\n")
        cleaned: list[str] = []

        for line in lines:
            stripped = line.strip()
            lower = stripped.lower().rstrip(".")

            # Keep blank lines (collapse later)
            if not stripped:
                cleaned.append(line)
                continue

            # Drop CTA-only lines
            if lower in _CTA_PHRASES:
                continue

            # Drop markdown links whose text is a CTA phrase
            link_match = _CTA_LINK_RE.match(stripped)
            if link_match and link_match.group(1).lower().strip().rstrip(".") in _CTA_PHRASES:
                continue

            # Drop "Company Logo" lines
            if _LOGO_LINE_RE.match(stripped):
                continue

            # Drop social-proof headers ("Used by companies of all sizes")
            if _SOCIAL_PROOF_RE.match(stripped):
                continue

            cleaned.append(line)

        result = "\n".join(cleaned)
        # Collapse runs of 3+ blank lines back to 2
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

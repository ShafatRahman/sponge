"""HTML meta tag extraction using BeautifulSoup."""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from apps.core.models import CSRDetection, ExtractedPage

logger = logging.getLogger(__name__)

MAX_DESCRIPTION_LENGTH = 500


class MetaExtractor:
    """Extracts metadata (title, description, OG tags) from HTML.

    Used by both Default and Detailed modes to extract metadata from HTML.
    """

    def extract(self, url: str, html: str) -> ExtractedPage:
        """Parse HTML and extract metadata into an ExtractedPage."""
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_title(soup)
        description = self._extract_description(soup)
        og_title = self._extract_meta(soup, "og:title")
        og_description = self._extract_meta(soup, "og:description")
        og_type = self._extract_meta(soup, "og:type")
        og_image = self._extract_meta(soup, "og:image")

        csr = self.detect_csr(soup)

        return ExtractedPage(
            url=url,
            title=title,
            description=description,
            og_title=og_title,
            og_description=og_description,
            og_type=og_type,
            og_image=og_image,
            is_js_rendered=csr.is_csr,
        )

    def detect_csr(self, soup: BeautifulSoup) -> CSRDetection:
        """Detect whether a page is client-side rendered.

        Returns a CSRDetection with two fields:
        - is_csr: True if the page content likely requires browser rendering.
        - has_useful_meta: True if <title> and <meta description> are present
          regardless of CSR status (SSR frameworks like Next.js serve meta
          tags even when body content is hydrated client-side).
        """
        title = self._extract_title(soup)
        description = self._extract_description(soup)
        has_useful_meta = bool(title and description)

        body = soup.find("body")
        if body is None:
            return CSRDetection(is_csr=True, has_useful_meta=has_useful_meta)

        body_text = body.get_text(strip=True)

        # Plenty of visible text means SSR -- not CSR regardless of framework markers
        if len(body_text) > 200:
            return CSRDetection(is_csr=False, has_useful_meta=has_useful_meta)

        # Sparse body: check for SPA framework markers

        # Next.js SSR: renders meta tags and often has __next div with content.
        # If meta is present, treat as SSR even if body text is sparse (e.g. image-heavy pages).
        next_div = soup.find("div", id="__next")
        if next_div and has_useful_meta:
            return CSRDetection(is_csr=False, has_useful_meta=True)

        # React SPA: empty #root or #app div, typically no meta tags
        root_div = soup.find("div", id="root") or soup.find("div", id="app")
        if root_div and len(root_div.get_text(strip=True)) < 50:
            return CSRDetection(is_csr=True, has_useful_meta=has_useful_meta)

        # <noscript> tag with sparse body is a strong CSR signal
        noscript = soup.find("noscript")
        if noscript and len(body_text) < 100:
            return CSRDetection(is_csr=True, has_useful_meta=has_useful_meta)

        # Body contains only script tags and a single empty div
        children = [c for c in body.children if getattr(c, "name", None)]
        non_script_children = [c for c in children if c.name not in ("script", "style", "link")]
        if len(non_script_children) <= 1 and len(body_text) < 50:
            return CSRDetection(is_csr=True, has_useful_meta=has_useful_meta)

        return CSRDetection(is_csr=False, has_useful_meta=has_useful_meta)

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        """Extract page title from <title> or first <h1>."""
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()

        h1_tag = soup.find("h1")
        if h1_tag:
            return h1_tag.get_text(strip=True)

        return None

    def _extract_description(self, soup: BeautifulSoup) -> str | None:
        """Extract description from meta tag or first paragraph."""
        desc = self._extract_meta(soup, "description", name_attr="name")
        if desc:
            return desc[:MAX_DESCRIPTION_LENGTH]

        og_desc = self._extract_meta(soup, "og:description")
        if og_desc:
            return og_desc[:MAX_DESCRIPTION_LENGTH]

        first_p = soup.find("p")
        if first_p:
            text = first_p.get_text(strip=True)
            if len(text) > 20:
                return text[:MAX_DESCRIPTION_LENGTH]

        return None

    def _extract_meta(
        self,
        soup: BeautifulSoup,
        value: str,
        name_attr: str = "property",
    ) -> str | None:
        """Extract content from a <meta> tag."""
        tag = soup.find("meta", attrs={name_attr: value})
        if tag is None:
            tag = soup.find("meta", attrs={"name": value})
        if tag and tag.get("content"):
            return tag["content"].strip()
        return None

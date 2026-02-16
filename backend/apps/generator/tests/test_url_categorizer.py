"""Tests for URL categorization into llms.txt sections."""

from __future__ import annotations

from apps.core.models import ExtractedPage
from apps.generator.url_categorizer import URLCategorizer


def _page(url: str, title: str = "Page") -> ExtractedPage:
    """Helper to create a minimal ExtractedPage."""
    return ExtractedPage(url=url, title=title)


def _error_page(url: str) -> ExtractedPage:
    return ExtractedPage(url=url, error="fetch failed", fetch_status=500)


class TestURLCategorizer:
    """Test pattern-based URL categorization."""

    def setup_method(self) -> None:
        self.categorizer = URLCategorizer()

    def test_categorizes_docs_path(self) -> None:
        pages = [_page("https://example.com/docs/getting-started")]
        sections = self.categorizer.categorize(pages)
        assert "Documentation" in sections
        assert len(sections["Documentation"]) == 1

    def test_categorizes_documentation_path(self) -> None:
        pages = [_page("https://example.com/documentation/api")]
        sections = self.categorizer.categorize(pages)
        assert "Documentation" in sections

    def test_categorizes_api_reference(self) -> None:
        pages = [_page("https://example.com/api/v2/users")]
        sections = self.categorizer.categorize(pages)
        assert "API Reference" in sections

    def test_categorizes_guides(self) -> None:
        pages = [_page("https://example.com/tutorials/intro")]
        sections = self.categorizer.categorize(pages)
        assert "Guides" in sections

    def test_categorizes_blog(self) -> None:
        pages = [_page("https://example.com/blog/new-release")]
        sections = self.categorizer.categorize(pages)
        assert "Blog" in sections

    def test_categorizes_about(self) -> None:
        pages = [_page("https://example.com/about")]
        sections = self.categorizer.categorize(pages)
        assert "About" in sections

    def test_categorizes_pricing(self) -> None:
        pages = [_page("https://example.com/pricing")]
        sections = self.categorizer.categorize(pages)
        assert "Pricing" in sections

    def test_categorizes_legal_as_optional(self) -> None:
        pages = [
            _page("https://example.com/privacy"),
            _page("https://example.com/terms"),
        ]
        sections = self.categorizer.categorize(pages)
        assert "Optional" in sections
        assert len(sections["Optional"]) == 2

    def test_fallback_uses_first_segment(self) -> None:
        pages = [_page("https://example.com/solutions/enterprise")]
        sections = self.categorizer.categorize(pages)
        assert "Solutions" in sections

    def test_root_path_falls_back_to_pages(self) -> None:
        pages = [_page("https://example.com/")]
        sections = self.categorizer.categorize(pages)
        assert "Pages" in sections

    def test_skips_error_pages(self) -> None:
        pages = [
            _error_page("https://example.com/docs/broken"),
            _page("https://example.com/docs/works"),
        ]
        sections = self.categorizer.categorize(pages)
        assert "Documentation" in sections
        assert len(sections["Documentation"]) == 1

    def test_case_insensitive_matching(self) -> None:
        pages = [_page("https://example.com/DOCS/intro")]
        sections = self.categorizer.categorize(pages)
        assert "Documentation" in sections

    def test_multiple_sections(self) -> None:
        pages = [
            _page("https://example.com/docs/intro"),
            _page("https://example.com/blog/post-1"),
            _page("https://example.com/about"),
        ]
        sections = self.categorizer.categorize(pages)
        assert len(sections) == 3
        assert "Documentation" in sections
        assert "Blog" in sections
        assert "About" in sections

    def test_empty_input(self) -> None:
        sections = self.categorizer.categorize([])
        assert sections == {}

    def test_getting_started_is_guide(self) -> None:
        pages = [_page("https://example.com/getting-started")]
        sections = self.categorizer.categorize(pages)
        assert "Guides" in sections

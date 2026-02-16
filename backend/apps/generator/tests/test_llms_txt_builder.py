"""Tests for spec-compliant llms.txt and llms-full.txt builder."""

from __future__ import annotations

from apps.core.models import EnhancedPage, ExtractedPage, SiteInfo
from apps.generator.llms_txt_builder import LlmsTxtBuilder


def _site() -> SiteInfo:
    return SiteInfo(name="Acme Corp", url="https://acme.com", description="Building the future")


def _page(url: str, title: str, description: str | None = None) -> ExtractedPage:
    return ExtractedPage(url=url, title=title, description=description)


class TestBuildIndex:
    """Test llms.txt index file generation."""

    def setup_method(self) -> None:
        self.builder = LlmsTxtBuilder()

    def test_header_contains_site_name(self) -> None:
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {}
        txt, _ = self.builder.build_index(_site(), sections)
        assert txt.startswith("# Acme Corp\n")

    def test_header_contains_blockquote_description(self) -> None:
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {}
        txt, _ = self.builder.build_index(_site(), sections)
        assert "> Building the future" in txt

    def test_no_description_omits_blockquote(self) -> None:
        site = SiteInfo(name="Acme", url="https://acme.com")
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {}
        txt, _ = self.builder.build_index(site, sections)
        assert ">" not in txt

    def test_section_headers_rendered(self) -> None:
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {
            "Documentation": [_page("https://acme.com/docs", "Docs", "Main docs")],
        }
        txt, _ = self.builder.build_index(_site(), sections)
        assert "## Documentation" in txt

    def test_entries_are_markdown_links(self) -> None:
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {
            "Documentation": [_page("https://acme.com/docs", "Docs", "Main docs")],
        }
        txt, _ = self.builder.build_index(_site(), sections)
        assert "- [Docs](https://acme.com/docs): Main docs" in txt

    def test_entries_without_description(self) -> None:
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {
            "Pages": [_page("https://acme.com/about", "About")],
        }
        txt, _ = self.builder.build_index(_site(), sections)
        assert "- [About](https://acme.com/about)" in txt
        assert ": " not in txt.split("About](https://acme.com/about)")[1].split("\n")[0]

    def test_structured_sections_returned(self) -> None:
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {
            "Documentation": [_page("https://acme.com/docs", "Docs", "Main docs")],
            "Blog": [_page("https://acme.com/blog", "Blog")],
        }
        _, structured = self.builder.build_index(_site(), sections)
        assert len(structured) == 2
        names = [s.name for s in structured]
        assert "Documentation" in names
        assert "Blog" in names

    def test_optional_section_last(self) -> None:
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {
            "Optional": [_page("https://acme.com/privacy", "Privacy")],
            "Documentation": [_page("https://acme.com/docs", "Docs")],
        }
        _, structured = self.builder.build_index(_site(), sections)
        assert structured[-1].name == "Optional"
        assert structured[-1].is_optional is True

    def test_enhanced_pages_use_enhanced_title(self) -> None:
        enhanced = EnhancedPage(
            url="https://acme.com/docs",
            title="Enhanced Docs Title",
            description="AI-generated description",
        )
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {
            "Documentation": [enhanced],
        }
        txt, _ = self.builder.build_index(_site(), sections)
        assert "[Enhanced Docs Title]" in txt
        assert "AI-generated description" in txt

    def test_output_ends_with_newline(self) -> None:
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {}
        txt, _ = self.builder.build_index(_site(), sections)
        assert txt.endswith("\n")


class TestBuildFull:
    """Test llms-full.txt expanded content generation."""

    def setup_method(self) -> None:
        self.builder = LlmsTxtBuilder()

    def test_includes_content_text(self) -> None:
        page = _page("https://acme.com/docs", "Docs")
        page.content_text = "This is the full docs content."
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {
            "Documentation": [page],
        }
        txt = self.builder.build_full(_site(), sections)
        assert "This is the full docs content." in txt

    def test_includes_source_url(self) -> None:
        page = _page("https://acme.com/docs", "Docs")
        page.content_text = "Content here"
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {
            "Documentation": [page],
        }
        txt = self.builder.build_full(_site(), sections)
        assert "Source: https://acme.com/docs" in txt

    def test_h3_per_page(self) -> None:
        page = _page("https://acme.com/docs", "Docs Guide")
        page.content_text = "Content"
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {
            "Documentation": [page],
        }
        txt = self.builder.build_full(_site(), sections)
        assert "### Docs Guide" in txt

    def test_no_content_shows_description(self) -> None:
        page = _page("https://acme.com/about", "About", "About Acme Corp")
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {
            "About": [page],
        }
        txt = self.builder.build_full(_site(), sections)
        assert "About Acme Corp" in txt

    def test_no_content_no_description_shows_placeholder(self) -> None:
        page = _page("https://acme.com/empty", "Empty")
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {
            "Pages": [page],
        }
        txt = self.builder.build_full(_site(), sections)
        assert "(No content available)" in txt

    def test_sections_separated_by_hr(self) -> None:
        page = _page("https://acme.com/docs", "Docs")
        page.content_text = "Content"
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {
            "Documentation": [page],
        }
        txt = self.builder.build_full(_site(), sections)
        assert "---" in txt

    def test_output_ends_with_newline(self) -> None:
        sections: dict[str, list[ExtractedPage | EnhancedPage]] = {}
        txt = self.builder.build_full(_site(), sections)
        assert txt.endswith("\n")

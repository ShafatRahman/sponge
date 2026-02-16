"""Tests for HTML meta tag extraction."""

from __future__ import annotations

from apps.extractor.meta_extractor import MetaExtractor


def _html(
    title: str = "",
    meta_desc: str = "",
    og_title: str = "",
    og_desc: str = "",
    og_type: str = "",
    og_image: str = "",
    body: str = "<p>Some content paragraph here for testing.</p>",
    noscript: bool = False,
    js_root: bool = False,
) -> str:
    """Build a minimal HTML document with specified meta tags."""
    parts = ["<html><head>"]
    if title:
        parts.append(f"<title>{title}</title>")
    if meta_desc:
        parts.append(f'<meta name="description" content="{meta_desc}">')
    if og_title:
        parts.append(f'<meta property="og:title" content="{og_title}">')
    if og_desc:
        parts.append(f'<meta property="og:description" content="{og_desc}">')
    if og_type:
        parts.append(f'<meta property="og:type" content="{og_type}">')
    if og_image:
        parts.append(f'<meta property="og:image" content="{og_image}">')
    parts.append("</head><body>")
    if js_root:
        parts.append('<div id="root"></div>')
    else:
        parts.append(body)
    if noscript:
        parts.append("<noscript>Enable JS</noscript>")
    parts.append("</body></html>")
    return "".join(parts)


class TestMetaExtractor:
    """Test HTML metadata extraction."""

    def setup_method(self) -> None:
        self.extractor = MetaExtractor()

    def test_extracts_title_from_tag(self) -> None:
        page = self.extractor.extract("https://ex.com", _html(title="My Page"))
        assert page.title == "My Page"

    def test_extracts_title_from_h1_when_no_title_tag(self) -> None:
        html = "<html><head></head><body><h1>Heading Title</h1></body></html>"
        page = self.extractor.extract("https://ex.com", html)
        assert page.title == "Heading Title"

    def test_title_none_when_missing(self) -> None:
        html = "<html><head></head><body><p>No title here</p></body></html>"
        page = self.extractor.extract("https://ex.com", html)
        assert page.title is None

    def test_extracts_meta_description(self) -> None:
        page = self.extractor.extract("https://ex.com", _html(meta_desc="A great website"))
        assert page.description == "A great website"

    def test_falls_back_to_og_description(self) -> None:
        page = self.extractor.extract("https://ex.com", _html(og_desc="OG fallback desc"))
        assert page.description == "OG fallback desc"

    def test_falls_back_to_first_paragraph(self) -> None:
        html = (
            "<html><head></head><body>"
            "<p>This is a long enough paragraph for testing extraction.</p>"
            "</body></html>"
        )
        page = self.extractor.extract("https://ex.com", html)
        assert page.description is not None
        assert "long enough paragraph" in page.description

    def test_short_paragraph_ignored(self) -> None:
        html = "<html><head></head><body><p>Short</p></body></html>"
        page = self.extractor.extract("https://ex.com", html)
        assert page.description is None

    def test_description_truncated_at_max_length(self) -> None:
        long_desc = "x" * 600
        page = self.extractor.extract("https://ex.com", _html(meta_desc=long_desc))
        assert page.description is not None
        assert len(page.description) <= 500

    def test_extracts_og_title(self) -> None:
        page = self.extractor.extract("https://ex.com", _html(og_title="OG Title"))
        assert page.og_title == "OG Title"

    def test_extracts_og_description(self) -> None:
        page = self.extractor.extract("https://ex.com", _html(og_desc="OG Description"))
        assert page.og_description == "OG Description"

    def test_extracts_og_type(self) -> None:
        page = self.extractor.extract("https://ex.com", _html(og_type="website"))
        assert page.og_type == "website"

    def test_extracts_og_image(self) -> None:
        page = self.extractor.extract("https://ex.com", _html(og_image="https://ex.com/img.png"))
        assert page.og_image == "https://ex.com/img.png"

    def test_detects_js_rendered_noscript(self) -> None:
        page = self.extractor.extract(
            "https://ex.com",
            _html(body="", noscript=True),
        )
        assert page.is_js_rendered is True

    def test_detects_js_rendered_root_div(self) -> None:
        page = self.extractor.extract(
            "https://ex.com",
            _html(js_root=True),
        )
        assert page.is_js_rendered is True

    def test_not_js_rendered_with_content(self) -> None:
        page = self.extractor.extract("https://ex.com", _html())
        assert page.is_js_rendered is False

    def test_url_preserved(self) -> None:
        page = self.extractor.extract("https://example.com/page", _html(title="Test"))
        assert page.url == "https://example.com/page"

    def test_missing_og_tags_are_none(self) -> None:
        page = self.extractor.extract("https://ex.com", _html(title="Only title"))
        assert page.og_title is None
        assert page.og_description is None
        assert page.og_type is None
        assert page.og_image is None

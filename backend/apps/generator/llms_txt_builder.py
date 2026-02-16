"""Spec-compliant llms.txt and llms-full.txt builder."""

from __future__ import annotations

from apps.core.models import (
    EnhancedPage,
    ExtractedPage,
    LlmsTxtEntry,
    LlmsTxtSection,
    SiteInfo,
)


class LlmsTxtBuilder:
    """Assembles spec-compliant llms.txt and llms-full.txt files.

    Follows the llmstxt.org specification:
    - H1 with site name
    - Blockquote with site description
    - H2 section headers
    - Markdown links with optional descriptions
    - "Optional" section for legal/boilerplate pages
    """

    def build_index(
        self,
        site_info: SiteInfo,
        sections: dict[str, list[ExtractedPage | EnhancedPage]],
        max_per_section: int | None = None,
    ) -> tuple[str, list[LlmsTxtSection]]:
        """Build the llms.txt index file (both Default and Detailed modes).

        Args:
            site_info: Site metadata including name, description, and notes.
            sections: Categorized pages.
            max_per_section: If set, limit entries per section (Default mode
                produces a curated index; Detailed includes everything).

        Returns:
            Tuple of (llms_txt_content, structured_sections).
        """
        lines: list[str] = []
        structured_sections: list[LlmsTxtSection] = []

        lines.append(f"# {site_info.name}")
        lines.append("")

        if site_info.description:
            lines.append(f"> {site_info.description}")
            lines.append("")

        if site_info.notes:
            for note in site_info.notes:
                lines.append(f"- {note}")
            lines.append("")

        ordered_sections = self._order_sections(sections)

        for section_name, pages in ordered_sections:
            is_optional = section_name == "Optional"
            section_entries: list[LlmsTxtEntry] = []

            # Curate: limit entries per section when max_per_section is set
            display_pages = pages
            if max_per_section and len(pages) > max_per_section:
                display_pages = pages[:max_per_section]

            lines.append(f"## {section_name}")
            lines.append("")

            for page in display_pages:
                title = self._get_title(page)
                description = self._get_description(page)
                url = page.url

                if description:
                    lines.append(f"- [{title}]({url}): {description}")
                else:
                    lines.append(f"- [{title}]({url})")

                section_entries.append(LlmsTxtEntry(title=title, url=url, description=description))

            lines.append("")
            structured_sections.append(
                LlmsTxtSection(
                    name=section_name,
                    entries=section_entries,
                    is_optional=is_optional,
                )
            )

        return "\n".join(lines).strip() + "\n", structured_sections

    def build_full(
        self,
        site_info: SiteInfo,
        sections: dict[str, list[ExtractedPage | EnhancedPage]],
    ) -> str:
        """Build the llms-full.txt expanded content file (Detailed mode only).

        Each page's full content is inlined under its section heading.
        """
        lines: list[str] = []

        lines.append(f"# {site_info.name}")
        lines.append("")

        if site_info.description:
            lines.append(f"> {site_info.description}")
            lines.append("")

        if site_info.notes:
            for note in site_info.notes:
                lines.append(f"- {note}")
            lines.append("")

        ordered_sections = self._order_sections(sections)

        for section_name, pages in ordered_sections:
            lines.append(f"## {section_name}")
            lines.append("")

            for page in pages:
                title = self._get_title(page)
                lines.append(f"### {title}")
                lines.append(f"Source: {page.url}")
                lines.append("")

                if page.content_text:
                    lines.append(page.content_text)
                else:
                    description = self._get_description(page)
                    if description:
                        lines.append(description)
                    else:
                        lines.append("(No content available)")

                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines).strip() + "\n"

    def _order_sections(
        self,
        sections: dict[str, list[ExtractedPage | EnhancedPage]],
    ) -> list[tuple[str, list[ExtractedPage | EnhancedPage]]]:
        """Order sections with a preferred order, Optional always last."""
        preferred_order = [
            "Documentation",
            "API Reference",
            "Guides",
            "Features",
            "Blog",
            "Resources",
            "About",
            "Pricing",
            "Pages",
        ]

        ordered: list[tuple[str, list[ExtractedPage | EnhancedPage]]] = []
        remaining = dict(sections)

        for name in preferred_order:
            if name in remaining:
                ordered.append((name, remaining.pop(name)))

        optional = remaining.pop("Optional", None)

        for name in sorted(remaining.keys()):
            ordered.append((name, remaining[name]))

        if optional:
            ordered.append(("Optional", optional))

        return ordered

    def _get_title(self, page: ExtractedPage | EnhancedPage) -> str:
        """Extract the best available title from a page."""
        if isinstance(page, EnhancedPage):
            return page.title

        return page.title or page.og_title or page.url.split("/")[-1] or "Untitled"

    def _get_description(self, page: ExtractedPage | EnhancedPage) -> str | None:
        """Extract the best available description from a page."""
        if isinstance(page, EnhancedPage):
            return page.description

        return page.description or page.og_description

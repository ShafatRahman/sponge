"""URL categorization into llms.txt sections using path pattern matching."""

from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import urlparse

from apps.core.models import CategorizationRule, ExtractedPage


class URLCategorizer:
    """Categorizes pages into llms.txt sections based on URL path patterns.

    Uses a priority-ordered list of rules. Pages that don't match any rule
    are grouped by their first path segment or placed in "Pages".
    """

    DEFAULT_RULES: ClassVar[list[CategorizationRule]] = [
        CategorizationRule(
            section_name="Documentation",
            path_patterns=[r"/docs?(/|$)", r"/documentation(/|$)", r"/manual(/|$)"],
            priority=10,
        ),
        CategorizationRule(
            section_name="API Reference",
            path_patterns=[r"/api(/|$)", r"/reference(/|$)", r"/sdk(/|$)", r"/endpoints?(/|$)"],
            priority=9,
        ),
        CategorizationRule(
            section_name="Guides",
            path_patterns=[
                r"/guides?(/|$)",
                r"/tutorials?(/|$)",
                r"/learn(/|$)",
                r"/how-to(/|$)",
                r"/getting-started(/|$)",
            ],
            priority=8,
        ),
        CategorizationRule(
            section_name="Blog",
            path_patterns=[
                r"/blog(/|$)",
                r"/posts?(/|$)",
                r"/articles?(/|$)",
                r"/news(/|$)",
            ],
            priority=7,
        ),
        CategorizationRule(
            section_name="Features",
            path_patterns=[
                r"/features?(/|$)",
                r"/products?(/|$)",
                r"/solutions?(/|$)",
                r"/platform(/|$)",
                r"/capabilities(/|$)",
            ],
            priority=6,
        ),
        CategorizationRule(
            section_name="About",
            path_patterns=[
                r"/about(/|$)",
                r"/team(/|$)",
                r"/careers?(/|$)",
                r"/contact(/|$)",
                r"/company(/|$)",
                r"/customers?(/|$)",
                r"/case-stud(y|ies)(/|$)",
            ],
            priority=5,
        ),
        CategorizationRule(
            section_name="Resources",
            path_patterns=[
                r"/resources?(/|$)",
                r"/research(/|$)",
                r"/reports?(/|$)",
                r"/webinars?(/|$)",
                r"/events?(/|$)",
                r"/whitepapers?(/|$)",
            ],
            priority=4,
        ),
        CategorizationRule(
            section_name="Pricing",
            path_patterns=[r"/pricing(/|$)", r"/plans?(/|$)"],
            priority=3,
        ),
        CategorizationRule(
            section_name="Optional",
            path_patterns=[
                r"/legal(/|$)",
                r"/privacy[-_]?policy(/|$)",
                r"/privacy(/|$)",
                r"/terms[-_]?(of[-_]?service|of[-_]?use)?(/|$)",
                r"/cookies?[-_]?policy(/|$)",
                r"/cookies?(/|$)",
                r"/tos(/|$)",
                r"/disclaimer(/|$)",
                r"/gdpr(/|$)",
                r"/imprint(/|$)",
                r"/accessibility(/|$)",
            ],
            priority=1,
        ),
    ]

    # URL patterns for pages that should be excluded entirely (not useful content)
    EXCLUDE_PATTERNS: ClassVar[list[str]] = [
        r"/login(/|$)",
        r"/signin(/|$)",
        r"/sign-in(/|$)",
        r"/signup(/|$)",
        r"/sign-up(/|$)",
        r"/register(/|$)",
        r"/auth(/|$)",
        r"/welcome(/|$)",
        r"/password[-_]?reset(/|$)",
        r"/forgot[-_]?password(/|$)",
        r"/unsubscribe(/|$)",
        r"/404(/|$)",
        r"/error(/|$)",
    ]

    # Small sections with fewer entries than this get merged into "Pages"
    MIN_SECTION_SIZE = 2

    def __init__(self, rules: list[CategorizationRule] | None = None) -> None:
        self._rules = rules or self.DEFAULT_RULES
        self._compiled: list[tuple[CategorizationRule, list[re.Pattern[str]]]] = [
            (rule, [re.compile(p, re.IGNORECASE) for p in rule.path_patterns])
            for rule in sorted(self._rules, key=lambda r: r.priority, reverse=True)
        ]
        self._exclude_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.EXCLUDE_PATTERNS
        ]

    def categorize(self, pages: list[ExtractedPage]) -> dict[str, list[ExtractedPage]]:
        """Categorize pages into named sections.

        Returns:
            Dict mapping section names to lists of ExtractedPages.
            Excludes login/auth pages. Merges tiny fallback sections into "Pages".
        """
        sections: dict[str, list[ExtractedPage]] = {}

        for page in pages:
            if page.error:
                continue
            if self._is_excluded(page.url):
                continue

            section = self._match_section(page.url)
            if section not in sections:
                sections[section] = []
            sections[section].append(page)

        return self._consolidate_small_sections(sections)

    def _match_section(self, url: str) -> str:
        """Match a URL to a section name using path patterns."""
        parsed = urlparse(url)
        path = parsed.path.lower()

        for rule, patterns in self._compiled:
            for pattern in patterns:
                if pattern.search(path):
                    return rule.section_name

        return self._fallback_section(path)

    def _is_excluded(self, url: str) -> bool:
        """Check if a URL should be excluded from the output entirely."""
        parsed = urlparse(url)
        path = parsed.path.lower()
        for pattern in self._exclude_compiled:
            if pattern.search(path):
                return True
        return False

    def _consolidate_small_sections(
        self, sections: dict[str, list[ExtractedPage]]
    ) -> dict[str, list[ExtractedPage]]:
        """Merge tiny auto-generated sections into a 'Pages' catch-all.

        Rule-matched sections (Documentation, Blog, etc.) are always kept.
        Fallback sections (auto-generated from URL path) are merged into
        'Pages' if they have fewer than MIN_SECTION_SIZE entries.
        """
        rule_section_names = {rule.section_name for rule in self._rules}
        consolidated: dict[str, list[ExtractedPage]] = {}
        overflow: list[ExtractedPage] = []

        for name, pages in sections.items():
            if name in rule_section_names or len(pages) >= self.MIN_SECTION_SIZE:
                consolidated[name] = pages
            else:
                overflow.extend(pages)

        if overflow:
            if "Pages" in consolidated:
                consolidated["Pages"].extend(overflow)
            else:
                consolidated["Pages"] = overflow

        return consolidated

    def _fallback_section(self, path: str) -> str:
        """Generate a section name from the first path segment."""
        segments = [s for s in path.split("/") if s]
        if not segments:
            return "Pages"

        first = segments[0]
        return first.replace("-", " ").replace("_", " ").title()

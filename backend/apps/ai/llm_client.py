"""OpenAI client with Langfuse observability."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from langfuse import Langfuse
from langfuse.openai import OpenAI as LangfuseOpenAI

from apps.core.models import EnhancedPage, EnhancedPageDescription, SiteInfo

if TYPE_CHECKING:
    from apps.core.models import AIConfig, ExtractedPage

logger = logging.getLogger(__name__)

FALLBACK_SYSTEM_PROMPT = (
    "You write concise titles and descriptions for web pages in an llms.txt file "
    "(see llmstxt.org). The output helps LLMs quickly understand what each page "
    "contains. Respond in JSON format only.\n\n"
    "Rules:\n"
    "- Title: 2-5 word noun phrase. Specific to the page content, not generic.\n"
    "- Description: 8-15 words. State what the page contains or explains, "
    "not what the reader should do.\n"
    "- NEVER start with filler verbs like 'Explore', 'Discover', 'Learn about', "
    "'Find out', 'Check out', 'Dive into', 'Uncover'. Start with the subject.\n"
    "- Be factual and specific. Mention product names, technologies, or topics.\n"
    "- Vary your sentence structure across pages."
)

FALLBACK_USER_PROMPT_TEMPLATE = (
    "Generate a title and description for this web page.\n\n"
    "URL: {url}\n\n"
    "Page content:\n{content}\n\n"
    "Good examples:\n"
    "- {{\"title\": \"Python SDK Reference\", "
    "\"description\": \"Complete API reference for the Python client library.\"}}\n"
    "- {{\"title\": \"Pricing Plans\", "
    "\"description\": \"Three tiers from free to enterprise with usage-based billing.\"}}\n"
    "- {{\"title\": \"HTMX Integration Guide\", "
    "\"description\": \"Step-by-step setup for adding HTMX to a FastHTML project.\"}}\n\n"
    "Bad examples (do NOT produce these):\n"
    "- {{\"title\": \"Explore Our Platform\", "
    "\"description\": \"Discover how our platform can help you.\"}}\n"
    "- {{\"title\": \"Learn More\", "
    "\"description\": \"Explore the latest insights from our team.\"}}\n\n"
    'Respond with:\n{{"title": "...", "description": "..."}}'
)


SITE_SUMMARY_SYSTEM_PROMPT = (
    "You write the summary section for an llms.txt file (see llmstxt.org). "
    "The llms.txt file helps LLMs quickly understand a website.\n\n"
    "You will receive the homepage content of a website. Produce:\n"
    "1. 'description': A 1-2 sentence factual summary of what the site/product IS "
    "and what it does. This becomes the blockquote. Write as if explaining to a "
    "knowledgeable colleague. No marketing language.\n"
    "2. 'notes': A list of 2-5 important bullet points that provide critical context "
    "an LLM would need to understand the site correctly. Include things like: "
    "what technology it uses, what it's NOT (common misconceptions), key limitations, "
    "the target audience, or how the product fits into its ecosystem. "
    "Only include notes if genuinely useful. If the site is too simple or generic "
    "for notes to add value, return an empty list.\n\n"
    "Respond in JSON only."
)

SITE_SUMMARY_USER_TEMPLATE = (
    "Generate the llms.txt summary for this website.\n\n"
    "URL: {url}\n"
    "Site name: {name}\n\n"
    "Homepage content:\n{content}\n\n"
    "Good example output:\n"
    '{{"description": "FastHTML is a Python library that combines Starlette, Uvicorn, '
    "HTMX, and fastcore's FT FastTags for creating server-rendered hypermedia "
    'applications.", "notes": ["Although parts of its API are inspired by FastAPI, '
    "it is not compatible with FastAPI syntax and is not targeted at creating API "
    'services", "FastHTML is compatible with JS-native web components and any vanilla '
    'JS library, but not with React, Vue, or Svelte"]}}\n\n'
    'Respond with:\n{{"description": "...", "notes": ["...", "..."]}}'
)


BATCH_SECTION_SYSTEM_PROMPT = (
    "You write concise titles and descriptions for web pages in an llms.txt file "
    "(see llmstxt.org). You will receive multiple pages from the same section of a "
    "website. Produce a title and description for EACH page.\n\n"
    "Rules:\n"
    "- Title: 2-5 word noun phrase. Specific to the page content, not generic.\n"
    "- Description: 8-15 words. State what the page contains, not what the reader "
    "should do.\n"
    "- NEVER start with filler verbs like 'Explore', 'Discover', 'Learn about'. "
    "Start with the subject.\n"
    "- Differentiate similar pages clearly. If two pages cover related topics, "
    "highlight what makes each one unique.\n"
    "- Vary sentence structure across entries. Do not repeat phrasing patterns.\n"
    "- Be factual and specific. Mention product names, technologies, or topics.\n\n"
    "Respond with a JSON object: {\"pages\": [{\"url\": \"...\", \"title\": \"...\", "
    "\"description\": \"...\"}, ...]}"
)

BATCH_SECTION_USER_TEMPLATE = (
    "Generate titles and descriptions for all pages in the \"{section}\" section.\n\n"
    "{pages_block}\n\n"
    "Respond with:\n"
    "{{\"pages\": [{{\"url\": \"...\", \"title\": \"...\", \"description\": \"...\"}}, ...]}}"
)

POLISH_SYSTEM_PROMPT = (
    "You are an editor for llms.txt files (see llmstxt.org). You will receive a "
    "complete llms.txt file and must return an improved version.\n\n"
    "Your job:\n"
    "1. Refine the blockquote (> line) for accuracy and completeness.\n"
    "2. Improve the bullet-point notes if present. Remove any that are not genuinely "
    "useful. Add important context if missing.\n"
    "3. Ensure descriptions are consistent in tone, varied in phrasing, and free of "
    "filler verbs (Explore, Discover, Learn, etc.).\n"
    "4. Reorder entries within sections by importance if beneficial.\n"
    "5. Ensure strict compliance with the llmstxt.org format:\n"
    "   - H1 with site name\n"
    "   - Blockquote with description\n"
    "   - Optional bullet notes\n"
    "   - H2 sections with markdown link lists\n"
    "   - Optional section last\n"
    "6. Do NOT add or remove pages. Do NOT change URLs. Only improve titles, "
    "descriptions, blockquote, notes, and ordering.\n\n"
    "Return ONLY the improved llms.txt content as plain markdown. No JSON wrapper."
)

POLISH_USER_TEMPLATE = (
    "Improve this llms.txt file:\n\n"
    "```\n{llms_txt}\n```\n\n"
    "Return the improved version as plain markdown (no code fences)."
)


class LLMClient:
    """Wraps OpenAI with Langfuse observability. All LLM calls go through this class.

    Features:
    - Langfuse prompt management (versioned prompts without code deploys)
    - Full tracing per job (latency, cost, token usage)
    - Fallback to hardcoded prompts if Langfuse is unavailable
    """

    def __init__(self, config: AIConfig) -> None:
        self._config = config
        self._langfuse = Langfuse()
        self._openai = LangfuseOpenAI()

    def generate_site_summary(
        self,
        url: str,
        name: str,
        homepage_content: str,
        trace_id: str,
    ) -> SiteInfo:
        """Generate a site summary (blockquote + notes) from homepage content."""
        truncated = homepage_content[: self._config.max_content_chars * 2]

        try:
            prompt = self._langfuse.get_prompt("site_summary_generator")
            messages = prompt.compile(url=url, name=name, content=truncated)
        except Exception:
            logger.debug("Langfuse site_summary prompt unavailable, using fallback")
            messages = [
                {"role": "system", "content": SITE_SUMMARY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": SITE_SUMMARY_USER_TEMPLATE.format(
                        url=url, name=name, content=truncated
                    ),
                },
            ]

        response = self._openai.chat.completions.create(
            model=self._config.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=self._config.temperature,
            max_tokens=300,
            trace_id=trace_id,
            metadata={"url": url, "task": "site_summary"},
        )

        result_text = response.choices[0].message.content or "{}"
        result = json.loads(result_text)

        notes = result.get("notes", [])
        if not isinstance(notes, list):
            notes = []
        notes = [n for n in notes if isinstance(n, str) and n.strip()]

        return SiteInfo(
            name=name,
            url=url,
            description=result.get("description"),
            notes=notes or None,
        )

    def generate_section_descriptions(
        self,
        section_name: str,
        pages: list[ExtractedPage],
        trace_id: str,
        content_budget: int = 500,
    ) -> list[EnhancedPage]:
        """Generate titles and descriptions for all pages in a section in one call.

        Args:
            section_name: The section name (e.g. "Blog", "Documentation").
            pages: Pages in this section.
            trace_id: Job ID for Langfuse tracing.
            content_budget: Max chars of content per page to include.

        Returns:
            List of EnhancedPage with LLM-generated titles and descriptions.
        """
        # Build the pages block for the prompt
        page_entries = []
        for i, page in enumerate(pages, 1):
            snippet = (page.content_text or "")[:content_budget]
            entry = f"Page {i}:\nURL: {page.url}\nContent: {snippet}"
            page_entries.append(entry)

        pages_block = "\n\n".join(page_entries)

        try:
            prompt = self._langfuse.get_prompt("batch_section_enhancer")
            messages = prompt.compile(section=section_name, pages_block=pages_block)
        except Exception:
            logger.debug("Langfuse batch_section prompt unavailable, using fallback")
            messages = [
                {"role": "system", "content": BATCH_SECTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": BATCH_SECTION_USER_TEMPLATE.format(
                        section=section_name, pages_block=pages_block
                    ),
                },
            ]

        max_tokens = max(300, len(pages) * 60)

        response = self._openai.chat.completions.create(
            model=self._config.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=self._config.temperature,
            max_tokens=max_tokens,
            trace_id=trace_id,
            metadata={"section": section_name, "page_count": len(pages), "task": "batch_section"},
        )

        result_text = response.choices[0].message.content or "{}"
        result = json.loads(result_text)

        enhanced_by_url: dict[str, dict] = {}
        for entry in result.get("pages", []):
            if isinstance(entry, dict) and "url" in entry:
                enhanced_by_url[entry["url"]] = entry

        enhanced: list[EnhancedPage] = []
        for page in pages:
            if page.url in enhanced_by_url:
                e = enhanced_by_url[page.url]
                enhanced.append(EnhancedPage(
                    url=page.url,
                    title=e.get("title", page.title or "Untitled"),
                    description=e.get("description", ""),
                ))
            else:
                enhanced.append(EnhancedPage(
                    url=page.url,
                    title=page.title or page.og_title or "Untitled",
                    description=page.description or page.og_description or "",
                ))

        return enhanced

    def polish_llms_txt(self, llms_txt: str, trace_id: str) -> str:
        """Polish a complete llms.txt file for consistency and quality.

        Returns the improved llms.txt as plain markdown.
        """
        try:
            prompt = self._langfuse.get_prompt("llms_txt_polisher")
            messages = prompt.compile(llms_txt=llms_txt)
        except Exception:
            logger.debug("Langfuse polish prompt unavailable, using fallback")
            messages = [
                {"role": "system", "content": POLISH_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": POLISH_USER_TEMPLATE.format(llms_txt=llms_txt),
                },
            ]

        response = self._openai.chat.completions.create(
            model=self._config.model,
            messages=messages,
            temperature=self._config.temperature,
            max_tokens=4096,
            trace_id=trace_id,
            metadata={"task": "polish"},
        )

        result = response.choices[0].message.content or llms_txt
        # Strip any code fences the LLM may have wrapped around the output
        result = result.strip()
        if result.startswith("```"):
            lines = result.split("\n")
            lines = lines[1:]  # remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            result = "\n".join(lines)

        return result.strip() + "\n"

    def generate_description(
        self,
        url: str,
        content: str,
        trace_id: str,
    ) -> EnhancedPageDescription:
        """Generate a title and description for a single page.

        Uses Langfuse prompt management if available, falls back to hardcoded prompt.
        """
        messages = self._build_messages(url, content)

        response = self._openai.chat.completions.create(
            model=self._config.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            trace_id=trace_id,
            metadata={"url": url},
        )

        result_text = response.choices[0].message.content or "{}"
        result = json.loads(result_text)

        return EnhancedPageDescription(
            title=result.get("title", "Untitled"),
            description=result.get("description", ""),
        )

    def _build_messages(self, url: str, content: str) -> list[dict[str, str]]:
        """Build chat messages, preferring Langfuse-managed prompts."""
        truncated_content = content[: self._config.max_content_chars]

        try:
            prompt = self._langfuse.get_prompt("page_description_enhancer")
            return prompt.compile(url=url, content=truncated_content)
        except Exception:
            logger.debug("Langfuse prompt unavailable, using fallback")
            return [
                {"role": "system", "content": FALLBACK_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": FALLBACK_USER_PROMPT_TEMPLATE.format(
                        url=url, content=truncated_content
                    ),
                },
            ]

    def flush(self) -> None:
        """Flush Langfuse traces."""
        self._langfuse.flush()

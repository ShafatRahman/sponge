# Backend Generation Pipeline

The generation pipeline runs inside Celery tasks. Both Default and Detailed modes share the same pipeline; the only difference is that Detailed mode also produces `llms-full.txt`.

## Pipeline Stages

### 1. Discovery

Shared between Default and Detailed modes.

1. **Robots.txt parsing** (`RobotsParser`): Fetch `/robots.txt`, extract sitemap URLs and disallowed paths.
2. **Sitemap parsing** (`SitemapParser`): Recursively fetch and parse sitemaps (max depth 3, max 500 entries). Results are cached in Redis for 1 hour.
3. **BFS fallback** (`LinkCrawler`): If no sitemap entries found, crawl the homepage and follow links up to `max_depth` (default 2). Uses HTTP-first with Playwright fallback for bot-blocked (403) or CSR pages. Domain matching is www-agnostic (`tesla.com` == `www.tesla.com`).
4. Pages are capped at `max_urls` (default 50, max 100).

### 2. Extraction

**`SmartPageFetcher`** (shared pipeline for both modes):
- Concurrent HTTP fetches via `httpx` (10 concurrent connections)
- BeautifulSoup4 parses HTML for `<title>`, `<meta name="description">`, Open Graph tags
- Detects JS-rendered pages via heuristics (empty body + noscript, React/Vue root divs)
- Pages returning 403/429 (bot-blocked) are also flagged for Playwright re-fetch
- Playwright fallback: CSR or bot-blocked pages are re-rendered with headless Chromium
- Soft-404 detection filters out "access denied", "forbidden", and generic error pages

### 3. Categorization

**`URLCategorizer`**: Groups pages into sections (Documentation, API Reference, Guides, Blog, etc.) using regex path patterns. Unmatched pages get a section name from their first URL path segment. Small sections are merged into "Pages". This happens **before** enhancement so the LLM can process pages in section-aware batches.

### 4. Enhancement

**`DescriptionEnhancer`** + **`LLMClient`** (both Default and Detailed modes):
- Pages are sent to GPT-4o-mini in **batches by section** (one LLM call per section) for cross-page awareness and differentiated descriptions
- `LLMClient.generate_site_summary()`: Generates blockquote + key notes from the homepage
- `LLMClient.polish_llms_txt()`: Final consistency pass on the assembled output
- All LLM calls are traced via Langfuse (latency, cost, token usage)
- Graceful degradation: falls back to meta tag descriptions if LLM fails

### 5. Assembly

**`LlmsTxtBuilder`**: Assembles the final [llmstxt.org](https://llmstxt.org) spec-compliant output:
- `build_index()`: Produces `llms.txt` (H1 + blockquote + notes + H2 sections with markdown links, max 5 entries per section)
- `build_full()`: Produces `llms-full.txt` (full page content inlined under each section)
- Detailed mode uploads `llms-full.txt` to Supabase Storage

## Task Classes

Both tasks inherit from `BaseGenerationTask`, which provides:
- Lazy-initialized Redis, CacheService, and SupabaseService
- `publish_progress()`: writes to Redis cache AND publishes to pub/sub channel for SSE
- `update_job_status()`: updates the Django Job model
- `on_failure()`: marks job as failed with error message

```
generate (prefork pool, concurrency=4)
  -> _discover_pages (robots.txt -> sitemap -> BFS fallback)
  -> PageFetcher.fetch_all (HTTP-first, Playwright fallback for CSR/403)
  -> URLCategorizer.categorize (section-aware grouping)
  -> DescriptionEnhancer.enhance_sections (batch by section, OpenAI)
  -> LLMClient.generate_site_summary (homepage -> blockquote + notes)
  -> LlmsTxtBuilder.build_index (curated llms.txt)
  -> [Detailed only] LlmsTxtBuilder.build_full + upload to Supabase Storage
  -> LLMClient.polish_llms_txt (final consistency pass)
  -> save to Job model
```

## Key Files

| File | Purpose |
|------|---------|
| `apps/jobs/tasks.py` | Celery task definitions, pipeline orchestration |
| `apps/core/models.py` | All Pydantic data models (pipeline data, config, progress events) |
| `apps/crawler/` | Robots, sitemap, link crawler, page fetcher |
| `apps/extractor/` | Meta extraction (BS4), content extraction, Playwright provider |
| `apps/generator/` | URL categorizer, llms.txt builder |
| `apps/ai/` | LLM client (OpenAI + Langfuse), description enhancer |

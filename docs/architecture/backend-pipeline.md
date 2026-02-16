# Backend Generation Pipeline

The generation pipeline runs inside Celery tasks. Both Default and Detailed modes share the same pipeline; the only difference is that Detailed mode also produces `llms-full.txt`.

## Pipeline Stages

### 1. Discovery

Shared between Default and Detailed modes.

1. **Robots.txt parsing** (`RobotsParser`): Fetch `/robots.txt`, extract sitemap URLs and disallowed paths.
2. **Sitemap parsing** (`SitemapParser`): Recursively fetch and parse sitemaps. Results are cached in Redis for 1 hour.
3. **BFS fallback** (`LinkCrawler`): If no sitemap entries found, crawl the homepage and follow links up to `max_depth` (default 2).
4. Pages are capped at `max_urls` (default 50, max 100).

### 2. Extraction

**Default and Detailed modes** (shared pipeline: `PageFetcher` + `MetaExtractor`):
- Concurrent HTTP fetches via `httpx` (10 concurrent connections)
- BeautifulSoup4 parses HTML for `<title>`, `<meta name="description">`, Open Graph tags
- Detects JS-rendered pages via heuristics (empty body + noscript, React/Vue root divs)
- Playwright fallback: If a page is detected as client-side rendered, Playwright renders it with headless Chromium

### 3. Enhancement

`DescriptionEnhancer` + `LLMClient`:
- Pages with content are sent to GPT-4o-mini via Langfuse for AI-generated descriptions
- Batch processing with configurable concurrency (default 10 concurrent LLM calls)
- Cost is estimated and tracked in job metadata
- Used in both Default and Detailed modes

### 4. Categorization + Assembly

1. **`URLCategorizer`**: Categorizes pages into sections (Documentation, API Reference, Guides, Blog, etc.) using regex path patterns. Unmatched pages get a section name from their first URL path segment.
2. **`LlmsTxtBuilder`**: Assembles the final output:
   - `build_index()`: Produces `llms.txt` (H1 + blockquote + H2 sections with markdown links)
   - `build_full()`: Produces `llms-full.txt` (full page content inlined under each section)

## Task Classes

Both tasks inherit from `BaseGenerationTask`, which provides:
- Lazy-initialized Redis, CacheService, and SupabaseService
- `publish_progress()`: writes to Redis cache AND publishes to pub/sub channel for SSE
- `update_job_status()`: updates the Django Job model
- `on_failure()`: marks job as failed with error message

```
generate (prefork pool, concurrency=4) -- both Default and Detailed modes
  -> _discover_pages
  -> PageFetcher.fetch_all (with Playwright fallback for CSR sites)
  -> DescriptionEnhancer.enhance_batch (OpenAI)
  -> URLCategorizer.categorize
  -> LlmsTxtBuilder.build_index
  -> save to Job model

generate (prefork pool, concurrency=4)
  -> _discover_pages
  -> PageFetcher.fetch_all (with Playwright fallback for CSR sites)
  -> DescriptionEnhancer.enhance_batch (OpenAI)
  -> URLCategorizer.categorize
  -> LlmsTxtBuilder.build_index + build_full
  -> upload llms-full.txt to Supabase Storage
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

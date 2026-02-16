# Testing

## Running Tests

```bash
cd backend

# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a specific test module
uv run pytest apps/core/tests/test_rate_limiter.py

# Run a specific test class
uv run pytest apps/core/tests/test_ssrf_protection.py::TestSSRFGuard

# Run a specific test
uv run pytest apps/jobs/tests/test_views.py::TestJobStreamView::test_stream_returns_sse_content_type
```

## Test Structure

```
backend/
  conftest.py                              # Shared fixtures (fake_redis, cache_service, job_factory)
  apps/
    core/tests/
      test_ssrf_protection.py              # SSRFGuard: IP blocking, scheme validation, DNS resolution
      test_rate_limiter.py                 # RateLimiter: sliding window, limits, separate identifiers
      test_cache.py                        # CacheService: get/set/delete/publish, JSON round-trip
    generator/tests/
      test_url_categorizer.py              # URLCategorizer: pattern matching, fallback sections
      test_llms_txt_builder.py             # LlmsTxtBuilder: spec-compliant index + full output
    extractor/tests/
      test_meta_extractor.py               # MetaExtractor: title, description, OG tags, JS detection
    jobs/tests/
      test_views.py                        # API integration: create, detail, stream (SSE), rate limiting
```

**Total: 96 tests** across 8 test files.

## Test Categories

| Category | Tests | What's Covered |
|----------|-------|----------------|
| Core | 31 | SSRF guard, rate limiter, cache service |
| Generator | 32 | URL categorization, llms.txt/llms-full.txt building |
| Extractor | 17 | HTML metadata extraction, JS rendering detection |
| Views | 14 | API endpoints, SSE streaming, rate limiting |

## Shared Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `fake_redis` | function | `fakeredis.FakeRedis` instance. Behaves like real Redis without a server. |
| `cache_service` | function | `CacheService` backed by `fake_redis`. |
| `job_factory` | function | Factory for creating `Job` ORM instances with sensible defaults. Requires `db` fixture. |

## Writing New Tests

1. Create a test file in the appropriate `tests/` directory following the `test_*.py` naming convention.
2. Use `fakeredis` for any Redis-dependent code. Import via the `fake_redis` fixture.
3. For views tests, use `django.test.TestCase` with `rest_framework.test.APIClient`.
4. Mock external services (`socket.gethostbyname`, Celery `.delay()`, Supabase) with `unittest.mock.patch`.
5. Use `@override_settings` for test-specific Django settings.

### Example: Testing a new service

```python
from __future__ import annotations

from apps.my_module.my_service import MyService


class TestMyService:
    def test_does_something(self, fake_redis) -> None:
        service = MyService(redis=fake_redis)
        result = service.process("input")
        assert result.status == "ok"
```

## Configuration

Test configuration is in `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.development"
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
```

Dev dependencies: `pytest`, `pytest-django`, `pytest-asyncio`, `fakeredis`.

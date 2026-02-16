# Code Style Guide

## General

- Never use emojis in code, logs, print statements, or commit messages.
- All code must pass lint and format checks before committing (enforced by Husky pre-commit hook).

## Backend (Python)

### Conventions

- **Every module is a class** with dependency injection via `__init__`. No loose functions at module level (except helpers prefixed with `_`).
- **`from __future__ import annotations`** in every file for deferred type evaluation.
- **`TYPE_CHECKING` blocks** for imports only needed by type hints (keeps runtime imports lean).
- **Pydantic models** for all internal pipeline data. Never pass raw dicts between pipeline stages.
- **DRF serializers** for API boundary validation. Pydantic validates internal data; serializers validate external input/output.

### Tooling

| Tool | Command | Purpose |
|------|---------|---------|
| ruff | `uv run ruff check .` | Lint (replaces flake8 + isort) |
| ruff | `uv run ruff format .` | Format (replaces black) |
| mypy | `uv run mypy apps/` | Static type checking |
| pytest | `uv run pytest` | Test suite |

Configuration: `backend/ruff.toml` (line length 100, double quotes, migration files excluded).

### Example

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.core.http_client import HttpClient
    from apps.core.models import CrawlConfig

class MyService:
    def __init__(self, http_client: HttpClient, config: CrawlConfig) -> None:
        self._http_client = http_client
        self._config = config

    async def process(self, url: str) -> SomeResult:
        ...
```

## Frontend (TypeScript / React)

### Conventions

- **Functional components only**. No class components.
- **Class-based services**: `ApiClient`, `JobsService`, `AuthService`.
- **Zod schemas** for runtime validation of all API responses.
- **`@/` path alias** for imports (maps to project root).
- **snake_case <-> camelCase**: Axios interceptors handle the transformation at the API boundary.

### Tooling

| Tool | Command | Purpose |
|------|---------|---------|
| TypeScript | `npm run typecheck` | Type checking |
| ESLint 9 | `npm run lint` | Linting |
| Prettier | `npm run format` | Formatting (with Tailwind class sorting) |
| All-in-one | `npm run check` | typecheck + lint + format check |

Configuration: `eslint.config.mjs`, `.prettierrc.json`, `tsconfig.json`.

## Terraform

- Modular structure: each logical resource group is a module with `main.tf`, `variables.tf`, `outputs.tf`.
- Sensitive variables marked with `sensitive = true`.
- Secrets stored in SSM Parameter Store, never as plain-text env vars.
- Environment-specific values in `environments/{dev,prod}/terraform.tfvars`.

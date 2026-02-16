# Git Workflow

## Branch Strategy

- `main`: Production branch. Auto-deploys to Vercel (frontend) and ECS (backend on push).
- Feature branches: `feature/description` or `fix/description`. Branch from `main`, PR back to `main`.

## Commit Conventions

- Write concise commit messages focused on "why" not "what".
- No emojis in commit messages.
- Reference issue numbers when applicable.

## Pre-commit Hooks

Husky + lint-staged runs automatically on every commit:

1. `*.{ts,tsx}` files: ESLint --fix + Prettier --write
2. `*.{json,md,css}` files: Prettier --write

The hook is configured at the monorepo root (`.husky/pre-commit`) and delegates to `cd frontend && npx lint-staged`.

Backend linting is not in the pre-commit hook (run `uv run ruff check . && uv run ruff format .` manually or rely on CI).

## Pull Request Checklist

Before submitting a PR:

- [ ] Backend: `uv run ruff check . && uv run ruff format --check .` passes
- [ ] Backend: `uv run pytest` passes (96+ tests)
- [ ] Frontend: `npm run check` passes (typecheck + lint + format)
- [ ] If you changed backend code in `apps/`, consider if tests need updating
- [ ] If you changed architecture, update `docs/architecture/`
- [ ] If you added/changed an API endpoint, update `docs/api/endpoints.md`
- [ ] If you changed infrastructure, update `docs/deployment/` and `infrastructure/environments/*/terraform.tfvars.example`

## CI Checks

PRs trigger automated CI checks (see [CI/CD docs](../deployment/ci-cd.md)):
- Backend CI: ruff lint + format + pytest
- Frontend CI: typecheck + lint + format + build
- Terraform: plan (commented on PR)
- Docs staleness: reminder if code changed without doc updates

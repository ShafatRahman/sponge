# Keeping Documentation Up to Date

## The Problem

Documentation drifts out of sync with code. The longer it goes unnoticed, the less anyone trusts the docs, and the less they maintain them -- a vicious cycle.

## Our Approach: Three Layers of Defense

### 1. CI Staleness Detection (Automated)

A GitHub Actions workflow (`.github/workflows/docs-check.yml`) runs on every PR that touches `backend/`, `frontend/`, or `infrastructure/`. It checks whether the PR also includes changes to `docs/`. If not, it posts a reminder comment.

This is a **soft check** (does not block merge) because not every code change requires a doc update. It serves as a nudge.

### 2. AI Agent Rules (Cursor / Claude)

Both `.cursor/rules/` and `.claude/instructions.md` include instructions telling AI agents to:
- **Read** relevant docs before making changes
- **Update** docs when making architectural or API changes
- **Reference** `docs/` in their responses when applicable

This means every AI-assisted coding session is aware of the docs.

### 3. PR Review Culture (Human)

The PR checklist in [git-workflow.md](./git-workflow.md) includes doc update reminders for specific categories of changes. Reviewers should check:
- Architecture changes -> `docs/architecture/`
- API changes -> `docs/api/`
- New dependencies -> `docs/technologies/`
- Deployment changes -> `docs/deployment/`
- New test patterns -> `docs/testing/`

## What to Update and When

| Change | Docs to Update |
|--------|---------------|
| New API endpoint | `docs/api/endpoints.md` |
| Changed SSE protocol | `docs/api/sse-protocol.md`, `docs/architecture/sse-streaming.md` |
| New dependency | `docs/technologies/` (appropriate sub-file) |
| Architecture change | `docs/architecture/overview.md` + relevant sub-file |
| New Terraform module | `docs/deployment/` + `docs/technologies/infrastructure.md` |
| Changed env vars | `docs/setup/environment-variables.md` |
| New test patterns | `docs/testing/README.md` |
| Changed Docker setup | `docs/setup/docker.md` |

## Keeping .cursor and .claude in Sync

When making significant architectural changes, also update:
- `.cursor/rules/project-conventions.mdc` -- high-level architecture, data flow, key files
- `.claude/instructions.md` -- project overview, architecture, key commands, file layout

These files are the "executive summary" that AI agents read on every interaction. Keep them concise but accurate.

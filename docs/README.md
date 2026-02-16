# Sponge Documentation

Internal engineering documentation for the Sponge llms.txt generator project.

## How to Navigate

| Section | What You'll Find |
|---------|-----------------|
| [Setup](./setup/) | Local development, environment variables, Docker configuration |
| [Architecture](./architecture/) | System design, backend pipeline, data flow, SSE streaming |
| [Technologies](./technologies/) | Key packages, frameworks, and where to learn more |
| [Deployment](./deployment/) | AWS ECS, Vercel, CI/CD pipelines, SSM secrets management |
| [Testing](./testing/) | Test structure, running tests, writing new tests |
| [API](./api/) | REST endpoints, authentication, SSE streaming protocol |
| [Contributing](./contributing/) | Code style, git workflow, keeping docs up to date |

## Reference Links

- **Root README**: [`../README.md`](../README.md) -- project overview, quick start, tech stack summary
- **Cursor rules**: [`../.cursor/rules/`](../.cursor/rules/) -- AI agent conventions (auto-applied)
- **Claude instructions**: [`../.claude/instructions.md`](../.claude/instructions.md) -- Claude Code agent context

## Keeping Docs Current

Documentation follows a "docs-as-code" approach: it lives alongside the code in version control, is reviewed in PRs, and has a CI staleness check that flags when code changes without corresponding doc updates. See [Contributing > Docs Maintenance](./contributing/docs-maintenance.md) for details.

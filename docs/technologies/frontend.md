# Frontend Technologies

## Core Framework

### Next.js 16

- **What**: React framework with App Router, server components, and file-based routing.
- **Why**: SSR/SSG for SEO, built-in API rewrites for dev proxy, excellent DX with Turbopack.
- **Our usage**: App Router pages (`app/`), `next.config.ts` rewrites for API proxy.
- **Docs**: https://nextjs.org/docs

### React 19

- **What**: UI library for building component-based interfaces.
- **Why**: Industry standard. Hooks for state management, `use()` for async params.
- **Our usage**: Functional components only. Custom hooks like `useJobStream`.
- **Docs**: https://react.dev/

## UI

### shadcn/ui

- **What**: Copy-paste component library built on Radix UI primitives.
- **Why**: Beautiful, accessible, fully customizable (not a black-box library). Profound-inspired dark theme.
- **Our usage**: `Card`, `Button`, `Badge`, `Input`, etc. in `components/ui/`.
- **Add components**: `npx shadcn add <component-name>`
- **Docs**: https://ui.shadcn.com/

### Tailwind CSS v4

- **What**: Utility-first CSS framework.
- **Why**: Rapid styling, consistent design system, excellent dark mode support.
- **Our usage**: All styling via Tailwind classes. CSS variables for theme colors in `globals.css`.
- **Docs**: https://tailwindcss.com/docs

### Lucide React

- **What**: Icon library.
- **Why**: Consistent, customizable SVG icons. Used by shadcn/ui.
- **Docs**: https://lucide.dev/

## Data & API

### Zod

- **What**: TypeScript-first schema declaration and validation.
- **Why**: Runtime validation of API responses. Type inference from schemas.
- **Our usage**: All API response schemas in `lib/models/job.ts`. Parsed in `JobsService` and `useJobStream`.
- **Docs**: https://zod.dev/

### Axios

- **What**: Promise-based HTTP client.
- **Why**: Interceptors for auth tokens and case transformation. Better error handling than fetch.
- **Our usage**: `ApiClient` singleton in `lib/api/api-client.ts`.
- **Docs**: https://axios-http.com/

### Supabase JS

- **What**: JavaScript client for Supabase Auth.
- **Why**: Client-side auth (login, signup, OAuth, session refresh).
- **Our usage**: `@supabase/supabase-js` and `@supabase/ssr` in `lib/supabase/`.
- **Docs**: https://supabase.com/docs/reference/javascript

## Error Tracking & Notifications

### Sentry (@sentry/nextjs)

- **What**: Application error monitoring for Next.js (client, server, and edge runtimes).
- **Why**: Auto-captures unhandled errors, React rendering errors, and API failures with full context.
- **Our usage**: Config in `sentry.client.config.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`. DSN via `NEXT_PUBLIC_SENTRY_DSN`. Disabled when empty.
- **Docs**: https://docs.sentry.io/platforms/javascript/guides/nextjs/

### Sonner

- **What**: Toast notification library. Used via shadcn/ui's `<Toaster />` wrapper.
- **Why**: Lightweight, accessible, theme-aware. Provides non-blocking error/success notifications.
- **Our usage**: `<Toaster />` in `components/providers.tsx`, `toast.error()` / `toast.warning()` in error handlers.
- **Docs**: https://sonner.emilkowal.dev/

## Dev Tooling

### ESLint 9 + eslint-config-next

- **What**: JavaScript/TypeScript linter.
- **Why**: Catches bugs, enforces patterns. Next.js config includes React and accessibility rules.
- **Our usage**: `npm run lint`. Integrated with lint-staged for pre-commit.
- **Docs**: https://eslint.org/

### Prettier

- **What**: Opinionated code formatter.
- **Why**: Consistent formatting without debates. Tailwind class sorting via plugin.
- **Our usage**: `npm run format`. Config in `.prettierrc.json`.
- **Docs**: https://prettier.io/

### Husky + lint-staged

- **What**: Git hooks and staged-file processing.
- **Why**: Auto-lint and format on every commit. Catches issues before CI.
- **Our usage**: `.husky/pre-commit` runs `cd frontend && npx lint-staged`.
- **Docs**: https://typicode.github.io/husky/ / https://github.com/lint-staged/lint-staged

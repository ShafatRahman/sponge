import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN ?? "",

  // Performance monitoring: capture 10% of transactions
  tracesSampleRate: 0.1,

  // Session replay: capture 10% of sessions, 100% on error
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,

  integrations: [Sentry.replayIntegration(), Sentry.browserTracingIntegration()],

  // Don't send PII (emails, usernames, IPs)
  sendDefaultPii: false,

  // Only enable in production
  enabled: process.env.NODE_ENV === "production",
});

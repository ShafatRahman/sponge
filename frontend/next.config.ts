import { resolve } from "path";
import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: resolve(__dirname, ".."),
  },
  // Proxy API requests in development to avoid CORS issues
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default withSentryConfig(nextConfig, {
  // Silently ignore missing SENTRY_AUTH_TOKEN in dev
  silent: !process.env.CI,
  // Upload source maps for better stack traces in production
  widenClientFileUpload: true,
  // Hide source maps from users
  sourcemaps: {
    deleteSourcemapsAfterUpload: true,
  },
  // Disable Sentry telemetry
  telemetry: false,
  // Remove Sentry debug logging from bundle
  webpack: {
    treeshake: {
      removeDebugLogging: true,
    },
  },
});

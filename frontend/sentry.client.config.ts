/**
 * Sentry configuration for Next.js client-side
 * This captures JavaScript errors in the user's browser
 */

import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,

    // Environment
    environment: process.env.NODE_ENV,

    // Performance monitoring - 10% of transactions
    tracesSampleRate: 0.1,

    // Session replay for debugging (captures what user did before crash)
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,

    // Don't send errors in development
    enabled: process.env.NODE_ENV === "production",

    // Filter out noisy errors
    ignoreErrors: [
      // Browser extensions
      "ResizeObserver loop limit exceeded",
      "ResizeObserver loop completed with undelivered notifications",
      // Network errors that aren't actionable
      "Network request failed",
      "Failed to fetch",
      // Third-party script errors
      "Script error.",
    ],

    // Add context before sending
    beforeSend(event: Sentry.ErrorEvent) {
      // Don't send if no DSN (shouldn't happen but safety check)
      if (!SENTRY_DSN) return null;
      return event;
    },
  });
}

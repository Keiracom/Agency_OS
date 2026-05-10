"use client";

/**
 * FILE: frontend/app/admin/ops/AutoRefresh.tsx
 * PURPOSE: Client-side wrapper that calls router.refresh() every N seconds
 *          so the server-component ops panel re-fetches its Supabase data
 *          without a page reload. Phase 4 follow-up to PR #656 / Max's
 *          dispatch ("ops panel auto-refresh + per-vendor cost cards").
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";

interface AutoRefreshProps {
  /** Polling interval in milliseconds. Default 30s. */
  intervalMs?: number;
}

export function AutoRefresh({ intervalMs = 30_000 }: AutoRefreshProps) {
  const router = useRouter();
  useEffect(() => {
    const id = setInterval(() => router.refresh(), intervalMs);
    return () => clearInterval(id);
  }, [router, intervalMs]);
  return null;
}

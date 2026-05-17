/**
 * FILE: frontend/components/dispatcher/use-thread-usage.ts
 * PURPOSE: Hook contract for ThreadUsageGauge data loading. Sub-KEI claimer
 *          implements the Valkey-backed live count (subscribe to the tenant
 *          channel via a backend SSE endpoint or supabase realtime); this
 *          stub fixes the result shape so the gauge can compose against a
 *          stable interface.
 * KEI: 161 (Thread usage gauge) — data layer; depends on KEI-117A
 *      (Valkey connection pool + per-tenant key namespace).
 *
 * Stub: returns null usage + loading=false. Replace with live subscription
 * + a "tier ceiling" lookup against `public.tenants.tier` (or whatever
 * KEI-117C tier-limits-from-database lands).
 */

import type { DispatcherTier, ThreadUsage } from "./thread-usage-gauge";

export interface UseThreadUsageOptions {
  /** Tenant id whose thread count to watch. When omitted the hook expects
   *  the live implementation to derive it from the Supabase session. */
  tenantId?: string;
  /** Force a fixed tier for testing — production reads from the tenant row. */
  tier?: DispatcherTier;
  /** Poll interval (ms) used when realtime is unavailable. */
  pollMs?: number;
}

export interface UseThreadUsageResult {
  usage: ThreadUsage | null;
  loading: boolean;
  error: Error | null;
  reload: () => void;
}

const DEFAULT_RESULT: UseThreadUsageResult = {
  usage: null,
  loading: false,
  error: null,
  reload: () => {},
};

export function useThreadUsage(_opts: UseThreadUsageOptions = {}): UseThreadUsageResult {
  // Stub — sub-KEI implements:
  //   - Live count: subscribe to backend SSE or supabase realtime channel
  //     keyed by tenant id (KEI-117A namespace);
  //   - Tier ceiling: SELECT tier FROM public.tenants WHERE id = <tenant_id>,
  //     then look up ceiling via KEI-117C tier-limits table;
  //   - Poll fallback when realtime drops: every pollMs (default 5000)
  //     re-fetch active count from Valkey via backend endpoint;
  //   - Cleanup on unmount.
  return DEFAULT_RESULT;
}

/**
 * FILE: frontend/components/dispatcher/use-cost-breakdown.ts
 * PURPOSE: Hook contract stub for cost breakdown data.
 * KEI: KEI-159 (KEI-114B) — Cost Display implementation.
 *
 * DATABASE CONTRACT (wired by follow-up sub-KEI):
 *
 * Supabase RPC:
 *   get_tenant_cost_breakdown(tenant_id uuid, period_days int default 30)
 *   RETURNS TABLE(task_id text, title text, cost_aud numeric, completed_at timestamptz)
 *
 * Backed by materialised view `tenant_cost_breakdown_mv` refreshed nightly.
 * The view aggregates cost_events joined to tasks for the tenant, pre-computing
 * both the per-task rows and the cumulative total — so the render is a single
 * RPC call rather than a sum-on-every-load aggregate.
 *
 * Example call:
 *   const { data } = await supabase.rpc('get_tenant_cost_breakdown', {
 *     tenant_id: session.tenantId,
 *     period_days: 30,
 *   });
 *
 * LAW II: The RPC returns cost_aud. All callers display with
 * explicit AUD suffix (A$N.NN AUD). Never display bare $N.
 */

import type { CostRow } from "./cost-breakdown-table";

export type UseCostBreakdownResult = {
  rows: CostRow[];
  totalAud: number;
  loading: boolean;
  error: Error | null;
  periodDays: number;
  refresh: () => void;
};

/**
 * useCostBreakdown — stub implementation.
 *
 * Returns empty/zero state until the follow-up sub-KEI wires the Supabase RPC.
 * Replace this body with an actual `supabase.rpc('get_tenant_cost_breakdown', ...)`
 * call once `tenant_cost_breakdown_mv` migration is applied.
 *
 * @param periodDays - Rolling window in days (default 30).
 */
export function useCostBreakdown(periodDays = 30): UseCostBreakdownResult {
  return {
    rows: [],
    totalAud: 0,
    loading: false,
    error: null,
    periodDays,
    refresh: () => {
      // no-op stub — replace with queryClient.invalidateQueries(...) when wired
    },
  };
}

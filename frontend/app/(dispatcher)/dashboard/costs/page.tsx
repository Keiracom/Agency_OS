/**
 * FILE: frontend/app/(dispatcher)/dashboard/costs/page.tsx
 * PURPOSE: Customer cost view — cost-per-task breakdown + cumulative spend.
 * KEI: 114B (Linear KEI-159) — Cost Display implementation.
 *      Deps: 114A (Feed Component must exist for the row → cost drill-down).
 *
 * Stub only. Implementer wires:
 *   - SELECT task_id, container_run_seconds, cost_usd, cost_aud FROM public.tasks
 *     JOIN public.cost_events ON task_id (table TBD by sub-KEI claimer)
 *   - Per-AU-dollar conversion (Australia-first per LAW II — 1 USD = 1.55 AUD)
 *   - Cumulative spend card (sum over the configured window — default 30d)
 *   - Cost-per-task table (descending by cost_aud, drill-down link to feed row)
 *   - Query optimisation: materialised view or daily rollup table for the
 *     cumulative card so the page render doesn't sum every claim every load.
 */

export default function DispatcherDashboardCostsPage() {
  return (
    <main className="mx-auto max-w-5xl p-8">
      <h1 className="text-2xl font-semibold">Costs</h1>
      <p className="mt-4 text-sm text-muted-foreground">
        Implementation pending KEI-114B (KEI-159). Cost-per-task breakdown +
        cumulative AUD spend card land here. Currency labels match values per
        LAW II (1 USD = 1.55 AUD).
      </p>
    </main>
  );
}

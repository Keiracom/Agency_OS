/**
 * FILE: frontend/app/(dispatcher)/dashboard/usage/page.tsx
 * PURPOSE: Thread usage meter — real-time count vs tier limit.
 * KEI: 114D (Linear KEI-161) — Usage Meter implementation.
 *      Deps: 117A (Valkey connection pool + key namespace).
 *
 * Stub only. Implementer wires:
 *   - Read live counter from Valkey: KEY=`tenant:{id}:threads_active`
 *     (per-tenant namespace per KEI-117A).
 *   - Read tier limit from public.subscriptions (KEI-112B) → max_threads.
 *   - Gauge component: current/max with colour bands (green <60%, amber
 *     60-90%, red >=90%, hard-stop at 100% per rate limiter KEI-117B).
 *   - Tier indicator: Basic / Pro / Enterprise label + upgrade CTA when
 *     usage trends consistently >80% (3 polls in 5 min window).
 *   - Refresh cadence: 5s polling at first; switch to Supabase Realtime
 *     once the subscriptions table publishes ('threads_active' changes).
 */

export default function DispatcherDashboardUsagePage() {
  return (
    <main className="mx-auto max-w-5xl p-8">
      <h1 className="text-2xl font-semibold">Thread usage</h1>
      <p className="mt-4 text-sm text-muted-foreground">
        Implementation pending KEI-114D (KEI-161). Real-time thread counter
        vs tier limit with colour-banded gauge lands here. Reads from Valkey
        (KEI-117A) once that pool is configured.
      </p>
    </main>
  );
}

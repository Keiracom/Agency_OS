/**
 * FILE: frontend/app/dispatcher/dashboard/page.tsx
 * PURPOSE: Customer dashboard — task feed + cost + key management.
 * KEI: 113D (KEI-157) + KEI-114 family — implements:
 *      - First-task completion banner (KEI-113D)
 *      - Task feed UI (KEI-114A, KEI-158)
 *      - Cost-per-task + cumulative spend (KEI-114B, KEI-159)
 *      - API key management list/rotate/revoke (KEI-114C, KEI-160)
 *      - Thread usage gauge + tier indicator (KEI-114D, KEI-161)
 *      - Deps: full onboarding chain landed
 *
 * Stub only.
 */

export default function DispatcherDashboardPage() {
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <p className="mt-4 text-sm text-muted-foreground">
        Implementation pending KEI-113D (KEI-157) + KEI-114 family (KEI-158..161).
        Task feed + cost + key mgmt + thread usage land here.
      </p>
    </main>
  );
}

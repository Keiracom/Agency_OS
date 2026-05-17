/**
 * FILE: frontend/app/dispatcher/onboarding/first-task/page.tsx
 * PURPOSE: Customer submits their first task to the dispatcher.
 * KEI: 113C (KEI-156) — implements:
 *      - Form: task title + description
 *      - On submit: INSERT into public.tasks + trigger Prefect flow
 *      - User sees pending state (poll or realtime subscribe)
 *      - On task complete → redirect /dispatcher/dashboard (KEI-113D)
 *      - Deps: KEI-113B (BYO key present), KEI-115E LiteLLM router (KEI-166)
 *
 * Stub only.
 */

export default function DispatcherFirstTaskPage() {
  return (
    <main className="mx-auto max-w-md p-8">
      <h1 className="text-2xl font-semibold">Submit your first task</h1>
      <p className="mt-4 text-sm text-muted-foreground">
        Implementation pending KEI-113C (KEI-156). Form → INSERT public.tasks →
        Prefect enqueue → pending state → dashboard on completion.
      </p>
    </main>
  );
}

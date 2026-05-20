/**
 * FILE: frontend/components/dispatcher/use-first-task-watcher.ts
 * PURPOSE: Contract hook — watches for the customer's first completed task and
 *          drives FirstTaskSuccessBanner visibility.
 * KEI: 157 — KEI-113D dashboard populate on first-task completion.
 *
 * Stub: returns safe default state so banner renders deterministically in
 * tests and the dashboard shell without a live Supabase connection.
 *
 * Sub-KEI claimers wire the subscription:
 *   KEI-157A — Supabase realtime channel:
 *     supabase
 *       .channel('first-task-watcher')
 *       .on(
 *         'postgres_changes',
 *         {
 *           event: 'UPDATE',
 *           schema: 'public',
 *           table: 'tasks',
 *           filter: `status=eq.done`,
 *         },
 *         (payload) => { ... }
 *       )
 *       .subscribe()
 *   KEI-157B — banner dismiss persistence via localStorage / user_prefs.
 *   KEI-157C — polling fallback for environments where realtime is unavailable.
 *
 * S1135 pre-empt: deferred work expressed as sub-KEIs in kei157_first_task_scope.md.
 */

import type { DispatcherTask } from "./task-feed";

export interface UseFirstTaskWatcherOptions {
  /** Polling interval in ms for KEI-157C fallback. Sub-KEI claimer honours. */
  pollIntervalMs?: number;
  /** Tenant scope filter. Sub-KEI claimer passes to realtime filter. */
  tenantId?: string;
}

export interface UseFirstTaskWatcherResult {
  /** The first task to reach `done` status, or null if none yet. */
  firstCompletedTask: DispatcherTask | null;
  /** True while the initial query is in-flight. */
  loading: boolean;
  /** Call to hide the success banner and persist the dismissal (KEI-157B). */
  dismiss: () => void;
}

/**
 * Watches for the customer's first completed task.
 *
 * Stub implementation returns `{ firstCompletedTask: null, loading: false }`.
 * KEI-157A claimer replaces this body with a Supabase realtime subscription
 * (see module doc-comment for the subscription pattern).
 */
export function useFirstTaskWatcher(
  _options: Readonly<UseFirstTaskWatcherOptions> = {}
): UseFirstTaskWatcherResult {
  return {
    firstCompletedTask: null,
    loading: false,
    dismiss: () => {
      /* KEI-157B claimer wires dismissal persistence; stub is a deliberate no-op. */
    },
  };
}

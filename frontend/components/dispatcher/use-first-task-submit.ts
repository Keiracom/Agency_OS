/**
 * FILE: frontend/components/dispatcher/use-first-task-submit.ts
 * PURPOSE: Hook contract for the FirstTaskForm onSubmit callback. Sub-KEI
 *          claimer implements the actual public.tasks INSERT + Prefect
 *          flow trigger; this stub fixes the signature so the form can
 *          compose against a stable interface.
 * KEI: 156 (First-task submission form → Prefect enqueue).
 *
 * Stub: returns a no-op async submitter that always resolves. Replace
 * with the live POST /api/dispatcher/tasks (or supabase.from('tasks').insert)
 * + Prefect deployment trigger.
 */

import type { FirstTaskFormValues } from "./first-task-form";

export interface UseFirstTaskSubmitOptions {
  /** Tenant whose task to create. When omitted the live hook derives it
   *  from the Supabase session. */
  tenantId?: string;
  /** Prefect deployment name to trigger. Sub-KEI implements; default
   *  follows the dispatcher convention. */
  deployment?: string;
}

export interface UseFirstTaskSubmitResult {
  submit: (values: FirstTaskFormValues) => Promise<void>;
}

export function useFirstTaskSubmit(_opts: UseFirstTaskSubmitOptions = {}): UseFirstTaskSubmitResult {
  // Stub — sub-KEI implements:
  //   1. INSERT into public.tasks via Supabase client OR a backend
  //      /api/dispatcher/tasks POST endpoint (recommended — server can
  //      set tenant_id from the session, status='pending').
  //   2. Trigger the Prefect deployment via REST (or via a Supabase
  //      database trigger on tasks INSERT that calls the deployment).
  //   3. Return the created task id so the dashboard-populate hook
  //      (KEI-113D) can subscribe to its completion.
  return {
    submit: async (_values: FirstTaskFormValues) => {
      // No-op until sub-KEI implements.
    },
  };
}

/**
 * FILE: frontend/components/dispatcher/use-task-feed.ts
 * PURPOSE: Hook contract for TaskFeed data loading. Sub-KEI claimer
 *          implements the Supabase query + realtime subscription;
 *          this stub fixes the shape so TaskFeed + Pagination can be
 *          composed against a stable interface.
 * KEI: 158 (Task feed UI) — data layer; depends on KEI-111B (auth)
 *      for the customer-id RLS scoping.
 *
 * Stub: returns the resolved shape with sensible defaults. Replace
 * the body with `useEffect` + `supabase.from('tasks').select(...)`.
 */

import type { DispatcherTask } from "./task-feed";

export interface UseTaskFeedOptions {
  pageSize?: number;
  cursor?: string | null;
  /**
   * Customer id whose tasks to fetch. When omitted, the hook expects
   * the implementing version to derive it from the Supabase session.
   */
  customerId?: string;
}

export interface UseTaskFeedResult {
  tasks: DispatcherTask[];
  loading: boolean;
  error: Error | null;
  hasPrev: boolean;
  hasNext: boolean;
  nextCursor: string | null;
  prevCursor: string | null;
  reload: () => void;
}

const DEFAULT_RESULT: UseTaskFeedResult = {
  tasks: [],
  loading: false,
  error: null,
  hasPrev: false,
  hasNext: false,
  nextCursor: null,
  prevCursor: null,
  reload: () => {},
};

export function useTaskFeed(_opts: UseTaskFeedOptions = {}): UseTaskFeedResult {
  // Stub — sub-KEI implements:
  //   - Supabase query: SELECT id, title, status, cost_aud, created_at, completed_at
  //                     FROM public.tasks
  //                    WHERE customer_id = <session.user.id>
  //                    ORDER BY created_at DESC
  //                    LIMIT pageSize + 1
  //                    (KEY-SET pagination via cursor)
  //   - Realtime subscription: supabase
  //       .channel('public:tasks:<customer_id>')
  //       .on('postgres_changes', { event: '*', schema: 'public', table: 'tasks' }, …)
  //   - Cleanup on unmount
  return DEFAULT_RESULT;
}

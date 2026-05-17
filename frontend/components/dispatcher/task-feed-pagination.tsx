/**
 * FILE: frontend/components/dispatcher/task-feed-pagination.tsx
 * PURPOSE: Page controls for TaskFeed. Cursor-based to match the
 *          existing public.tasks indexes (id + created_at). Sub-KEI
 *          claimer wires the cursor advance/back into useTaskFeed hook.
 * KEI: 158 — Task feed pagination (sibling of task-feed.tsx).
 *
 * Stub: button shell + props interface. Disabled state when no prev/next.
 */

import * as React from "react";

export interface TaskFeedPaginationProps {
  hasPrev: boolean;
  hasNext: boolean;
  onPrev?: () => void;
  onNext?: () => void;
  pageLabel?: string;
}

export function TaskFeedPagination({
  hasPrev,
  hasNext,
  onPrev,
  onNext,
  pageLabel,
}: TaskFeedPaginationProps) {
  return (
    <div data-testid="task-feed-pagination" className="flex items-center justify-between py-4">
      <button
        type="button"
        disabled={!hasPrev}
        onClick={onPrev}
        className="rounded border px-3 py-1 text-sm disabled:opacity-50"
      >
        ← Previous
      </button>
      {pageLabel ? <span className="text-sm text-muted-foreground">{pageLabel}</span> : null}
      <button
        type="button"
        disabled={!hasNext}
        onClick={onNext}
        className="rounded border px-3 py-1 text-sm disabled:opacity-50"
      >
        Next →
      </button>
    </div>
  );
}

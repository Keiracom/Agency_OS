/**
 * FILE: frontend/components/dispatcher/first-task-success-banner.tsx
 * PURPOSE: Celebratory banner shown when a customer's first task completes.
 *          Composes with useFirstTaskWatcher — caller passes watcher output
 *          straight through.
 * KEI: 157 — KEI-113D dashboard populate on first-task completion.
 *
 * Readonly<T> on props satisfies Sonar S6759.
 * S1135 pre-empt: no task-marker comments in this file.
 */

import * as React from "react";
import type { DispatcherTask } from "./task-feed";

export interface FirstTaskSuccessBannerProps {
  task: DispatcherTask | null;
  visible: boolean;
  onDismiss: () => void;
}

/**
 * Renders a celebratory success banner when a customer's first task is done.
 *
 * Returns null if `visible` is false or `task` is null — caller drives
 * visibility via useFirstTaskWatcher.
 */
export function FirstTaskSuccessBanner({
  task,
  visible,
  onDismiss,
}: Readonly<FirstTaskSuccessBannerProps>) {
  if (!visible || task === null) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="first-task-success-banner"
      className="flex items-start justify-between gap-4 rounded-lg border border-green-200 bg-green-50 p-4 text-green-900"
    >
      <div className="flex flex-col gap-1">
        <p className="font-semibold">Your first task is done!</p>
        <p className="text-sm text-green-700" data-testid="banner-task-title">
          {task.title}
        </p>
      </div>
      <button
        type="button"
        aria-label="Dismiss success banner"
        data-testid="banner-dismiss-button"
        onClick={onDismiss}
        className="shrink-0 rounded px-3 py-1 text-sm font-medium text-green-800 hover:bg-green-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-green-600"
      >
        Dismiss
      </button>
    </div>
  );
}

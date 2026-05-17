/**
 * FILE: frontend/components/dispatcher/task-feed.tsx
 * PURPOSE: Customer-facing task feed for the Dispatcher dashboard.
 *          Lists active + completed tasks in chronological order with
 *          pagination. Sub-KEI claimer wires data loading + Supabase
 *          realtime subscription.
 * KEI: 158 — Part 17 dashboard MVP (parent KEI-114).
 *
 * Stub: typed component shell + props interface. Render path uses the
 * shared shadcn Table primitives. No data fetching — caller passes
 * `tasks` in. Pagination + status transitions land in sub-PR.
 */

import * as React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";

export type DispatcherTaskStatus =
  | "pending"
  | "active"
  | "done"
  | "failed"
  | "cancelled";

export interface DispatcherTask {
  id: string;
  title: string;
  status: DispatcherTaskStatus;
  // LAW II Australia First — all financial values stored + displayed in $AUD.
  // Field name carries the unit so sub-KEI claimers can't silently propagate
  // USD through 10+ consumer files (anchored: feedback_currency_label_must_match_value 2026-05-08).
  cost_aud: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface TaskFeedProps {
  tasks: DispatcherTask[];
  loading?: boolean;
  emptyMessage?: string;
}

const STATUS_LABEL: Record<DispatcherTaskStatus, string> = {
  pending: "Pending",
  active: "Active",
  done: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
};

export function TaskFeed({
  tasks,
  loading = false,
  emptyMessage = "No tasks yet. Submit your first task to get started.",
}: TaskFeedProps) {
  if (loading) {
    return (
      <div data-testid="task-feed-loading" className="py-8 text-center text-sm text-muted-foreground">
        Loading tasks…
      </div>
    );
  }
  if (tasks.length === 0) {
    return (
      <div data-testid="task-feed-empty" className="py-8 text-center text-sm text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }
  return (
    <Table data-testid="task-feed-table">
      <TableHeader>
        <TableRow>
          <TableHead>Title</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Cost (AUD)</TableHead>
          <TableHead className="text-right">Submitted</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tasks.map((task) => (
          <TableRow key={task.id} data-task-id={task.id} data-task-status={task.status}>
            <TableCell className="font-medium">{task.title}</TableCell>
            <TableCell>{STATUS_LABEL[task.status]}</TableCell>
            <TableCell className="text-right">
              {task.cost_aud === null ? "—" : `A$${task.cost_aud.toFixed(2)}`}
            </TableCell>
            <TableCell className="text-right text-muted-foreground">
              {new Date(task.created_at).toLocaleString()}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

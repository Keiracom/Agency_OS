/**
 * FILE: frontend/components/ui/empty-state.tsx
 * PURPOSE: Empty state component for when no data is available
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-007
 */

"use client";

import { type ReactNode } from "react";
import { type LucideIcon, Inbox, Search, FileX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

/**
 * Empty state component - displays when no data is available
 */
export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn("text-center py-12", className)}>
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      {description && (
        <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
          {description}
        </p>
      )}
      {action}
    </div>
  );
}

/**
 * No search results state
 */
export function NoSearchResults({
  query,
  onClear,
}: {
  query: string;
  onClear?: () => void;
}) {
  return (
    <EmptyState
      icon={Search}
      title="No results found"
      description={`We couldn't find any results for "${query}". Try adjusting your search or filters.`}
      action={
        onClear && (
          <Button variant="outline" onClick={onClear}>
            Clear search
          </Button>
        )
      }
    />
  );
}

/**
 * No items state with create action
 */
export function NoItemsState({
  itemName,
  onCreate,
  canCreate = true,
}: {
  itemName: string;
  onCreate?: () => void;
  canCreate?: boolean;
}) {
  return (
    <EmptyState
      icon={FileX}
      title={`No ${itemName} yet`}
      description={
        canCreate
          ? `Get started by creating your first ${itemName.toLowerCase()}.`
          : `There are no ${itemName.toLowerCase()} to display.`
      }
      action={
        onCreate && canCreate && (
          <Button onClick={onCreate}>
            Create {itemName}
          </Button>
        )
      }
    />
  );
}

/**
 * Empty list in a card/table
 */
export function EmptyListRow({
  colSpan = 1,
  message = "No items to display",
}: {
  colSpan?: number;
  message?: string;
}) {
  return (
    <tr>
      <td
        colSpan={colSpan}
        className="h-24 text-center text-muted-foreground"
      >
        {message}
      </td>
    </tr>
  );
}

export default EmptyState;

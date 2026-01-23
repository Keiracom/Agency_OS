/**
 * FILE: frontend/components/onboarding/OnboardingChecklist.tsx
 * PURPOSE: Checklist component for onboarding setup tasks with progress tracking
 * PHASE: Fix #33 - Onboarding Progress Components
 */

"use client";

import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Check, Circle, ArrowRight, ExternalLink } from "lucide-react";
import Link from "next/link";

export interface ChecklistItem {
  /** Unique item identifier */
  id: string;
  /** Item title */
  title: string;
  /** Optional item description */
  description?: string;
  /** Whether the item is completed */
  completed: boolean;
  /** Optional link to navigate to for completing this item */
  href?: string;
  /** Whether the link is external */
  external?: boolean;
  /** Optional action label */
  actionLabel?: string;
}

export interface OnboardingChecklistProps {
  /** Checklist title */
  title?: string;
  /** Description shown below title */
  description?: string;
  /** List of checklist items */
  items: ChecklistItem[];
  /** Show progress bar */
  showProgress?: boolean;
  /** Optional click handler for items */
  onItemClick?: (itemId: string) => void;
  /** Additional class names */
  className?: string;
}

/**
 * Default checklist items for Agency OS onboarding
 */
export const DEFAULT_CHECKLIST_ITEMS: ChecklistItem[] = [
  {
    id: "verify-email",
    title: "Verify your email",
    description: "Confirm your email address to secure your account",
    completed: false,
    href: "/settings/profile",
    actionLabel: "Verify",
  },
  {
    id: "complete-profile",
    title: "Complete your profile",
    description: "Add your company details and preferences",
    completed: false,
    href: "/settings/profile",
    actionLabel: "Edit Profile",
  },
  {
    id: "connect-email",
    title: "Connect email account",
    description: "Link your email for sending outreach campaigns",
    completed: false,
    href: "/settings/email",
    actionLabel: "Connect",
  },
  {
    id: "connect-linkedin",
    title: "Connect LinkedIn",
    description: "Enable LinkedIn outreach and connection requests",
    completed: false,
    href: "/onboarding/linkedin",
    actionLabel: "Connect",
  },
  {
    id: "discover-icp",
    title: "Discover your ICP",
    description: "Let us analyze your website to find ideal customers",
    completed: false,
    href: "/onboarding",
    actionLabel: "Start",
  },
  {
    id: "create-campaign",
    title: "Create your first campaign",
    description: "Set up an outreach campaign to engage prospects",
    completed: false,
    href: "/dashboard/campaigns/new",
    actionLabel: "Create",
  },
  {
    id: "add-leads",
    title: "Add leads to campaign",
    description: "Import or manually add leads to start outreach",
    completed: false,
    href: "/dashboard/leads",
    actionLabel: "Add Leads",
  },
];

export function OnboardingChecklist({
  title = "Setup Checklist",
  description,
  items,
  showProgress = true,
  onItemClick,
  className,
}: OnboardingChecklistProps) {
  const completedCount = items.filter((item) => item.completed).length;
  const progressPercent = (completedCount / items.length) * 100;
  const allComplete = completedCount === items.length;

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">{title}</CardTitle>
            {description && (
              <p className="text-sm text-muted-foreground mt-1">{description}</p>
            )}
          </div>
          <span
            className={cn("text-sm font-medium", {
              "text-green-600": allComplete,
              "text-muted-foreground": !allComplete,
            })}
          >
            {completedCount}/{items.length}
          </span>
        </div>
        {showProgress && <Progress value={progressPercent} className="h-2 mt-3" />}
      </CardHeader>
      <CardContent>
        <ul className="space-y-1">
          {items.map((item) => (
            <ChecklistItemRow
              key={item.id}
              item={item}
              onItemClick={onItemClick}
            />
          ))}
        </ul>

        {allComplete && (
          <div className="mt-4 p-3 bg-green-50 dark:bg-green-950/20 rounded-lg text-center">
            <p className="text-sm font-medium text-green-700 dark:text-green-400">
              All setup tasks completed!
            </p>
            <p className="text-xs text-green-600 dark:text-green-500 mt-1">
              You are ready to start your outreach campaigns.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface ChecklistItemRowProps {
  item: ChecklistItem;
  onItemClick?: (itemId: string) => void;
}

function ChecklistItemRow({ item, onItemClick }: ChecklistItemRowProps) {
  const content = (
    <div className="flex items-center gap-3 p-2 rounded-lg transition-colors hover:bg-muted/50">
      {/* Checkbox indicator */}
      <div
        className={cn(
          "flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors",
          item.completed
            ? "bg-primary border-primary text-primary-foreground"
            : "border-muted-foreground/30 bg-background"
        )}
      >
        {item.completed && <Check className="h-3 w-3" />}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <span
          className={cn("text-sm font-medium block", {
            "line-through text-muted-foreground": item.completed,
          })}
        >
          {item.title}
        </span>
        {item.description && (
          <p className="text-xs text-muted-foreground truncate">
            {item.description}
          </p>
        )}
      </div>

      {/* Action indicator */}
      {!item.completed && (
        <div className="flex items-center gap-1 text-muted-foreground">
          {item.actionLabel && (
            <span className="text-xs hidden sm:inline">{item.actionLabel}</span>
          )}
          {item.external ? (
            <ExternalLink className="h-4 w-4" />
          ) : (
            <ArrowRight className="h-4 w-4" />
          )}
        </div>
      )}

      {/* Completed indicator */}
      {item.completed && (
        <span className="text-xs text-green-600 dark:text-green-400 font-medium">
          Done
        </span>
      )}
    </div>
  );

  // If item has a link and is not completed, make it clickable
  if (item.href && !item.completed) {
    if (item.external) {
      return (
        <li>
          <a
            href={item.href}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => onItemClick?.(item.id)}
          >
            {content}
          </a>
        </li>
      );
    }
    return (
      <li>
        <Link href={item.href} onClick={() => onItemClick?.(item.id)}>
          {content}
        </Link>
      </li>
    );
  }

  // Non-clickable item
  return (
    <li
      onClick={onItemClick ? () => onItemClick(item.id) : undefined}
      className={onItemClick ? "cursor-pointer" : undefined}
    >
      {content}
    </li>
  );
}

export default OnboardingChecklist;

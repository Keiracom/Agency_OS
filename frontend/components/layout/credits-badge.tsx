/**
 * FILE: frontend/components/layout/credits-badge.tsx
 * PURPOSE: Persistent badge showing remaining credits with visual warning
 * PHASE: 14 (Missing UI)
 * TASK: MUI-003
 */

"use client";

import Link from "next/link";
import { Coins } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useClient } from "@/hooks/use-client";
import { cn } from "@/lib/utils";

interface CreditsBadgeProps {
  className?: string;
}

/**
 * Credits badge component with color-coded warning levels.
 *
 * Color coding:
 * - Green (default): > 500 credits
 * - Yellow (warning): 100-500 credits
 * - Red (destructive): < 100 credits
 */
export function CreditsBadge({ className }: CreditsBadgeProps) {
  const { client, isLoading } = useClient();

  if (isLoading) {
    return (
      <Badge variant="secondary" className={cn("gap-1 animate-pulse", className)}>
        <Coins className="h-3 w-3" />
        <span className="w-8 h-3 bg-muted rounded" />
      </Badge>
    );
  }

  if (!client) {
    return null;
  }

  const credits = client.credits_remaining ?? 0;

  // Determine variant based on credit level
  const getVariant = (): "default" | "warning" | "destructive" => {
    if (credits > 500) return "default";
    if (credits > 100) return "warning";
    return "destructive";
  };

  const variant = getVariant();

  // Get appropriate styling
  const variantStyles = {
    default: "bg-green-100 text-green-800 hover:bg-green-100 dark:bg-green-900 dark:text-green-200",
    warning: "bg-yellow-100 text-yellow-800 hover:bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-200",
    destructive: "bg-red-100 text-red-800 hover:bg-red-100 dark:bg-red-900 dark:text-red-200",
  };

  const tooltipText =
    credits > 500
      ? "Credits remaining this month. Looking good!"
      : credits > 100
        ? "Credits running low. Consider upgrading your plan."
        : "Credits critically low! Actions may be limited.";

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Link href="/dashboard/settings?tab=billing">
            <Badge
              className={cn(
                "gap-1 cursor-pointer transition-colors",
                variantStyles[variant],
                className
              )}
            >
              <Coins className="h-3 w-3" />
              {credits.toLocaleString()}
            </Badge>
          </Link>
        </TooltipTrigger>
        <TooltipContent>
          <p>{tooltipText}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default CreditsBadge;

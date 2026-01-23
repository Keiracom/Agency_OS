"use client";

/**
 * LeadStatusProgress.tsx - Lead Funnel Status Visualization
 * Phase: Fix #29 - Frontend Components
 *
 * Displays a visual progress indicator showing a lead's position
 * in the sales funnel with stages and transition indicators.
 *
 * Stages (in order):
 * - New: Lead added to system
 * - Enriched: Data enrichment completed
 * - Scored: ALS score calculated
 * - In Sequence: Active in outreach campaign
 * - Converted: Deal closed
 *
 * Special statuses (not in funnel):
 * - Unsubscribed: Opted out
 * - Bounced: Email bounced
 */

import { cn } from "@/lib/utils";
import {
  Check,
  Circle,
  Loader2,
  XCircle,
  AlertTriangle,
  UserPlus,
  Database,
  Target,
  Mail,
  Trophy,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { LeadStatus } from "@/lib/api/types";

// ============================================
// Types
// ============================================

interface StatusTransition {
  status: LeadStatus;
  date?: string;
}

interface LeadStatusProgressProps {
  /** Current status of the lead */
  currentStatus: LeadStatus;
  /** Optional status transition history with dates */
  transitions?: StatusTransition[];
  /** Additional CSS classes */
  className?: string;
  /** Whether to show status labels below steps */
  showLabels?: boolean;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Callback when a stage is clicked (for status updates) */
  onStageClick?: (status: LeadStatus) => void;
  /** Whether clicking stages is enabled */
  clickable?: boolean;
}

// ============================================
// Constants
// ============================================

/** Ordered stages in the funnel (excludes special statuses) */
const FUNNEL_STAGES: LeadStatus[] = [
  "new",
  "enriched",
  "scored",
  "in_sequence",
  "converted",
];

/** Human-readable labels for each status */
const STATUS_LABELS: Record<LeadStatus, string> = {
  new: "New",
  enriched: "Enriched",
  scored: "Scored",
  in_sequence: "In Sequence",
  converted: "Converted",
  unsubscribed: "Unsubscribed",
  bounced: "Bounced",
};

/** Descriptions shown in tooltips */
const STATUS_DESCRIPTIONS: Record<LeadStatus, string> = {
  new: "Lead added to system",
  enriched: "Data enrichment completed",
  scored: "ALS score calculated",
  in_sequence: "Active in outreach campaign",
  converted: "Deal closed successfully",
  unsubscribed: "Opted out of communications",
  bounced: "Email address bounced",
};

/** Icons for each status */
const STATUS_ICONS: Record<LeadStatus, React.ReactNode> = {
  new: <UserPlus className="h-full w-full p-0.5" />,
  enriched: <Database className="h-full w-full p-0.5" />,
  scored: <Target className="h-full w-full p-0.5" />,
  in_sequence: <Mail className="h-full w-full p-0.5" />,
  converted: <Trophy className="h-full w-full p-0.5" />,
  unsubscribed: <XCircle className="h-full w-full p-0.5" />,
  bounced: <AlertTriangle className="h-full w-full p-0.5" />,
};

// ============================================
// Utilities
// ============================================

/**
 * Formats a date string for display
 */
function formatDate(dateString?: string): string {
  if (!dateString) return "";
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-AU", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

/**
 * Gets the transition date for a specific status from history
 */
function getTransitionDate(
  transitions: StatusTransition[] | undefined,
  status: LeadStatus
): string | undefined {
  if (!transitions) return undefined;
  const transition = transitions.find((t) => t.status === status);
  return transition?.date;
}

// ============================================
// Special Status Component
// ============================================

/**
 * Renders a special status badge for non-funnel statuses (bounced, unsubscribed)
 */
function SpecialStatusBadge({
  status,
  size,
}: {
  status: "unsubscribed" | "bounced";
  size: "sm" | "md" | "lg";
}) {
  const sizeClasses = {
    sm: { container: "h-5 w-5", text: "text-xs" },
    md: { container: "h-6 w-6", text: "text-sm" },
    lg: { container: "h-8 w-8", text: "text-base" },
  };

  const sizes = sizeClasses[size];
  const isUnsubscribed = status === "unsubscribed";

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "flex items-center justify-center rounded-full",
                sizes.container,
                isUnsubscribed
                  ? "bg-yellow-500/20 text-yellow-500"
                  : "bg-red-500/20 text-red-500"
              )}
            >
              {STATUS_ICONS[status]}
            </div>
            <span
              className={cn(
                "font-medium",
                sizes.text,
                isUnsubscribed ? "text-yellow-500" : "text-red-500"
              )}
            >
              {STATUS_LABELS[status]}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <p>{STATUS_DESCRIPTIONS[status]}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ============================================
// Main Component
// ============================================

export function LeadStatusProgress({
  currentStatus,
  transitions,
  className,
  showLabels = true,
  size = "md",
  onStageClick,
  clickable = false,
}: LeadStatusProgressProps) {
  // Handle special statuses that are not part of the funnel
  if (currentStatus === "bounced" || currentStatus === "unsubscribed") {
    return (
      <div className={cn("flex items-center", className)}>
        <SpecialStatusBadge status={currentStatus} size={size} />
      </div>
    );
  }

  const currentIndex = FUNNEL_STAGES.indexOf(currentStatus);

  // Size configuration
  const sizeConfig = {
    sm: {
      step: "h-5 w-5",
      icon: "h-3 w-3",
      line: "h-0.5",
      text: "text-xs",
      gap: "gap-1",
    },
    md: {
      step: "h-7 w-7",
      icon: "h-4 w-4",
      line: "h-0.5",
      text: "text-xs",
      gap: "gap-1.5",
    },
    lg: {
      step: "h-9 w-9",
      icon: "h-5 w-5",
      line: "h-1",
      text: "text-sm",
      gap: "gap-2",
    },
  };

  const sizes = sizeConfig[size];

  return (
    <TooltipProvider>
      <div className={cn("w-full", className)}>
        {/* Progress Steps */}
        <div className="flex items-center justify-between">
          {FUNNEL_STAGES.map((status, index) => {
            const isComplete = index < currentIndex;
            const isCurrent = index === currentIndex;
            const isPending = index > currentIndex;
            const transitionDate = getTransitionDate(transitions, status);
            const isClickable = clickable && onStageClick;

            return (
              <div key={status} className="flex flex-1 items-center">
                {/* Step Circle */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={() => isClickable && onStageClick?.(status)}
                      disabled={!isClickable}
                      className={cn(
                        "flex items-center justify-center rounded-full transition-all",
                        sizes.step,
                        {
                          // Completed step
                          "bg-emerald-500 text-white": isComplete,
                          // Current step
                          "bg-blue-500 text-white ring-2 ring-blue-500/30 ring-offset-2 ring-offset-background":
                            isCurrent,
                          // Pending step
                          "bg-muted text-muted-foreground": isPending,
                          // Clickable styles
                          "cursor-pointer hover:scale-110 hover:shadow-md":
                            isClickable,
                          "cursor-default": !isClickable,
                        }
                      )}
                    >
                      {isComplete ? (
                        <Check className={sizes.icon} />
                      ) : isCurrent ? (
                        <Loader2 className={cn(sizes.icon, "animate-spin")} />
                      ) : (
                        <Circle className={cn(sizes.icon, "opacity-50")} />
                      )}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    <div className="space-y-1">
                      <p className="font-medium">{STATUS_LABELS[status]}</p>
                      <p className="text-xs text-muted-foreground">
                        {STATUS_DESCRIPTIONS[status]}
                      </p>
                      {transitionDate && (
                        <p className="text-xs text-muted-foreground">
                          Reached: {formatDate(transitionDate)}
                        </p>
                      )}
                    </div>
                  </TooltipContent>
                </Tooltip>

                {/* Connector Line */}
                {index < FUNNEL_STAGES.length - 1 && (
                  <div
                    className={cn(
                      "flex-1 mx-1.5 rounded-full transition-colors",
                      sizes.line,
                      {
                        "bg-emerald-500": index < currentIndex,
                        "bg-muted": index >= currentIndex,
                      }
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Labels */}
        {showLabels && (
          <div className="mt-2 flex justify-between">
            {FUNNEL_STAGES.map((status, index) => {
              const isCurrent = index === currentIndex;
              const isComplete = index < currentIndex;

              return (
                <div
                  key={`label-${status}`}
                  className={cn(
                    "flex-1 text-center truncate px-0.5",
                    sizes.text,
                    {
                      "font-medium text-blue-500": isCurrent,
                      "text-emerald-500": isComplete,
                      "text-muted-foreground": !isCurrent && !isComplete,
                    }
                  )}
                >
                  {STATUS_LABELS[status]}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}

// ============================================
// Compact Variant
// ============================================

interface LeadStatusBadgeProps {
  status: LeadStatus;
  className?: string;
}

/**
 * A compact badge showing just the current status with an icon
 */
export function LeadStatusBadge({ status, className }: LeadStatusBadgeProps) {
  const isSpecial = status === "bounced" || status === "unsubscribed";
  const isFinal = status === "converted";

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              "inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium transition-colors",
              {
                // Special statuses
                "bg-red-500/20 text-red-500 border border-red-500/30":
                  status === "bounced",
                "bg-yellow-500/20 text-yellow-500 border border-yellow-500/30":
                  status === "unsubscribed",
                // Converted (success)
                "bg-emerald-500/20 text-emerald-500 border border-emerald-500/30":
                  isFinal,
                // In progress statuses
                "bg-blue-500/20 text-blue-500 border border-blue-500/30":
                  !isSpecial && !isFinal,
              },
              className
            )}
          >
            <span className="h-3.5 w-3.5">{STATUS_ICONS[status]}</span>
            <span>{STATUS_LABELS[status]}</span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="top">
          <p>{STATUS_DESCRIPTIONS[status]}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default LeadStatusProgress;

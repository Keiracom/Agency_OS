/**
 * FILE: frontend/components/leads/LeadQuickActions.tsx
 * PURPOSE: Quick action buttons for common lead operations
 * PHASE: Phase I Dashboard Redesign - Gap #28
 *
 * Features:
 * - Send Email action
 * - Make Call action
 * - Send SMS action
 * - View LinkedIn action
 * - Add Note action
 * - Responsive design (icon-only on mobile)
 * - Loading states during actions
 * - Disabled states when actions unavailable
 */

"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Mail,
  Phone,
  MessageSquare,
  Linkedin,
  StickyNote,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Lead } from "@/lib/api/types";

// ============================================
// Types
// ============================================

export type QuickActionType = "email" | "call" | "sms" | "linkedin" | "note";

export interface LeadQuickActionsProps {
  /** The lead to perform actions on */
  lead: Lead;
  /** Callback when an action is triggered */
  onAction?: (action: QuickActionType, lead: Lead) => void | Promise<void>;
  /** Currently loading action (disables that button) */
  loadingAction?: QuickActionType | null;
  /** Actions that are disabled */
  disabledActions?: QuickActionType[];
  /** Show labels on larger screens */
  showLabels?: boolean;
  /** Size variant */
  size?: "sm" | "default";
  /** Additional class names */
  className?: string;
}

// ============================================
// Action Configuration
// ============================================

interface ActionConfig {
  id: QuickActionType;
  label: string;
  icon: React.ReactNode;
  tooltip: string;
  /** Check if action is available for the lead */
  isAvailable: (lead: Lead) => boolean;
  /** Reason why action is unavailable */
  unavailableReason: (lead: Lead) => string;
}

const getActionConfigs = (iconSize: string): ActionConfig[] => [
  {
    id: "email",
    label: "Email",
    icon: <Mail className={iconSize} />,
    tooltip: "Send Email",
    isAvailable: (lead) => !!lead.email,
    unavailableReason: () => "No email address available",
  },
  {
    id: "call",
    label: "Call",
    icon: <Phone className={iconSize} />,
    tooltip: "Make Call",
    isAvailable: (lead) => !!lead.phone,
    unavailableReason: () => "No phone number available",
  },
  {
    id: "sms",
    label: "SMS",
    icon: <MessageSquare className={iconSize} />,
    tooltip: "Send SMS",
    isAvailable: (lead) => !!lead.phone,
    unavailableReason: () => "No phone number available",
  },
  {
    id: "linkedin",
    label: "LinkedIn",
    icon: <Linkedin className={iconSize} />,
    tooltip: "View LinkedIn",
    isAvailable: (lead) => !!lead.linkedin_url,
    unavailableReason: () => "No LinkedIn profile linked",
  },
  {
    id: "note",
    label: "Note",
    icon: <StickyNote className={iconSize} />,
    tooltip: "Add Note",
    isAvailable: () => true,
    unavailableReason: () => "",
  },
];

// ============================================
// Quick Action Button Component
// ============================================

interface QuickActionButtonProps {
  config: ActionConfig;
  lead: Lead;
  onAction?: (action: QuickActionType, lead: Lead) => void | Promise<void>;
  isLoading: boolean;
  isDisabled: boolean;
  showLabel: boolean;
  size: "sm" | "default";
}

function QuickActionButton({
  config,
  lead,
  onAction,
  isLoading,
  isDisabled,
  showLabel,
  size,
}: QuickActionButtonProps) {
  const [internalLoading, setInternalLoading] = React.useState(false);
  const isAvailable = config.isAvailable(lead);
  const isButtonDisabled = isDisabled || isLoading || internalLoading || !isAvailable;

  const handleClick = async () => {
    if (!onAction || isButtonDisabled) return;

    // Handle LinkedIn specially - open in new tab
    if (config.id === "linkedin" && lead.linkedin_url) {
      window.open(lead.linkedin_url, "_blank", "noopener,noreferrer");
      return;
    }

    try {
      setInternalLoading(true);
      await onAction(config.id, lead);
    } finally {
      setInternalLoading(false);
    }
  };

  const buttonContent = (
    <Button
      variant="ghost"
      size={size === "sm" ? "sm" : "default"}
      onClick={handleClick}
      disabled={isButtonDisabled}
      className={cn(
        "transition-colors",
        !showLabel && (size === "sm" ? "h-8 w-8 p-0" : "h-9 w-9 p-0"),
        showLabel && "gap-2",
        !isAvailable && "opacity-50 cursor-not-allowed"
      )}
    >
      {isLoading || internalLoading ? (
        <Loader2 className={cn(size === "sm" ? "h-4 w-4" : "h-4 w-4", "animate-spin")} />
      ) : (
        config.icon
      )}
      {showLabel && (
        <span className="hidden sm:inline">{config.label}</span>
      )}
    </Button>
  );

  const tooltipContent = !isAvailable
    ? config.unavailableReason(lead)
    : config.tooltip;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        {buttonContent}
      </TooltipTrigger>
      <TooltipContent side="bottom">
        <p>{tooltipContent}</p>
      </TooltipContent>
    </Tooltip>
  );
}

// ============================================
// Main Component
// ============================================

/**
 * LeadQuickActions provides quick action buttons for common lead operations.
 *
 * Actions:
 * - Send Email: Opens email composer (requires email)
 * - Make Call: Initiates phone call (requires phone)
 * - Send SMS: Opens SMS composer (requires phone)
 * - View LinkedIn: Opens LinkedIn profile (requires linkedin_url)
 * - Add Note: Opens note dialog (always available)
 *
 * Features:
 * - Responsive: Icon-only on mobile, with labels on desktop
 * - Loading states during async operations
 * - Disabled states when data is missing
 * - Tooltips explaining unavailable actions
 */
export function LeadQuickActions({
  lead,
  onAction,
  loadingAction = null,
  disabledActions = [],
  showLabels = false,
  size = "default",
  className,
}: LeadQuickActionsProps) {
  const iconSize = size === "sm" ? "h-4 w-4" : "h-4 w-4";
  const actionConfigs = React.useMemo(() => getActionConfigs(iconSize), [iconSize]);

  return (
    <TooltipProvider delayDuration={300}>
      <div
        className={cn(
          "flex items-center gap-1",
          className
        )}
        role="group"
        aria-label="Lead quick actions"
      >
        {actionConfigs.map((config) => (
          <QuickActionButton
            key={config.id}
            config={config}
            lead={lead}
            onAction={onAction}
            isLoading={loadingAction === config.id}
            isDisabled={disabledActions.includes(config.id)}
            showLabel={showLabels}
            size={size}
          />
        ))}
      </div>
    </TooltipProvider>
  );
}

export default LeadQuickActions;

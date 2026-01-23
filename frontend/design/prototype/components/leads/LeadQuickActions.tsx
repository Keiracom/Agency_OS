"use client";

import { Pause, Archive, Star, RefreshCw, Loader2 } from "lucide-react";

/**
 * LeadQuickActions props
 */
export interface LeadQuickActionsProps {
  /** Handler for pause action */
  onPause?: () => void;
  /** Handler for archive action */
  onArchive?: () => void;
  /** Handler for prioritize action */
  onPrioritize?: () => void;
  /** Handler for rescore action */
  onRescore?: () => void;
  /** Loading states for actions */
  loadingStates?: {
    pause?: boolean;
    archive?: boolean;
    prioritize?: boolean;
    rescore?: boolean;
  };
  /** Is lead currently paused */
  isPaused?: boolean;
  /** Is lead currently prioritized */
  isPrioritized?: boolean;
}

/**
 * Action button component
 */
function ActionButton({
  icon: Icon,
  label,
  onClick,
  isLoading,
  variant = "default",
  isActive,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick?: () => void;
  isLoading?: boolean;
  variant?: "default" | "danger" | "warning";
  isActive?: boolean;
}) {
  const baseClasses =
    "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 disabled:opacity-50";

  const variantClasses = {
    default: isActive
      ? "bg-[#3B82F6] text-white"
      : "bg-[#F1F5F9] text-[#64748B] hover:bg-[#E2E8F0] hover:text-[#1E293B]",
    danger: "bg-[#FEE2E2] text-[#991B1B] hover:bg-[#FECACA]",
    warning: isActive
      ? "bg-[#F97316] text-white"
      : "bg-[#FEF3C7] text-[#92400E] hover:bg-[#FDE68A]",
  };

  return (
    <button
      onClick={onClick}
      disabled={isLoading}
      className={`${baseClasses} ${variantClasses[variant]}`}
    >
      {isLoading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Icon className="h-4 w-4" />
      )}
      <span>{label}</span>
    </button>
  );
}

/**
 * LeadQuickActions - Quick action buttons component
 *
 * Features:
 * - Pause outreach button
 * - Archive button
 * - Prioritize button
 * - Re-score button
 * - Loading states
 * - Active states for toggleable actions
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Accent blue: #3B82F6 (accent-blue)
 * - Background: #F1F5F9
 * - Text secondary: #64748B
 *
 * Usage:
 * ```tsx
 * <LeadQuickActions
 *   onPause={() => handlePause()}
 *   onArchive={() => handleArchive()}
 *   onPrioritize={() => handlePrioritize()}
 *   onRescore={() => handleRescore()}
 *   loadingStates={{ rescore: true }}
 * />
 * ```
 */
export function LeadQuickActions({
  onPause,
  onArchive,
  onPrioritize,
  onRescore,
  loadingStates = {},
  isPaused = false,
  isPrioritized = false,
}: LeadQuickActionsProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <ActionButton
        icon={Pause}
        label={isPaused ? "Resume" : "Pause"}
        onClick={onPause}
        isLoading={loadingStates.pause}
        variant="warning"
        isActive={isPaused}
      />
      <ActionButton
        icon={Archive}
        label="Archive"
        onClick={onArchive}
        isLoading={loadingStates.archive}
        variant="danger"
      />
      <ActionButton
        icon={Star}
        label="Prioritize"
        onClick={onPrioritize}
        isLoading={loadingStates.prioritize}
        isActive={isPrioritized}
      />
      <ActionButton
        icon={RefreshCw}
        label="Re-score"
        onClick={onRescore}
        isLoading={loadingStates.rescore}
      />
    </div>
  );
}

export default LeadQuickActions;

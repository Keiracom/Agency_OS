"use client";

import { Check } from "lucide-react";

/**
 * Lead status type
 */
export type LeadStatus =
  | "new"
  | "enriched"
  | "scored"
  | "in_sequence"
  | "converted"
  | "unsubscribed"
  | "bounced";

/**
 * LeadStatusProgress props
 */
export interface LeadStatusProgressProps {
  /** Current lead status */
  status: LeadStatus;
}

/**
 * Status steps configuration
 */
const statusSteps = [
  { key: "new", label: "New" },
  { key: "enriched", label: "Enriched" },
  { key: "scored", label: "Scored" },
  { key: "in_sequence", label: "In Sequence" },
  { key: "converted", label: "Converted" },
] as const;

/**
 * Get step index for a status
 */
function getStepIndex(status: LeadStatus): number {
  const index = statusSteps.findIndex((s) => s.key === status);
  return index >= 0 ? index : 0;
}

/**
 * LeadStatusProgress - Status funnel progress component
 *
 * Features:
 * - Visual progress through status steps
 * - Completed steps shown with checkmark
 * - Current step highlighted
 * - Future steps grayed out
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Accent blue: #3B82F6 (current step)
 * - Accent green: #10B981 (completed)
 * - Text muted: #94A3B8 (future steps)
 *
 * Usage:
 * ```tsx
 * <LeadStatusProgress status="scored" />
 * ```
 */
export function LeadStatusProgress({ status }: LeadStatusProgressProps) {
  // Handle special statuses
  if (status === "unsubscribed" || status === "bounced") {
    return (
      <div className="flex items-center gap-2">
        <div className="px-3 py-1 bg-[#FEE2E2] rounded-full">
          <span className="text-sm font-medium text-[#991B1B] capitalize">
            {status === "unsubscribed" ? "Unsubscribed" : "Bounced"}
          </span>
        </div>
      </div>
    );
  }

  const currentIndex = getStepIndex(status);

  return (
    <div className="flex items-center gap-1">
      {statusSteps.map((step, index) => {
        const isCompleted = index < currentIndex;
        const isCurrent = index === currentIndex;
        const isFuture = index > currentIndex;

        return (
          <div key={step.key} className="flex items-center">
            {/* Step indicator */}
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 ${
                  isCompleted
                    ? "bg-[#10B981] text-white"
                    : isCurrent
                    ? "bg-[#3B82F6] text-white ring-4 ring-[#DBEAFE]"
                    : "bg-[#E2E8F0] text-[#94A3B8]"
                }`}
              >
                {isCompleted ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <span className="text-xs font-semibold">{index + 1}</span>
                )}
              </div>
              <span
                className={`mt-1 text-xs whitespace-nowrap ${
                  isCompleted
                    ? "text-[#10B981] font-medium"
                    : isCurrent
                    ? "text-[#3B82F6] font-semibold"
                    : "text-[#94A3B8]"
                }`}
              >
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {index < statusSteps.length - 1 && (
              <div
                className={`w-8 h-0.5 mx-1 transition-all duration-200 ${
                  index < currentIndex ? "bg-[#10B981]" : "bg-[#E2E8F0]"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default LeadStatusProgress;

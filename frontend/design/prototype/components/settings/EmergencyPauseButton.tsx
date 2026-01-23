"use client";

import { AlertTriangle, Pause, Play } from "lucide-react";

/**
 * EmergencyPauseButton props
 */
export interface EmergencyPauseButtonProps {
  /** Whether outreach is currently paused */
  isPaused: boolean;
  /** Timestamp when outreach was paused */
  pausedAt: string | null;
  /** Handler for pausing outreach */
  onPause: () => void;
  /** Handler for resuming outreach */
  onResume: () => void;
}

/**
 * Format a date string for display
 */
function formatPauseDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-AU", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

/**
 * EmergencyPauseButton - Prominent pause/resume control for all outreach
 *
 * Features:
 * - Red "Pause All Outreach" when outreach is active
 * - Green "Resume Outreach" when paused
 * - Shows pause timestamp when paused
 * - Warning styling to draw attention
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Error/Hot: #EF4444 (accent-red)
 * - Success: #10B981 (accent-green)
 * - Warning: #F97316 (accent-orange)
 * - Card background: #FFFFFF
 * - Card border: #E2E8F0
 */
export function EmergencyPauseButton({
  isPaused,
  pausedAt,
  onPause,
  onResume,
}: EmergencyPauseButtonProps) {
  return (
    <div
      className={`bg-white rounded-xl border shadow-sm p-6 ${
        isPaused ? "border-[#F97316]" : "border-[#E2E8F0]"
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div
          className={`p-2 rounded-lg ${
            isPaused ? "bg-[#FEF3C7]" : "bg-[#FEE2E2]"
          }`}
        >
          <AlertTriangle
            className={`h-5 w-5 ${isPaused ? "text-[#F97316]" : "text-[#EF4444]"}`}
          />
        </div>
        <h3 className="text-lg font-semibold text-[#1E293B]">
          Emergency Controls
        </h3>
      </div>

      {/* Status and Action */}
      {isPaused ? (
        <div className="space-y-4">
          <div className="p-4 bg-[#FFFBEB] rounded-lg border border-[#FDE68A]">
            <p className="text-sm font-medium text-[#92400E] mb-1">
              Outreach PAUSED
            </p>
            {pausedAt && (
              <p className="text-xs text-[#B45309]">
                Since {formatPauseDate(pausedAt)}
              </p>
            )}
          </div>
          <button
            onClick={onResume}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[#10B981] hover:bg-[#059669] text-white font-medium rounded-lg transition-colors shadow-lg shadow-green-500/25"
          >
            <Play className="h-5 w-5" />
            Resume Outreach
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-[#64748B]">
            All outreach is currently <span className="font-medium text-[#10B981]">ACTIVE</span>.
            Pausing will immediately stop all email, SMS, LinkedIn, and voice outreach.
          </p>
          <button
            onClick={onPause}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[#EF4444] hover:bg-[#DC2626] text-white font-medium rounded-lg transition-colors shadow-lg shadow-red-500/25"
          >
            <Pause className="h-5 w-5" />
            Pause All Outreach
          </button>
        </div>
      )}
    </div>
  );
}

export default EmergencyPauseButton;

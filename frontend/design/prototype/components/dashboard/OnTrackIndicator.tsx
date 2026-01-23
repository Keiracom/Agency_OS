"use client";

/**
 * OnTrackIndicator.tsx - Meeting pace status indicator
 * Design System: frontend/design/prototype/DESIGN_SYSTEM.md
 *
 * Features:
 * - Color coded badge (ahead/on_track/behind)
 * - Progress bar showing current vs target
 * - Target range display
 */

type TrackStatus = "ahead" | "on_track" | "behind";

interface OnTrackIndicatorProps {
  status: TrackStatus;
  current: number;
  targetLow: number;
  targetHigh: number;
}

const statusConfig: Record<TrackStatus, { label: string; bgColor: string; textColor: string; progressColor: string }> = {
  ahead: {
    label: "Ahead",
    bgColor: "bg-[#D1FAE5]",
    textColor: "text-[#047857]",
    progressColor: "bg-[#10B981]",
  },
  on_track: {
    label: "On Track",
    bgColor: "bg-[#DBEAFE]",
    textColor: "text-[#1D4ED8]",
    progressColor: "bg-[#3B82F6]",
  },
  behind: {
    label: "Behind",
    bgColor: "bg-[#FFEDD5]",
    textColor: "text-[#C2410C]",
    progressColor: "bg-[#F97316]",
  },
};

export function OnTrackIndicator({
  status,
  current,
  targetLow,
  targetHigh,
}: OnTrackIndicatorProps) {
  const config = statusConfig[status];

  // Calculate progress percentage (based on target high)
  const progressPercentage = Math.min((current / targetHigh) * 100, 100);

  // Calculate target range markers
  const targetLowMarker = (targetLow / targetHigh) * 100;

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-4">
      <div className="flex items-center justify-between mb-3">
        {/* Status badge */}
        <span
          className={`px-3 py-1 rounded-full text-sm font-medium ${config.bgColor} ${config.textColor}`}
        >
          {config.label}
        </span>

        {/* Current vs target text */}
        <span className="text-sm text-[#64748B]">
          <span className="font-semibold text-[#1E293B]">{current}</span>
          {" "}of{" "}
          <span className="font-medium">{targetLow}-{targetHigh}</span>
          {" "}target
        </span>
      </div>

      {/* Progress bar with target markers */}
      <div className="relative">
        {/* Background track */}
        <div className="h-2 bg-[#E2E8F0] rounded-full overflow-hidden">
          {/* Progress fill */}
          <div
            className={`h-full ${config.progressColor} rounded-full transition-all duration-500`}
            style={{ width: `${progressPercentage}%` }}
          />
        </div>

        {/* Target range indicators */}
        <div className="relative h-0">
          {/* Low target marker */}
          <div
            className="absolute -top-3 w-0.5 h-4 bg-[#94A3B8]"
            style={{ left: `${targetLowMarker}%` }}
          />
          {/* High target marker */}
          <div
            className="absolute -top-3 w-0.5 h-4 bg-[#94A3B8]"
            style={{ left: "100%" }}
          />
        </div>
      </div>

      {/* Target labels */}
      <div className="flex justify-between mt-1">
        <span className="text-xs text-[#94A3B8]">0</span>
        <span className="text-xs text-[#94A3B8]">{targetHigh}</span>
      </div>
    </div>
  );
}

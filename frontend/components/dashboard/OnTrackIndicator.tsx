/**
 * FILE: frontend/components/dashboard/OnTrackIndicator.tsx
 * PURPOSE: Visual indicator for meeting pace vs target
 * PHASE: Dashboard Redesign
 * SPEC: docs/architecture/frontend/DASHBOARD.md:380
 */

"use client";

import { cn } from "@/lib/utils";
import { TrendingUp, CheckCircle, AlertTriangle } from "lucide-react";

export type OnTrackStatus = "ahead" | "on_track" | "behind";

interface OnTrackIndicatorProps {
  status: OnTrackStatus;
  targetLow: number;
  targetHigh: number;
  current: number;
  className?: string;
}

const STATUS_CONFIG: Record<OnTrackStatus, {
  label: string;
  color: string;
  bgColor: string;
  icon: React.ElementType;
}> = {
  ahead: {
    label: "Ahead",
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10",
    icon: TrendingUp,
  },
  on_track: {
    label: "On track",
    color: "text-blue-400",
    bgColor: "bg-blue-500/10",
    icon: CheckCircle,
  },
  behind: {
    label: "Behind",
    color: "text-amber-400",
    bgColor: "bg-amber-500/10",
    icon: AlertTriangle,
  },
};

/**
 * Visual indicator for meeting pace:
 * - Green "Ahead" if > 110% expected
 * - Blue "On Track" if 90-110% expected
 * - Orange "Behind" if < 90% expected
 */
export function OnTrackIndicator({
  status,
  targetLow,
  targetHigh,
  current,
  className,
}: OnTrackIndicatorProps) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  // Calculate month progress (day of month / days in month)
  const now = new Date();
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const dayOfMonth = now.getDate();
  const monthProgress = (dayOfMonth / daysInMonth) * 100;

  // Calculate expected range at current point in month
  const expectedLow = Math.round((targetLow * dayOfMonth) / daysInMonth);
  const expectedHigh = Math.round((targetHigh * dayOfMonth) / daysInMonth);

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className={cn("flex items-center gap-1.5 px-2 py-1 rounded-md", config.bgColor)}>
        <Icon className={cn("h-3.5 w-3.5", config.color)} />
        <span className={cn("text-sm font-medium", config.color)}>
          {config.label}
        </span>
      </div>
      <span className="text-sm text-white/60">
        for {targetLow}-{targetHigh}
      </span>
      {/* Optional: Show expected range tooltip */}
      <span className="text-xs text-white/40 hidden sm:inline">
        (expect {expectedLow}-{expectedHigh} by day {dayOfMonth})
      </span>
    </div>
  );
}

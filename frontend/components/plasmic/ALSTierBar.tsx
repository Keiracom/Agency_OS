/**
 * FILE: frontend/components/plasmic/ALSTierBar.tsx
 * PURPOSE: ALS tier distribution bar - Plasmic design spec
 * DESIGN: Horizontal bar with tier colors and percentages
 */

"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

type ALSTier = "hot" | "warm" | "cool" | "cold" | "dead";

interface ALSTierBarProps {
  tier: ALSTier;
  count: number;
  percentage: number;
  className?: string;
}

const tierConfig: Record<ALSTier, { label: string; color: string; bg: string }> = {
  hot: { label: "Hot", color: "text-white", bg: "bg-[#EF4444]" },
  warm: { label: "Warm", color: "text-white", bg: "bg-[#F97316]" },
  cool: { label: "Cool", color: "text-white", bg: "bg-[#3B82F6]" },
  cold: { label: "Cold", color: "text-white", bg: "bg-[#6B7280]" },
  dead: { label: "Dead", color: "text-gray-700", bg: "bg-[#D1D5DB]" },
};

export function ALSTierBar({ tier, count, percentage, className }: ALSTierBarProps) {
  const config = tierConfig[tier];

  return (
    <div className={cn("space-y-2", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <Badge className={cn("text-xs font-medium", config.bg, config.color)}>
          {config.label}
        </Badge>
        <span className="text-sm font-medium text-white">{Math.round(percentage)}%</span>
      </div>

      {/* Progress Bar */}
      <div className="h-2 w-full rounded-full bg-white/10 overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500", config.bg)}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Count */}
      <p className="text-xs text-white/40 text-center">
        {count.toLocaleString()} leads
      </p>
    </div>
  );
}

interface ALSDistributionProps {
  distribution: { tier: ALSTier; count: number; percentage: number }[];
  className?: string;
}

export function ALSDistribution({ distribution, className }: ALSDistributionProps) {
  return (
    <div className={cn("grid grid-cols-5 gap-4", className)}>
      {distribution.map((item) => (
        <ALSTierBar
          key={item.tier}
          tier={item.tier}
          count={item.count}
          percentage={item.percentage}
        />
      ))}
    </div>
  );
}

export default ALSTierBar;

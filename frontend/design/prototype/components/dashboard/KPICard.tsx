"use client";

/**
 * KPICard.tsx - Hero metric card for dashboard
 * Design System: frontend/design/prototype/DESIGN_SYSTEM.md
 *
 * Features:
 * - Large value display (text-4xl)
 * - Trend indicator (green up, red down)
 * - Icon in top right
 * - White card with shadow
 */

import { LucideIcon, TrendingUp, TrendingDown } from "lucide-react";

interface KPICardProps {
  label: string;
  value: string | number;
  trend?: "up" | "down" | "neutral";
  trendLabel?: string;
  icon?: LucideIcon;
  subtitle?: string;
}

export function KPICard({
  label,
  value,
  trend,
  trendLabel,
  icon: Icon,
  subtitle,
}: KPICardProps) {
  const getTrendColor = () => {
    switch (trend) {
      case "up":
        return "text-[#10B981]"; // accent-green
      case "down":
        return "text-[#EF4444]"; // accent-red
      default:
        return "text-[#64748B]"; // text-secondary
    }
  };

  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : null;

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-6">
      {/* Header row: label + icon */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-[#64748B]">{label}</span>
        {Icon && <Icon className="h-5 w-5 text-[#94A3B8]" />}
      </div>

      {/* Large value */}
      <div className="text-4xl font-bold text-[#1E293B]">{value}</div>

      {/* Trend + subtitle row */}
      <div className="flex items-center gap-2 mt-1">
        {trend && TrendIcon && trendLabel && (
          <div className={`flex items-center gap-1 text-sm ${getTrendColor()}`}>
            <TrendIcon className="h-4 w-4" />
            <span>{trendLabel}</span>
          </div>
        )}
        {subtitle && (
          <span className="text-sm text-[#94A3B8]">{subtitle}</span>
        )}
      </div>
    </div>
  );
}

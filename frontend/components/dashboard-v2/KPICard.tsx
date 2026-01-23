/**
 * KPI Card - Displays key metrics with trend indicators
 * Open in Codux to adjust card styling, colors
 */

"use client";

import { ArrowUp, ArrowDown, Minus, LucideIcon } from "lucide-react";

interface KPICardProps {
  label: string;
  value: string | number;
  trend?: number;
  trendLabel?: string;
  icon?: LucideIcon;
  subtitle?: string;
}

export function KPICard({
  label,
  value,
  trend,
  trendLabel = "vs last month",
  icon: Icon,
  subtitle,
}: KPICardProps) {
  const getTrendColor = () => {
    if (trend === undefined) return "text-[#94A3B8]";
    if (trend > 0) return "text-[#10B981]";
    if (trend < 0) return "text-[#F59E0B]";
    return "text-[#94A3B8]";
  };

  const TrendIcon = trend === undefined ? null : trend > 0 ? ArrowUp : trend < 0 ? ArrowDown : Minus;

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] p-6 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-medium text-[#64748B]">{label}</span>
        {Icon && <Icon className="h-5 w-5 text-[#94A3B8]" />}
      </div>

      {/* Value */}
      <div className="mb-2">
        <span className="text-4xl font-bold text-[#1E293B]">{value}</span>
      </div>

      {/* Trend or Subtitle */}
      {subtitle ? (
        <p className="text-sm text-[#64748B]">{subtitle}</p>
      ) : trend !== undefined ? (
        <div className={`flex items-center gap-1 text-sm ${getTrendColor()}`}>
          {TrendIcon && <TrendIcon className="h-4 w-4" />}
          <span>{trend > 0 && "+"}{trend}</span>
          <span className="text-[#94A3B8]">{trendLabel}</span>
        </div>
      ) : null}
    </div>
  );
}

export default KPICard;

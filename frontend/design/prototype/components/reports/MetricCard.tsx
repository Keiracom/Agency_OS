"use client";

import { TrendingUp, TrendingDown, LucideIcon } from "lucide-react";

/**
 * MetricCard props
 */
export interface MetricCardProps {
  /** Label for the metric */
  label: string;
  /** Main value to display */
  value: string | number;
  /** Change percentage or value */
  change?: number;
  /** Label for the comparison period */
  changeLabel?: string;
  /** Icon component to display */
  icon?: LucideIcon;
}

/**
 * MetricCard - Report metric card component
 *
 * Features:
 * - Large value display
 * - Change indicator (up/down arrow, green/red)
 * - Comparison label
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Background: #FFFFFF (card-bg)
 * - Border: #E2E8F0 (card-border)
 * - Text primary: #1E293B
 * - Text secondary: #64748B
 * - Success: #10B981 (accent-green)
 * - Error: #EF4444 (accent-red)
 */
export function MetricCard({
  label,
  value,
  change,
  changeLabel = "vs last period",
  icon: Icon,
}: MetricCardProps) {
  const isPositive = change !== undefined && change >= 0;
  const hasChange = change !== undefined;

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-6">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-[#64748B]">{label}</span>
        {Icon && <Icon className="h-5 w-5 text-[#94A3B8]" />}
      </div>
      <div className="text-4xl font-bold text-[#1E293B] mb-2">{value}</div>
      {hasChange && (
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1 text-sm font-medium ${
              isPositive ? "text-[#10B981]" : "text-[#EF4444]"
            }`}
          >
            {isPositive ? (
              <TrendingUp className="h-4 w-4" />
            ) : (
              <TrendingDown className="h-4 w-4" />
            )}
            <span>
              {isPositive ? "+" : ""}
              {change}%
            </span>
          </div>
          <span className="text-sm text-[#94A3B8]">{changeLabel}</span>
        </div>
      )}
    </div>
  );
}

export default MetricCard;

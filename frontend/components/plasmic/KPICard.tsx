/**
 * FILE: frontend/components/plasmic/KPICard.tsx
 * PURPOSE: Key Performance Indicator card - Plasmic design spec
 * DESIGN: Dark card with large number, trend indicator
 */

"use client";

import { cn } from "@/lib/utils";
import { ArrowUp, ArrowDown, Minus, LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface KPICardProps {
  label: string;
  value: string | number;
  trend?: number;
  trendLabel?: string;
  icon?: LucideIcon;
  variant?: "dark" | "light";
  isLoading?: boolean;
  className?: string;
  subtitle?: string;
}

export function KPICard({
  label,
  value,
  trend,
  trendLabel = "vs last month",
  icon: Icon,
  variant = "dark",
  isLoading = false,
  className,
  subtitle,
}: KPICardProps) {
  const isDark = variant === "dark";

  if (isLoading) {
    return (
      <Card
        className={cn(
          "border",
          isDark
            ? "bg-[#1a1a1f] border-white/10"
            : "bg-bg-panel border-[#E5E7EB]",
          className
        )}
      >
        <CardContent className="p-6">
          <Skeleton className={cn("h-4 w-32 mb-4", isDark ? "bg-bg-panel/10" : "bg-panel")} />
          <Skeleton className={cn("h-10 w-20 mb-2", isDark ? "bg-bg-panel/10" : "bg-panel")} />
          <Skeleton className={cn("h-4 w-24", isDark ? "bg-bg-panel/10" : "bg-panel")} />
        </CardContent>
      </Card>
    );
  }

  const getTrendIcon = () => {
    if (trend === undefined || trend === null) return null;
    if (trend > 0) return ArrowUp;
    if (trend < 0) return ArrowDown;
    return Minus;
  };

  const getTrendColor = () => {
    if (trend === undefined || trend === null) return isDark ? "text-ink/40" : "text-ink-3";
    if (trend > 0) return "text-[#10B981]"; // emerald
    if (trend < 0) return "text-[#F59E0B]"; // amber (not red, less alarming)
    return isDark ? "text-ink/40" : "text-ink-3";
  };

  const TrendIcon = getTrendIcon();

  return (
    <Card
      className={cn(
        "border transition-shadow hover:shadow-lg",
        isDark
          ? "bg-[#1a1a1f] border-white/10"
          : "bg-bg-panel border-[#E5E7EB]",
        className
      )}
    >
      <CardContent className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <span
            className={cn(
              "text-sm font-medium",
              isDark ? "text-ink/60" : "text-[#6B7280]"
            )}
          >
            {label}
          </span>
          {Icon && (
            <Icon
              className={cn(
                "h-5 w-5",
                isDark ? "text-ink/40" : "text-[#9CA3AF]"
              )}
            />
          )}
        </div>

        {/* Value */}
        <div className="mb-2">
          <span
            className={cn(
              "text-4xl font-bold tracking-tight",
              isDark ? "text-ink" : "text-[#1F2937]"
            )}
          >
            {value}
          </span>
        </div>

        {/* Subtitle or Trend */}
        {subtitle ? (
          <p
            className={cn(
              "text-sm",
              isDark ? "text-ink/60" : "text-[#6B7280]"
            )}
          >
            {subtitle}
          </p>
        ) : trend !== undefined ? (
          <div className={cn("flex items-center gap-1 text-sm", getTrendColor())}>
            {TrendIcon && <TrendIcon className="h-4 w-4" />}
            <span>
              {trend > 0 && "+"}
              {trend}
            </span>
            <span className={isDark ? "text-ink/40" : "text-[#9CA3AF]"}>
              {trendLabel}
            </span>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default KPICard;

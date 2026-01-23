/**
 * FILE: frontend/components/dashboard/HeroMetricsCard.tsx
 * PURPOSE: Displays T1 Hero metrics (meetings booked, show rate, on-track status)
 * PHASE: Dashboard Redesign
 * SPEC: docs/architecture/frontend/DASHBOARD.md:258
 */

"use client";

import { cn } from "@/lib/utils";
import { Calendar, TrendingUp, ArrowUp, ArrowDown, Minus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { OnTrackIndicator, type OnTrackStatus } from "./OnTrackIndicator";
import { useDashboardMetrics } from "@/hooks/use-reports";

interface HeroMetricsCardProps {
  className?: string;
}

/**
 * Displays T1 Hero metrics:
 * - Meetings booked this month (large number)
 * - Show rate percentage
 * - On track/Ahead/Behind indicator
 * - vs last month comparison
 *
 * Design:
 * +------------------------------------------+
 * |  12 Meetings Booked        85% Show Rate |
 * |  On track for 15-25            +3 vs last month |
 * +------------------------------------------+
 */
export function HeroMetricsCard({ className }: HeroMetricsCardProps) {
  const { data: metrics, isLoading, error } = useDashboardMetrics();

  if (isLoading) {
    return <HeroMetricsCardSkeleton className={className} />;
  }

  if (error || !metrics) {
    return (
      <Card className={cn("bg-[#1a1a1f] border-white/10", className)}>
        <CardContent className="p-6">
          <div className="text-white/60 text-center py-4">
            Unable to load metrics
          </div>
        </CardContent>
      </Card>
    );
  }

  const { outcomes, comparison } = metrics;
  const vsLastMonth = comparison.meetings_vs_last_month;

  return (
    <Card className={cn("bg-[#1a1a1f] border-white/10", className)}>
      <CardContent className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Meetings Booked */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-white/60">
              <Calendar className="h-4 w-4" />
              <span className="text-sm font-medium">Meetings Booked</span>
            </div>
            <div className="flex items-baseline gap-3">
              <span className="text-4xl font-bold text-white">
                {outcomes.meetings_booked}
              </span>
              <ComparisonBadge value={vsLastMonth} label="vs last month" />
            </div>
            <OnTrackIndicator
              status={outcomes.status as OnTrackStatus}
              targetLow={comparison.tier_target_low}
              targetHigh={comparison.tier_target_high}
              current={outcomes.meetings_booked}
            />
          </div>

          {/* Show Rate */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-white/60">
              <TrendingUp className="h-4 w-4" />
              <span className="text-sm font-medium">Show Rate</span>
            </div>
            <div className="flex items-baseline gap-3">
              <span className="text-4xl font-bold text-white">
                {Math.round(outcomes.show_rate)}%
              </span>
              {outcomes.meetings_showed > 0 && (
                <span className="text-sm text-white/40">
                  ({outcomes.meetings_showed} showed)
                </span>
              )}
            </div>
            <div className="text-sm text-white/60">
              {outcomes.deals_created > 0 && (
                <span className="text-emerald-400">
                  {outcomes.deals_created} deal{outcomes.deals_created !== 1 ? "s" : ""} created
                </span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Comparison badge showing +/- vs last period
 */
function ComparisonBadge({ value, label }: { value: number; label: string }) {
  const isPositive = value > 0;
  const isNeutral = value === 0;

  const Icon = isNeutral ? Minus : isPositive ? ArrowUp : ArrowDown;
  const colorClass = isNeutral
    ? "text-white/40"
    : isPositive
    ? "text-emerald-400"
    : "text-amber-400";

  return (
    <div className={cn("flex items-center gap-1 text-sm", colorClass)}>
      <Icon className="h-3 w-3" />
      <span>
        {isPositive && "+"}
        {value}
      </span>
      <span className="text-white/40">{label}</span>
    </div>
  );
}

/**
 * Loading skeleton for HeroMetricsCard
 */
function HeroMetricsCardSkeleton({ className }: { className?: string }) {
  return (
    <Card className={cn("bg-[#1a1a1f] border-white/10", className)}>
      <CardContent className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Meetings Booked skeleton */}
          <div className="space-y-2">
            <Skeleton className="h-4 w-32 bg-white/10" />
            <Skeleton className="h-10 w-20 bg-white/10" />
            <Skeleton className="h-6 w-40 bg-white/10" />
          </div>
          {/* Show Rate skeleton */}
          <div className="space-y-2">
            <Skeleton className="h-4 w-24 bg-white/10" />
            <Skeleton className="h-10 w-16 bg-white/10" />
            <Skeleton className="h-4 w-32 bg-white/10" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

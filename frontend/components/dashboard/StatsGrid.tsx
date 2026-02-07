/**
 * StatsGrid.tsx - Dashboard Statistics Grid
 * Phase: Operation Modular Cockpit
 * 
 * Displays T1 Hero metrics per DASHBOARD.md spec:
 * - Meetings Booked
 * - Show Rate  
 * - Deals Created
 * - Campaign Status (On Track/Behind)
 * 
 * Does NOT show (per spec):
 * - Credits remaining
 * - Lead counts
 * - Cost per meeting
 */

"use client";

import {
  Calendar,
  CheckCircle,
  Briefcase,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  type LucideIcon,
} from "lucide-react";
import { useDashboardStats, useOnTrackStatus } from "@/hooks/use-dashboard-stats";

// ============================================
// Types
// ============================================

type ColorVariant = "blue" | "green" | "orange" | "purple" | "red";

interface StatCardProps {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon: LucideIcon;
  color?: ColorVariant;
  isLoading?: boolean;
}

interface StatsGridProps {
  /** Campaign ID to filter stats */
  campaignId?: string;
  /** Custom class name */
  className?: string;
}

// ============================================
// Color Configuration
// ============================================

const colorConfig: Record<ColorVariant, string> = {
  blue: "bg-blue-50 text-blue-600",
  green: "bg-emerald-50 text-emerald-600",
  orange: "bg-orange-50 text-orange-600",
  purple: "bg-purple-50 text-purple-600",
  red: "bg-red-50 text-red-600",
};

// ============================================
// StatCard Component
// ============================================

export function StatCard({
  label,
  value,
  change,
  changeLabel,
  icon: Icon,
  color = "blue",
  isLoading = false,
}: StatCardProps) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 shadow-md shadow-black/10 p-4 animate-pulse">
        <div className="flex items-start justify-between mb-2">
          <div className="h-3 w-24 bg-slate-200 rounded" />
          <div className="w-8 h-8 rounded-lg bg-slate-200" />
        </div>
        <div className="h-8 w-16 bg-slate-200 rounded mt-2" />
        <div className="h-3 w-20 bg-slate-200 rounded mt-2" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-md shadow-black/10 p-4">
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">
          {label}
        </span>
        <div
          className={`w-8 h-8 rounded-lg ${colorConfig[color]} flex items-center justify-center`}
        >
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      {change !== undefined && (
        <div className="flex items-center gap-1 mt-1">
          {change >= 0 ? (
            <ArrowUpRight className="w-3 h-3 text-emerald-500" />
          ) : (
            <ArrowDownRight className="w-3 h-3 text-red-500" />
          )}
          <span
            className={`text-xs font-medium ${
              change >= 0 ? "text-emerald-600" : "text-red-600"
            }`}
          >
            {change >= 0 ? "+" : ""}
            {change}%
          </span>
          {changeLabel && (
            <span className="text-xs text-slate-400">{changeLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================
// Status Card Component
// ============================================

function StatusCard({
  isLoading = false,
}: {
  isLoading?: boolean;
}) {
  const {
    status,
    label,
    color,
    meetingsBooked,
    targetHigh,
    progressPercent,
  } = useOnTrackStatus();

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 shadow-md shadow-black/10 p-4 animate-pulse">
        <div className="flex items-start justify-between mb-2">
          <div className="h-3 w-24 bg-slate-200 rounded" />
          <div className="w-8 h-8 rounded-lg bg-slate-200" />
        </div>
        <div className="h-8 w-20 bg-slate-200 rounded mt-2" />
        <div className="h-3 w-32 bg-slate-200 rounded mt-2" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-md shadow-black/10 p-4">
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">
          Campaign Status
        </span>
        <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
          <Activity className="w-4 h-4" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={`text-2xl font-bold ${color}`}>{label}</span>
      </div>
      <div className="text-xs text-slate-500 mt-1">
        {meetingsBooked} of {targetHigh} meetings target
      </div>
      {/* Progress bar */}
      <div className="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-emerald-500 rounded-full transition-all duration-500"
          style={{ width: `${progressPercent}%` }}
        />
      </div>
    </div>
  );
}

// ============================================
// StatsGrid Component
// ============================================

export function StatsGrid({ campaignId, className = "" }: StatsGridProps) {
  const { stats, isLoading } = useDashboardStats({ campaignId });

  return (
    <div className={`grid grid-cols-4 gap-4 ${className}`}>
      <StatCard
        label="Meetings Booked"
        value={stats?.meetingsBooked ?? 0}
        change={stats?.meetingsVsLastMonthPct}
        changeLabel="vs last month"
        icon={Calendar}
        color="blue"
        isLoading={isLoading}
      />
      <StatCard
        label="Show Rate"
        value={stats ? `${stats.showRate}%` : "0%"}
        change={5} // TODO: Calculate from API
        changeLabel="vs last month"
        icon={CheckCircle}
        color="green"
        isLoading={isLoading}
      />
      <StatCard
        label="Deals Created"
        value={stats?.dealsCreated ?? 0}
        change={50} // TODO: Calculate from API
        changeLabel="vs last month"
        icon={Briefcase}
        color="green"
        isLoading={isLoading}
      />
      <StatusCard isLoading={isLoading} />
    </div>
  );
}

export default StatsGrid;

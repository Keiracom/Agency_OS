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

// Glass-themed color configuration
const colorConfig: Record<ColorVariant, string> = {
  blue: "bg-blue-500/20 text-blue-400",
  green: "bg-emerald-500/20 text-emerald-400",
  orange: "bg-orange-500/20 text-orange-400",
  purple: "bg-purple-500/20 text-purple-400",
  red: "bg-red-500/20 text-red-400",
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
      <div className="bg-slate-900/40 backdrop-blur-md rounded-lg border border-white/10 shadow-lg shadow-black/20 p-4 animate-pulse">
        <div className="flex items-start justify-between mb-2">
          <div className="h-3 w-24 bg-white/10 rounded" />
          <div className="w-8 h-8 rounded-lg bg-white/10" />
        </div>
        <div className="h-8 w-16 bg-white/10 rounded mt-2" />
        <div className="h-3 w-20 bg-white/10 rounded mt-2" />
      </div>
    );
  }

  return (
    <div className="bg-slate-900/40 backdrop-blur-md rounded-lg border border-white/10 shadow-lg shadow-black/20 p-4 hover:bg-slate-900/50 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-medium text-slate-300 uppercase tracking-wide">
          {label}
        </span>
        <div
          className={`w-8 h-8 rounded-lg ${colorConfig[color]} flex items-center justify-center backdrop-blur-sm`}
        >
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-2xl font-bold text-white drop-shadow-sm">{value}</div>
      {change !== undefined && (
        <div className="flex items-center gap-1 mt-1">
          {change >= 0 ? (
            <ArrowUpRight className="w-3 h-3 text-emerald-400" />
          ) : (
            <ArrowDownRight className="w-3 h-3 text-red-400" />
          )}
          <span
            className={`text-xs font-medium ${
              change >= 0 ? "text-emerald-400" : "text-red-400"
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
      <div className="bg-slate-900/40 backdrop-blur-md rounded-lg border border-white/10 shadow-lg shadow-black/20 p-4 animate-pulse">
        <div className="flex items-start justify-between mb-2">
          <div className="h-3 w-24 bg-white/10 rounded" />
          <div className="w-8 h-8 rounded-lg bg-white/10" />
        </div>
        <div className="h-8 w-20 bg-white/10 rounded mt-2" />
        <div className="h-3 w-32 bg-white/10 rounded mt-2" />
      </div>
    );
  }

  // Map color to glass-friendly variants
  const glassColor = color.includes('emerald') ? 'text-emerald-400' : 
                     color.includes('yellow') ? 'text-yellow-400' : 
                     color.includes('red') ? 'text-red-400' : 'text-white';

  return (
    <div className="bg-slate-900/40 backdrop-blur-md rounded-lg border border-white/10 shadow-lg shadow-black/20 p-4 hover:bg-slate-900/50 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-medium text-slate-300 uppercase tracking-wide">
          Campaign Status
        </span>
        <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center backdrop-blur-sm">
          <Activity className="w-4 h-4" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={`text-2xl font-bold ${glassColor} drop-shadow-sm`}>{label}</span>
      </div>
      <div className="text-xs text-slate-400 mt-1">
        {meetingsBooked} of {targetHigh} meetings target
      </div>
      {/* Progress bar with glass effect */}
      <div className="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden">
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

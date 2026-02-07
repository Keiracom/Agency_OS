"use client";

/**
 * Bloomberg-style Stat Card
 * Matches: dashboard-v3.html stats-grid design
 */

import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  color?: "purple" | "green" | "blue" | "orange";
  className?: string;
}

const colorClasses = {
  purple: "text-[#9D5CFF]",
  green: "text-[#10B981]",
  blue: "text-[#3B82F6]",
  orange: "text-[#F59E0B]",
};

export function StatCard({ label, value, color = "purple", className }: StatCardProps) {
  return (
    <div
      className={cn(
        "bg-[#12121A] border border-[#2A2A3A] rounded-xl p-5",
        "hover:border-[#7C3AED]/30 transition-colors",
        className
      )}
    >
      <p className="text-sm text-[#A0A0B0] mb-2">{label}</p>
      <p className={cn("text-3xl font-bold font-mono", colorClasses[color])}>
        {value}
      </p>
    </div>
  );
}

interface StatsGridProps {
  stats: {
    label: string;
    value: string | number;
    color?: "purple" | "green" | "blue" | "orange";
  }[];
  className?: string;
}

export function StatsGrid({ stats, className }: StatsGridProps) {
  return (
    <div className={cn("grid grid-cols-4 gap-4", className)}>
      {stats.map((stat, index) => (
        <StatCard
          key={index}
          label={stat.label}
          value={stat.value}
          color={stat.color}
        />
      ))}
    </div>
  );
}

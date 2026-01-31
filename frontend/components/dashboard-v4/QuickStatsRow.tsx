/**
 * FILE: frontend/components/dashboard-v4/QuickStatsRow.tsx
 * PURPOSE: Row of 4 quick stat cards with premium effects
 * PHASE: Dashboard V4 Implementation + Mint Theme
 */

"use client";

import { Card } from "@/components/ui/card";
import { NumberTicker } from "@/components/ui/number-ticker";
import type { QuickStat } from "./types";

interface QuickStatsRowProps {
  stats: QuickStat[];
}

// Extract numeric value from stat string (e.g., "$12.4K" -> 12.4, "78%" -> 78)
function extractNumber(value: string): number | null {
  const match = value.match(/[\d.]+/);
  return match ? parseFloat(match[0]) : null;
}

function StatCard({ stat, index }: { stat: QuickStat; index: number }) {
  const changeColor = stat.changeDirection === "up" 
    ? "text-mint-500" 
    : stat.changeDirection === "down" 
      ? "text-red-500" 
      : "text-muted-foreground";

  const numericValue = extractNumber(stat.value);
  const prefix = stat.value.startsWith("$") ? "$" : "";
  const suffix = stat.value.endsWith("%") ? "%" : stat.value.includes("K") ? "K" : stat.value.includes("x") ? "x" : "";

  return (
    <Card className="p-5 text-center relative overflow-hidden group hover:shadow-md transition-shadow border-border/50 hover:border-mint-200">
      {/* Subtle gradient overlay on hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-mint-50/0 to-mint-100/0 group-hover:from-mint-50/50 group-hover:to-mint-100/30 transition-all duration-300" />
      
      <div className="relative">
        {numericValue !== null ? (
          <p className="text-3xl font-extrabold text-foreground">
            {prefix}
            <NumberTicker 
              value={numericValue} 
              delay={index * 0.1}
              decimalPlaces={numericValue % 1 !== 0 ? 1 : 0}
            />
            {suffix}
          </p>
        ) : (
          <p className="text-3xl font-extrabold text-foreground">{stat.value}</p>
        )}
        <p className="text-xs text-muted-foreground mt-1 uppercase tracking-wide font-medium">
          {stat.label}
        </p>
        <p className={`text-xs font-medium mt-2 ${changeColor}`}>
          {stat.change}
        </p>
      </div>
    </Card>
  );
}

export function QuickStatsRow({ stats }: QuickStatsRowProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map((stat, index) => (
        <StatCard key={index} stat={stat} index={index} />
      ))}
    </div>
  );
}

/**
 * FILE: frontend/components/dashboard-v4/QuickStatsRow.tsx
 * PURPOSE: Row of 4 quick stat cards
 * PHASE: Dashboard V4 Implementation
 */

"use client";

import { Card } from "@/components/ui/card";
import type { QuickStat } from "./types";

interface QuickStatsRowProps {
  stats: QuickStat[];
}

function StatCard({ stat }: { stat: QuickStat }) {
  const changeColor = stat.changeDirection === "up" 
    ? "text-emerald-500" 
    : stat.changeDirection === "down" 
      ? "text-red-500" 
      : "text-muted-foreground";

  return (
    <Card className="p-5 text-center">
      <p className="text-3xl font-extrabold text-foreground">{stat.value}</p>
      <p className="text-xs text-muted-foreground mt-1 uppercase tracking-wide font-medium">
        {stat.label}
      </p>
      <p className={`text-xs font-medium mt-2 ${changeColor}`}>
        {stat.change}
      </p>
    </Card>
  );
}

export function QuickStatsRow({ stats }: QuickStatsRowProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map((stat, index) => (
        <StatCard key={index} stat={stat} />
      ))}
    </div>
  );
}

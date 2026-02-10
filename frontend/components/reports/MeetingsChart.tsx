/**
 * MeetingsChart.tsx - CSS-based Bar Chart
 * Sprint 4 - Reports Page
 *
 * Meetings over time visualization without external charting libraries.
 */

"use client";

import { TrendingUp } from "lucide-react";
import type { MonthlyMeetings } from "@/data/mock-reports";

// ============================================
// Types
// ============================================

interface MeetingsChartProps {
  data: MonthlyMeetings[];
}

// ============================================
// Component
// ============================================

export function MeetingsChart({ data }: MeetingsChartProps) {
  // Calculate max value for relative heights
  const maxValue = Math.max(...data.map((d) => d.value));

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
        <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
          <TrendingUp className="w-4 h-4 text-accent-primary" />
          Meetings Over Time
        </div>
      </div>

      {/* Chart */}
      <div className="p-5">
        <div className="h-[200px] flex items-end gap-2 pt-4">
          {data.map((item, index) => {
            const heightPercent = (item.value / maxValue) * 100;

            return (
              <div
                key={item.month}
                className="flex-1 flex flex-col items-center h-full"
              >
                {/* Bar Container */}
                <div className="flex-1 w-full flex items-end justify-center">
                  <div
                    className="w-[70%] rounded-t transition-all duration-500 relative group
                      bg-gradient-to-t from-accent-primary/50 to-accent-primary
                      hover:brightness-110 cursor-pointer"
                    style={{ height: `${heightPercent}%` }}
                  >
                    {/* Tooltip on hover */}
                    <span
                      className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1
                        text-[11px] font-mono font-semibold text-text-primary
                        opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      {item.value}
                    </span>
                  </div>
                </div>

                {/* Label */}
                <div className="text-[11px] text-text-muted font-medium mt-2">
                  {item.month}
                </div>

                {/* Value */}
                <div className="text-xs font-mono font-semibold text-text-secondary mt-0.5">
                  {item.value}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default MeetingsChart;

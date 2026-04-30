/**
 * MeetingsChart.tsx - Meetings Over Time Bar Chart
 * CSS-only bar chart with amber accent
 */

"use client";

import { TrendingUp } from "lucide-react";
import { meetingsData } from "@/lib/mock/reports-data";

export function MeetingsChart() {
  const maxVal = Math.max(...meetingsData.map((d) => d.value));

  return (
    <div className="bg-bg-surface border border-default rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-default flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-[#D4956A]" />
        <h3 className="text-sm font-semibold text-ink">Meetings Over Time</h3>
      </div>
      <div className="p-5">
        <div className="h-48 flex items-end gap-2">
          {meetingsData.map((d) => {
            const height = (d.value / maxVal) * 100;
            return (
              <div key={d.month} className="flex-1 flex flex-col items-center h-full">
                <div className="flex-1 w-full flex items-end justify-center">
                  <div
                    className="w-[70%] rounded-t bg-gradient-to-t from-[#D4956A]/50 to-[#D4956A] hover:brightness-110 transition-all relative group"
                    style={{ height: `${height}%` }}
                  >
                    <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-xs font-mono font-semibold text-ink opacity-0 group-hover:opacity-100 transition-opacity">
                      {d.value}
                    </span>
                  </div>
                </div>
                <p className="text-[11px] text-ink-3 mt-2 font-medium">{d.month}</p>
                <p className="text-xs font-mono font-semibold text-ink-2">{d.value}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

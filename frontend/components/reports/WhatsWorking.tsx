/**
 * WhatsWorking.tsx - Insights Panel
 * Who Converts table, Best Timing, Discovery insight
 */

"use client";

import { Lightbulb, Flame } from "lucide-react";
import { whoConverts, bestTiming, discoveryInsight } from "@/lib/mock/reports-data";

export function WhatsWorking() {
  return (
    <div className="bg-bg-base border border-default rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-default flex items-center gap-2">
        <Lightbulb className="w-4 h-4 text-[#D4956A]" />
        <h3 className="text-sm font-semibold text-text-primary">What&apos;s Working</h3>
      </div>
      <div className="p-5">
        <div className="grid grid-cols-2 gap-3 mb-3">
          {/* Who Converts */}
          <div className="bg-bg-void rounded-lg p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-2">Who Converts</p>
            {whoConverts.map((item) => (
              <div key={item.label} className="flex justify-between items-center py-1.5">
                <span className="text-xs text-text-secondary">{item.label}</span>
                <span className="text-xs font-semibold font-mono text-[#22C55E]">{item.value}</span>
              </div>
            ))}
          </div>
          {/* Best Timing */}
          <div className="bg-bg-void rounded-lg p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-2">Best Timing</p>
            {bestTiming.map((item) => (
              <div key={item.label} className="flex justify-between items-center py-1.5">
                <span className="text-xs text-text-secondary">{item.label}</span>
                <span className="text-xs font-semibold font-mono text-[#22C55E]">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
        {/* Discovery Banner */}
        <div className="p-3 bg-gradient-to-r from-[#D4956A]/10 to-[#3B82F6]/10 border border-[#D4956A]/30 rounded-lg">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-[#D4956A] flex items-center gap-1.5 mb-1">
            <Flame className="w-3.5 h-3.5" />
            {discoveryInsight.label}
          </p>
          <p className="text-[13px] text-text-primary leading-relaxed">{discoveryInsight.text}</p>
        </div>
      </div>
    </div>
  );
}

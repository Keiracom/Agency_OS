/**
 * VoicePerformance.tsx - Smart Calling Performance
 * Stats row + Objections table
 */

"use client";

import { Phone } from "lucide-react";
import { voiceStats, objectionData } from "@/lib/mock/reports-data";

export function VoicePerformance() {
  return (
    <div className="bg-[#12121D] border border-[#1E1E2E] rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-[#1E1E2E] flex items-center gap-2">
        <Phone className="w-4 h-4 text-amber-500" />
        <h3 className="text-sm font-semibold text-[#F8F8FC]">Smart Calling Performance</h3>
      </div>
      <div className="p-5">
        {/* Stats Row */}
        <div className="grid grid-cols-4 gap-3 mb-4">
          {[
            { label: "Total Calls", value: voiceStats.totalCalls },
            { label: "Avg Duration", value: voiceStats.avgDuration },
            { label: "Connect Rate", value: `${voiceStats.connectRate}%` },
            { label: "Booking Rate", value: `${voiceStats.bookingRate}%` },
          ].map((stat) => (
            <div key={stat.label} className="bg-[#0A0A12] rounded-lg p-4 text-center">
              <p className="text-2xl font-bold font-mono text-[#F8F8FC]">{stat.value}</p>
              <p className="text-[10px] text-[#6E6E82] uppercase tracking-wider mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
        {/* Objections Table */}
        <div className="space-y-2">
          {objectionData.map((obj) => (
            <div key={obj.objection} className="flex items-center justify-between bg-[#0A0A12] rounded-md px-3 py-2.5">
              <span className="text-xs text-[#B4B4C4]">{obj.objection}</span>
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-[#6E6E82]">{obj.count}x</span>
                <span className="text-xs font-mono font-semibold text-[#22C55E]">{obj.recoveryRate}% recovered</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

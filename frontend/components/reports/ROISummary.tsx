/**
 * ROISummary.tsx - ROI Summary Cards
 * 3-column: Spend, Pipeline, ROI (AUD)
 */

"use client";

import { DollarSign } from "lucide-react";
import { roiSummary } from "@/lib/mock/reports-data";

export function ROISummary() {
  return (
    <div className="bg-[#12121D] border border-[#1E1E2E] rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-[#1E1E2E] flex items-center gap-2">
        <DollarSign className="w-4 h-4 text-[#D4956A]" />
        <h3 className="text-sm font-semibold text-[#F8F8FC]">ROI Summary</h3>
      </div>
      <div className="p-5">
        <div className="grid grid-cols-3 gap-4">
          {/* Spend */}
          <div className="bg-[#0A0A12] rounded-lg p-4 text-center">
            <p className="text-3xl font-extrabold font-mono text-red-400">
              ${(roiSummary.spend / 1000).toFixed(0)}K
            </p>
            <p className="text-[10px] text-[#6E6E82] uppercase tracking-wider mt-1">Total Spend</p>
          </div>
          {/* Pipeline */}
          <div className="bg-[#0A0A12] rounded-lg p-4 text-center">
            <p className="text-3xl font-extrabold font-mono text-[#22C55E]">
              ${(roiSummary.pipeline / 1000).toFixed(0)}K
            </p>
            <p className="text-[10px] text-[#6E6E82] uppercase tracking-wider mt-1">Pipeline Generated</p>
          </div>
          {/* ROI */}
          <div className="bg-[#0A0A12] rounded-lg p-4 text-center">
            <p className="text-3xl font-extrabold font-mono bg-gradient-to-r from-[#D4956A] to-[#3B82F6] bg-clip-text text-transparent">
              {roiSummary.roi}x
            </p>
            <p className="text-[10px] text-[#6E6E82] uppercase tracking-wider mt-1">Return on Investment</p>
          </div>
        </div>
      </div>
    </div>
  );
}

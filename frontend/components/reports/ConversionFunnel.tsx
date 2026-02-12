/**
 * ConversionFunnel.tsx - Conversion Funnel Visualization
 * Horizontal funnel bars with gradient fills
 */

"use client";

import { Shield } from "lucide-react";
import { funnelData } from "@/lib/mock/reports-data";

const stageGradients: Record<number, string> = {
  0: "from-[#D4956A]/30 to-[#D4956A]",
  1: "from-[#3B82F6]/30 to-[#3B82F6]",
  2: "from-[#14B8A6]/30 to-[#14B8A6]",
  3: "from-[#22C55E]/30 to-[#22C55E]",
};

export function ConversionFunnel() {
  return (
    <div className="bg-[#12121D] border border-[#1E1E2E] rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-[#1E1E2E] flex items-center gap-2">
        <Shield className="w-4 h-4 text-teal-400" />
        <h3 className="text-sm font-semibold text-[#F8F8FC]">Conversion Funnel</h3>
      </div>
      <div className="p-5 space-y-2">
        {funnelData.map((stage, i) => (
          <div key={stage.stage} className="flex items-center gap-4">
            <p className="w-20 text-xs font-medium text-[#B4B4C4] text-right">{stage.label}</p>
            <div className="flex-1 h-8 bg-[#0A0A12] rounded-md overflow-hidden relative">
              <div
                className={`h-full rounded-md flex items-center justify-end pr-3 bg-gradient-to-r ${stageGradients[i]}`}
                style={{ width: `${stage.percentage}%` }}
              >
                <span className="text-xs font-mono font-semibold text-white">{stage.percentage}%</span>
              </div>
            </div>
            <div className="w-24 text-right">
              <p className="text-sm font-mono font-bold text-[#F8F8FC]">{stage.count.toLocaleString()}</p>
              <p className="text-[10px] text-[#6E6E82]">{stage.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

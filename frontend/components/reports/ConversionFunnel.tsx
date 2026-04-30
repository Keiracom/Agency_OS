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
    <div className="bg-panel border border-default rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-default flex items-center gap-2">
        <Shield className="w-4 h-4 text-amber" />
        <h3 className="text-sm font-semibold text-ink">Conversion Funnel</h3>
      </div>
      <div className="p-5 space-y-2">
        {funnelData.map((stage, i) => (
          <div key={stage.stage} className="flex items-center gap-4">
            <p className="w-20 text-xs font-medium text-ink-2 text-right">{stage.label}</p>
            <div className="flex-1 h-8 bg-bg-cream rounded-md overflow-hidden relative">
              <div
                className={`h-full rounded-md flex items-center justify-end pr-3 bg-gradient-to-r ${stageGradients[i]}`}
                style={{ width: `${stage.percentage}%` }}
              >
                <span className="text-xs font-mono font-semibold text-ink">{stage.percentage}%</span>
              </div>
            </div>
            <div className="w-24 text-right">
              <p className="text-sm font-mono font-bold text-ink">{stage.count.toLocaleString()}</p>
              <p className="text-[10px] text-ink-3">{stage.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

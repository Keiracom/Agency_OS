/**
 * ConversionFunnel.tsx - Horizontal Bar Funnel Visualization
 * Sprint 4 - Reports Page
 *
 * Funnel visualization showing conversion stages.
 */

"use client";

import { Shield } from "lucide-react";
import type { FunnelStageData, FunnelStage } from "@/data/mock-reports";

// ============================================
// Types
// ============================================

interface ConversionFunnelProps {
  stages: FunnelStageData[];
}

// ============================================
// Stage Colors
// ============================================

const stageColors: Record<FunnelStage, string> = {
  contacted: "bg-gradient-to-r from-accent-primary/30 to-accent-primary",
  engaged: "bg-gradient-to-r from-accent-blue/30 to-accent-blue",
  replied: "bg-gradient-to-r from-accent-teal/30 to-accent-teal",
  booked: "bg-gradient-to-r from-status-success/30 to-status-success",
};

// ============================================
// Component
// ============================================

export function ConversionFunnel({ stages }: ConversionFunnelProps) {
  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
        <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
          <Shield className="w-4 h-4 text-accent-teal" />
          Conversion Funnel
        </div>
      </div>

      {/* Funnel */}
      <div className="p-5">
        <div className="flex flex-col gap-2">
          {stages.map((stage) => (
            <div key={stage.stage} className="flex items-center gap-4">
              {/* Label */}
              <div className="w-24 text-right text-xs font-medium text-text-secondary">
                {stage.label}
              </div>

              {/* Bar Container */}
              <div className="flex-1 h-8 bg-bg-base rounded-md overflow-hidden relative">
                <div
                  className={`h-full rounded-md flex items-center justify-end pr-3 transition-all duration-500 ${stageColors[stage.stage]}`}
                  style={{ width: `${Math.max(stage.percentage, 5)}%` }}
                >
                  <span className="text-xs font-mono font-semibold text-white">
                    {stage.percentage}%
                  </span>
                </div>
              </div>

              {/* Stats */}
              <div className="w-24 flex flex-col gap-0.5">
                <div className="text-sm font-mono font-bold text-text-primary">
                  {stage.count.toLocaleString()}
                </div>
                <div className="text-[10px] text-text-muted">
                  {stage.description}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ConversionFunnel;

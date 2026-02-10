/**
 * TierBreakdown.tsx - Tier Conversion Breakdown
 * Sprint 4 - Reports Page
 *
 * Displays tier breakdown with conversion rates and bar visualization.
 */

"use client";

import { Layers } from "lucide-react";
import type { TierBreakdown as TierBreakdownType, TierType } from "@/data/mock-reports";

// ============================================
// Types
// ============================================

interface TierBreakdownProps {
  tiers: TierBreakdownType[];
}

// ============================================
// Tier Configuration
// ============================================

const tierConfig: Record<
  TierType,
  { label: string; badgeStyle: string; barStyle: string }
> = {
  hot: {
    label: "HOT",
    badgeStyle: "bg-tier-hot/15 text-tier-hot",
    barStyle: "bg-gradient-to-r from-tier-hot/30 to-tier-hot",
  },
  warm: {
    label: "WARM",
    badgeStyle: "bg-tier-warm/15 text-tier-warm",
    barStyle: "bg-gradient-to-r from-tier-warm/30 to-tier-warm",
  },
  cool: {
    label: "COOL",
    badgeStyle: "bg-tier-cool/15 text-tier-cool",
    barStyle: "bg-gradient-to-r from-tier-cool/30 to-tier-cool",
  },
  cold: {
    label: "COLD",
    badgeStyle: "bg-gray-500/15 text-gray-500",
    barStyle: "bg-gradient-to-r from-gray-500/30 to-gray-500",
  },
};

// ============================================
// Component
// ============================================

export function TierBreakdown({ tiers }: TierBreakdownProps) {
  // Find max count for relative bar widths
  const maxCount = Math.max(...tiers.map((t) => t.count));

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
        <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
          <Layers className="w-4 h-4 text-accent-primary" />
          Conversion by Tier
        </div>
      </div>

      {/* Tier List */}
      <div className="p-5">
        <div className="flex flex-col gap-3">
          {tiers.map((tier) => {
            const config = tierConfig[tier.tier];
            const barWidth = (tier.count / maxCount) * 100;

            return (
              <div key={tier.tier} className="flex items-center gap-3">
                {/* Badge */}
                <div
                  className={`w-12 py-1.5 text-center text-[10px] font-bold uppercase rounded ${config.badgeStyle}`}
                >
                  {config.label}
                </div>

                {/* Bar Container */}
                <div className="flex-1 h-6 bg-bg-base rounded overflow-hidden">
                  <div
                    className={`h-full rounded flex items-center pl-2.5 transition-all duration-500 ${config.barStyle}`}
                    style={{ width: `${barWidth}%` }}
                  >
                    <span className="text-[11px] font-mono font-semibold text-white">
                      {tier.count.toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* Conversion Rate */}
                <div className="w-20 text-right">
                  <div className="text-sm font-mono font-bold text-text-primary">
                    {tier.conversionRate}%
                  </div>
                  <div className="text-[10px] text-text-muted">conv.</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default TierBreakdown;

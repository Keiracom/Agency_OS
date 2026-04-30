/**
 * TierConversion.tsx - Conversion Rate by Tier
 * Horizontal bars with tier-specific colors
 */

"use client";

import { BarChart3 } from "lucide-react";
import { tierData, type TierType } from "@/lib/mock/reports-data";

const tierConfig: Record<TierType, { label: string; badgeBg: string; badgeText: string; barGradient: string }> = {
  hot: {
    label: "HOT",
    badgeBg: "bg-amber-glow",
    badgeText: "text-amber",
    barGradient: "from-amber/30 to-amber",
  },
  warm: {
    label: "WARM",
    badgeBg: "bg-amber-500/15",
    badgeText: "text-amber-400",
    barGradient: "from-amber-500/30 to-amber-500",
  },
  cool: {
    label: "COOL",
    badgeBg: "bg-panel/15",
    badgeText: "text-ink-2",
    barGradient: "from-amber/30 to-amber",
  },
  cold: {
    label: "COLD",
    badgeBg: "bg-bg-surface0/15",
    badgeText: "text-ink-3",
    barGradient: "from-gray-500/30 to-gray-500",
  },
};

export function TierConversion() {
  const maxRate = Math.max(...tierData.map((t) => t.conversionRate));

  return (
    <div className="bg-panel border border-default rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-default flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-[#D4956A]" />
        <h3 className="text-sm font-semibold text-ink">Conversion Rate by Tier</h3>
      </div>
      <div className="p-5 space-y-3">
        {tierData.map((tier) => {
          const cfg = tierConfig[tier.tier];
          const barWidth = (tier.conversionRate / maxRate) * 100;
          return (
            <div key={tier.tier} className="flex items-center gap-3">
              <span className={`w-12 py-1 text-center text-[10px] font-bold uppercase rounded ${cfg.badgeBg} ${cfg.badgeText}`}>
                {cfg.label}
              </span>
              <div className="flex-1 h-6 bg-bg-cream rounded overflow-hidden">
                <div
                  className={`h-full rounded flex items-center pl-2.5 bg-gradient-to-r ${cfg.barGradient}`}
                  style={{ width: `${barWidth}%` }}
                >
                  <span className="text-[11px] font-mono font-semibold text-ink">{tier.count}</span>
                </div>
              </div>
              <div className="w-16 text-right">
                <p className="text-sm font-mono font-bold text-ink">{tier.conversionRate}%</p>
                <p className="text-[9px] text-ink-3">conv rate</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

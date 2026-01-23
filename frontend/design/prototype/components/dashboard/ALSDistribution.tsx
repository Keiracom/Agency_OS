"use client";

/**
 * ALSDistribution.tsx - Lead tier distribution bars
 * Design System: frontend/design/prototype/DESIGN_SYSTEM.md
 *
 * Features:
 * - 5 tier columns (Hot/Warm/Cool/Cold/Dead)
 * - Colored badges and progress bars
 * - Lead count below each
 */

type ALSTier = "hot" | "warm" | "cool" | "cold" | "dead";

interface TierData {
  tier: ALSTier;
  count: number;
  percentage: number;
}

interface ALSDistributionProps {
  data: TierData[];
}

const tierConfig: Record<ALSTier, { label: string; color: string; bgColor: string; barColor: string }> = {
  hot: {
    label: "Hot",
    color: "text-[#EF4444]",
    bgColor: "bg-[#FEE2E2]",
    barColor: "bg-[#EF4444]"
  },
  warm: {
    label: "Warm",
    color: "text-[#F97316]",
    bgColor: "bg-[#FFEDD5]",
    barColor: "bg-[#F97316]"
  },
  cool: {
    label: "Cool",
    color: "text-[#3B82F6]",
    bgColor: "bg-[#DBEAFE]",
    barColor: "bg-[#3B82F6]"
  },
  cold: {
    label: "Cold",
    color: "text-[#6B7280]",
    bgColor: "bg-[#F3F4F6]",
    barColor: "bg-[#6B7280]"
  },
  dead: {
    label: "Dead",
    color: "text-[#9CA3AF]",
    bgColor: "bg-[#F3F4F6]",
    barColor: "bg-[#D1D5DB]"
  },
};

// Fixed order for display
const tierOrder: ALSTier[] = ["hot", "warm", "cool", "cold", "dead"];

export function ALSDistribution({ data }: ALSDistributionProps) {
  // Create a map for quick lookup
  const tierMap = new Map(data.map((item) => [item.tier, item]));

  // Find max percentage for scaling bars
  const maxPercentage = Math.max(...data.map((d) => d.percentage), 1);

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-6">
      {/* Header */}
      <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider mb-6">
        Lead Distribution by ALS Tier
      </h2>

      {/* Tier columns */}
      <div className="flex items-end justify-between gap-4">
        {tierOrder.map((tier) => {
          const config = tierConfig[tier];
          const tierData = tierMap.get(tier) || { tier, count: 0, percentage: 0 };
          const barHeight = (tierData.percentage / maxPercentage) * 100;

          return (
            <div key={tier} className="flex-1 flex flex-col items-center">
              {/* Bar container */}
              <div className="w-full h-32 flex flex-col justify-end mb-3">
                <div
                  className={`w-full rounded-t-md ${config.barColor} transition-all duration-300`}
                  style={{ height: `${Math.max(barHeight, 4)}%` }}
                />
              </div>

              {/* Tier badge */}
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-medium ${config.bgColor} ${config.color} mb-2`}
              >
                {config.label}
              </span>

              {/* Count */}
              <span className="text-lg font-semibold text-[#1E293B]">
                {tierData.count}
              </span>

              {/* Percentage */}
              <span className="text-xs text-[#94A3B8]">
                {tierData.percentage}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

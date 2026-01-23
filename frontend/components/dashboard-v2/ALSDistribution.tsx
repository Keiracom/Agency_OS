/**
 * ALS Distribution - Lead quality tier breakdown
 * Open in Codux to adjust bar colors, spacing
 */

"use client";

type Tier = "hot" | "warm" | "cool" | "cold" | "dead";

interface TierData {
  tier: Tier;
  count: number;
  percentage: number;
}

interface ALSDistributionProps {
  data: TierData[];
}

const tierStyles: Record<Tier, { bg: string; label: string }> = {
  hot: { bg: "bg-[#EF4444]", label: "Hot" },
  warm: { bg: "bg-[#F97316]", label: "Warm" },
  cool: { bg: "bg-[#3B82F6]", label: "Cool" },
  cold: { bg: "bg-[#6B7280]", label: "Cold" },
  dead: { bg: "bg-[#D1D5DB]", label: "Dead" },
};

export function ALSDistribution({ data }: ALSDistributionProps) {
  return (
    <div className="grid grid-cols-5 gap-4">
      {data.map((item) => {
        const style = tierStyles[item.tier];
        return (
          <div key={item.tier} className="space-y-2">
            {/* Header */}
            <div className="flex items-center justify-between">
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium text-white ${style.bg}`}>
                {style.label}
              </span>
              <span className="text-sm font-medium text-[#1E293B]">
                {Math.round(item.percentage)}%
              </span>
            </div>

            {/* Bar */}
            <div className="h-2 w-full rounded-full bg-[#E2E8F0] overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${style.bg}`}
                style={{ width: `${item.percentage}%` }}
              />
            </div>

            {/* Count */}
            <p className="text-xs text-[#94A3B8] text-center">
              {item.count.toLocaleString()} leads
            </p>
          </div>
        );
      })}
    </div>
  );
}

export default ALSDistribution;

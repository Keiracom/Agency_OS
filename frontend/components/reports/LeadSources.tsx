/**
 * LeadSources.tsx - Lead Source Horizontal Bars
 * Shows source distribution with icons
 */

"use client";

import { MapPin, Rocket, Briefcase, Users, Globe } from "lucide-react";
import { leadSources } from "@/lib/mock/reports-data";

const iconMap: Record<string, React.ReactNode> = {
  "data-partner": <Rocket className="w-4 h-4" />,
  linkedin: <Briefcase className="w-4 h-4" />,
  referral: <Users className="w-4 h-4" />,
  website: <Globe className="w-4 h-4" />,
};

const colorMap: Record<string, { bg: string; bar: string }> = {
  "data-partner": { bg: "bg-[#D4956A]/15", bar: "bg-[#D4956A]" },
  linkedin: { bg: "bg-[#0A66C2]/15", bar: "bg-[#0A66C2]" },
  referral: { bg: "bg-amber/15", bar: "bg-amber" },
  website: { bg: "bg-amber-500/15", bar: "bg-amber-500" },
};

export function LeadSources() {
  return (
    <div className="bg-panel border border-default rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-default flex items-center gap-2">
        <MapPin className="w-4 h-4 text-ink-2" />
        <h3 className="text-sm font-semibold text-ink">Lead Sources</h3>
      </div>
      <div className="p-5 space-y-2.5">
        {leadSources.map((src) => {
          const colors = colorMap[src.id];
          return (
            <div key={src.id} className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-md flex items-center justify-center text-ink-2 ${colors.bg}`}>
                {iconMap[src.id]}
              </div>
              <div className="flex-1">
                <p className="text-[13px] font-medium text-ink">{src.name}</p>
                <div className="h-1 bg-bg-cream rounded-full mt-1.5 overflow-hidden">
                  <div className={`h-full rounded-full ${colors.bar}`} style={{ width: `${src.percentage}%` }} />
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-mono font-semibold text-ink">{src.count}</p>
                <p className="text-[10px] text-ink-3">{src.percentage}%</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

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
  referral: { bg: "bg-teal-400/15", bar: "bg-teal-400" },
  website: { bg: "bg-amber-500/15", bar: "bg-amber-500" },
};

export function LeadSources() {
  return (
    <div className="bg-[#12121D] border border-[#1E1E2E] rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-[#1E1E2E] flex items-center gap-2">
        <MapPin className="w-4 h-4 text-blue-500" />
        <h3 className="text-sm font-semibold text-[#F8F8FC]">Lead Sources</h3>
      </div>
      <div className="p-5 space-y-2.5">
        {leadSources.map((src) => {
          const colors = colorMap[src.id];
          return (
            <div key={src.id} className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-md flex items-center justify-center text-[#B4B4C4] ${colors.bg}`}>
                {iconMap[src.id]}
              </div>
              <div className="flex-1">
                <p className="text-[13px] font-medium text-[#F8F8FC]">{src.name}</p>
                <div className="h-1 bg-[#0A0A12] rounded-full mt-1.5 overflow-hidden">
                  <div className={`h-full rounded-full ${colors.bar}`} style={{ width: `${src.percentage}%` }} />
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-mono font-semibold text-[#F8F8FC]">{src.count}</p>
                <p className="text-[10px] text-[#6E6E82]">{src.percentage}%</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

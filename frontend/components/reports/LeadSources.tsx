/**
 * LeadSources.tsx - Lead Source List with Progress Bars
 * Sprint 4 - Reports Page
 *
 * Displays lead sources with counts and visual progress bars.
 */

"use client";

import { MapPin, Rocket, Briefcase, Users, Globe } from "lucide-react";
import type { LeadSource } from "@/data/mock-reports";

// ============================================
// Types
// ============================================

interface LeadSourcesProps {
  sources: LeadSource[];
}

// ============================================
// Icon Configuration
// ============================================

const sourceIcons: Record<LeadSource["icon"], React.ReactNode> = {
  "data-partner": <Rocket className="w-4 h-4" />,
  linkedin: <Briefcase className="w-4 h-4" />,
  referral: <Users className="w-4 h-4" />,
  website: <Globe className="w-4 h-4" />,
};

const iconBgColors: Record<LeadSource["icon"], string> = {
  "data-partner": "bg-accent-primary/15",
  linkedin: "bg-accent-blue/15",
  referral: "bg-accent-teal/15",
  website: "bg-status-warning/15",
};

const barColors: Record<LeadSource["color"], string> = {
  purple: "bg-accent-primary",
  blue: "bg-accent-blue",
  teal: "bg-accent-teal",
  amber: "bg-status-warning",
};

// ============================================
// Component
// ============================================

export function LeadSources({ sources }: LeadSourcesProps) {
  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
        <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
          <MapPin className="w-4 h-4 text-accent-blue" />
          Lead Sources
        </div>
      </div>

      {/* Source List */}
      <div className="p-5">
        <div className="flex flex-col gap-2.5">
          {sources.map((source) => (
            <div key={source.id} className="flex items-center gap-3">
              {/* Icon */}
              <div
                className={`w-8 h-8 rounded-md flex items-center justify-center text-text-secondary ${iconBgColors[source.icon]}`}
              >
                {sourceIcons[source.icon]}
              </div>

              {/* Info with Bar */}
              <div className="flex-1">
                <div className="text-sm font-medium text-text-primary">
                  {source.name}
                </div>
                <div className="h-1 bg-bg-base rounded-full mt-1.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${barColors[source.color]}`}
                    style={{ width: `${source.percentage}%` }}
                  />
                </div>
              </div>

              {/* Stats */}
              <div className="text-right">
                <div className="text-sm font-mono font-semibold text-text-primary">
                  {source.count.toLocaleString()}
                </div>
                <div className="text-[11px] text-text-muted">
                  {source.percentage}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default LeadSources;

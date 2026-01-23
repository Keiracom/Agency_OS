"use client";

import { Calendar, Users, MessageSquare, Layers } from "lucide-react";

/**
 * CampaignMetricsPanel props
 */
export interface CampaignMetricsPanelProps {
  /** Number of meetings booked this month */
  meetings: number;
  /** Show rate percentage (meetings showed / meetings booked) */
  showRate: number;
  /** Reply rate percentage */
  replyRate: number;
  /** Number of active sequences */
  activeSequences: number;
}

/**
 * CampaignMetricsPanel - Campaign stats display with 4 metric cards
 *
 * Features:
 * - 4 metric cards in a row
 * - Large numbers with labels
 * - Icon for each metric
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Card background: #FFFFFF
 * - Card border: #E2E8F0
 * - Text primary: #1E293B
 * - Text secondary: #64748B
 * - Icon color: #94A3B8
 */
export function CampaignMetricsPanel({
  meetings,
  showRate,
  replyRate,
  activeSequences,
}: CampaignMetricsPanelProps) {
  const metrics = [
    {
      label: "Meetings Booked",
      value: meetings,
      format: (v: number) => v.toString(),
      icon: Calendar,
    },
    {
      label: "Show Rate",
      value: showRate,
      format: (v: number) => `${v}%`,
      icon: Users,
    },
    {
      label: "Reply Rate",
      value: replyRate,
      format: (v: number) => `${v}%`,
      icon: MessageSquare,
    },
    {
      label: "Active Sequences",
      value: activeSequences,
      format: (v: number) => v.toString(),
      icon: Layers,
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric) => {
        const Icon = metric.icon;
        return (
          <div
            key={metric.label}
            className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-6"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-[#64748B]">{metric.label}</span>
              <Icon className="h-5 w-5 text-[#94A3B8]" />
            </div>
            <div className="text-3xl font-bold text-[#1E293B]">
              {metric.format(metric.value)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default CampaignMetricsPanel;

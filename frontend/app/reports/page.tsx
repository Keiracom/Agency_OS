/**
 * Reports Page (/reports)
 * Sprint 4 - Analytics Terminal
 *
 * Multi-channel performance intelligence dashboard.
 */

"use client";

import { useState } from "react";
import { Download, FileText } from "lucide-react";
import AppShell from "@/components/layout/AppShell";
import {
  ExecSummaryCard,
  ChannelMatrix,
  MeetingsChart,
  ConversionFunnel,
  ResponseRates,
  InsightsCard,
  LeadSources,
  DateSelector,
  TierBreakdown,
} from "@/components/reports";
import {
  execMetrics,
  channelPerformance,
  monthlyMeetings,
  funnelStages,
  responseRates,
  insightBoxes,
  discoveryInsight,
  leadSources,
  tierBreakdown,
  dateRangeOptions,
  type DateRange,
} from "@/data/mock-reports";

export default function ReportsPage() {
  const [selectedDateRange, setSelectedDateRange] = useState<DateRange>("thisMonth");

  return (
    <AppShell pageTitle="Analytics Terminal">
      {/* Header Row with Date Selector and Actions */}
      <div className="p-6 pb-0">
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-sm text-text-muted">
              Multi-Channel Performance Intelligence
            </p>
          </div>
          <div className="flex items-center gap-4">
            <DateSelector
              options={dateRangeOptions}
              selected={selectedDateRange}
              onSelect={setSelectedDateRange}
            />
            <div className="flex gap-2">
              <button
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium
                  text-text-secondary bg-transparent border border-border-default rounded-lg
                  hover:bg-bg-surface-hover hover:border-border-strong transition-all"
              >
                <Download className="w-4 h-4" />
                CSV
              </button>
              <button
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium
                  text-white bg-accent-primary rounded-lg
                  hover:bg-accent-primary-hover transition-all"
              >
                <FileText className="w-4 h-4" />
                Export PDF
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6 pt-0">
        {/* Executive Summary Row */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {execMetrics.map((metric) => (
            <ExecSummaryCard key={metric.id} metric={metric} />
          ))}
        </div>

        {/* Channel Performance Matrix */}
        <ChannelMatrix channels={channelPerformance} />

        {/* Charts Row */}
        <div className="grid grid-cols-2 gap-6 mb-6">
          <MeetingsChart data={monthlyMeetings} />
          <ConversionFunnel stages={funnelStages} />
        </div>

        {/* Key Metrics Row */}
        <div className="grid grid-cols-3 gap-6 mb-6">
          <ResponseRates rates={responseRates} />
          <InsightsCard insights={insightBoxes} discovery={discoveryInsight} />
          <LeadSources sources={leadSources} />
        </div>

        {/* Bottom Row */}
        <div className="grid grid-cols-2 gap-6">
          <TierBreakdown tiers={tierBreakdown} />
          {/* Placeholder for additional card if needed */}
          <div className="bg-bg-surface border border-border-subtle rounded-xl p-5 flex items-center justify-center">
            <div className="text-center">
              <div className="text-2xl mb-2">📊</div>
              <div className="text-sm text-text-muted">
                Additional analytics coming soon
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

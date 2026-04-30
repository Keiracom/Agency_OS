/**
 * Analytics Terminal - Reports Page
 * Sprint 3c - Bloomberg Terminal aesthetic with amber accents
 * Route: /dashboard/reports
 */

"use client";

import { useState } from "react";
import type { DateRange } from "@/lib/mock/reports-data";
import {
  ReportsHeader,
  HeroMetrics,
  ChannelMatrix,
  MeetingsChart,
  ConversionFunnel,
  ResponseRates,
  WhatsWorking,
  LeadSources,
  TierConversion,
  VoicePerformance,
  ROISummary,
} from "@/components/reports";

export default function ReportsPage() {
  const [dateRange, setDateRange] = useState<DateRange>("thisMonth");

  return (
    <div className="min-h-screen bg-[#0C0A08]">
      {/* Header */}
      <ReportsHeader selectedRange={dateRange} onRangeChange={setDateRange} />

      {/* Content */}
      <div className="p-6 max-w-[1600px] mx-auto">
        {/* 1. Hero Metrics */}
        <HeroMetrics />

        {/* 2. Channel Matrix */}
        <ChannelMatrix />

        {/* 3. Charts Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-6 mb-6">
          <MeetingsChart />
          <ConversionFunnel />
        </div>

        {/* 4. Middle Row (3-col) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-6 mb-6">
          <ResponseRates />
          <WhatsWorking />
          <LeadSources />
        </div>

        {/* 5. Tier Conversion */}
        <div className="mb-6">
          <TierConversion />
        </div>

        {/* 6. Voice Performance */}
        <div className="mb-6">
          <VoicePerformance />
        </div>

        {/* 7. ROI Summary */}
        <ROISummary />
      </div>
    </div>
  );
}

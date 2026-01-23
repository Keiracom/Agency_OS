"use client";

import { useState } from "react";
import { Calendar, Users, MessageSquare, TrendingUp, Target } from "lucide-react";
import { DashboardShell } from "../layout";
import { MetricCard } from "./MetricCard";
import { DateRangePicker } from "./DateRangePicker";
import { TrendChart, TrendDataPoint } from "./TrendChart";
import { ChannelBreakdown, ChannelMetrics } from "./ChannelBreakdown";
import { CampaignPerformance, CampaignPerformanceData } from "./CampaignPerformance";
import { DonutChart, DonutChartDataPoint } from "./DonutChart";

// =============================================================================
// DEMO DATA - Static data for prototype
// =============================================================================

/**
 * Demo hero metrics
 */
const demoMetrics = {
  meetings: { value: 47, change: 12, label: "Meetings Booked" },
  showRate: { value: "78%", change: 5, label: "Show Rate" },
  replyRate: { value: "4.2%", change: -0.3, label: "Reply Rate" },
  activeLeads: { value: 1248, change: 8, label: "Active Leads" },
};

/**
 * Demo trend data - 30 days of meetings
 */
const demoTrendData: TrendDataPoint[] = Array.from({ length: 30 }, (_, i) => {
  const date = new Date();
  date.setDate(date.getDate() - (29 - i));
  // Simulate some variation with weekday patterns
  const isWeekend = date.getDay() === 0 || date.getDay() === 6;
  const baseValue = isWeekend ? 0 : Math.floor(Math.random() * 3) + 1;
  return {
    date: date.toISOString().split("T")[0],
    count: baseValue,
  };
});

/**
 * Demo channel metrics
 */
const demoChannelMetrics: ChannelMetrics[] = [
  {
    channel: "email",
    sent: 12450,
    delivered: 11830,
    opened: 4260,
    replied: 485,
    meetings: 28,
  },
  {
    channel: "linkedin",
    sent: 2100,
    delivered: 2058,
    opened: 1680,
    replied: 168,
    meetings: 12,
  },
  {
    channel: "sms",
    sent: 850,
    delivered: 833,
    opened: 791,
    replied: 67,
    meetings: 5,
  },
  {
    channel: "voice",
    sent: 320,
    delivered: 256,
    opened: 256,
    replied: 89,
    meetings: 2,
  },
];

/**
 * Demo campaign performance data
 */
const demoCampaignData: CampaignPerformanceData[] = [
  {
    id: "1",
    name: "Q1 Tech Startups",
    status: "active",
    sent: 4500,
    delivered: 4320,
    opened: 1728,
    replied: 194,
    meetings: 18,
    replyRate: 4.5,
    meetingRate: 0.42,
  },
  {
    id: "2",
    name: "Financial Services",
    status: "active",
    sent: 3200,
    delivered: 3040,
    opened: 1064,
    replied: 122,
    meetings: 11,
    replyRate: 4.0,
    meetingRate: 0.36,
  },
  {
    id: "3",
    name: "Healthcare Decision Makers",
    status: "active",
    sent: 2800,
    delivered: 2660,
    opened: 931,
    replied: 106,
    meetings: 9,
    replyRate: 4.0,
    meetingRate: 0.34,
  },
  {
    id: "4",
    name: "E-commerce Growth",
    status: "paused",
    sent: 1800,
    delivered: 1710,
    opened: 547,
    replied: 51,
    meetings: 5,
    replyRate: 3.0,
    meetingRate: 0.29,
  },
  {
    id: "5",
    name: "Manufacturing Leaders",
    status: "completed",
    sent: 3420,
    delivered: 3249,
    opened: 1040,
    replied: 97,
    meetings: 4,
    replyRate: 3.0,
    meetingRate: 0.12,
  },
];

/**
 * Demo ALS distribution data
 */
const demoALSDistribution: DonutChartDataPoint[] = [
  { label: "Hot (85-100)", value: 124, color: "#EF4444" },
  { label: "Warm (60-84)", value: 312, color: "#F97316" },
  { label: "Cool (35-59)", value: 498, color: "#3B82F6" },
  { label: "Cold (20-34)", value: 214, color: "#6B7280" },
  { label: "Dead (<20)", value: 100, color: "#D1D5DB" },
];

// =============================================================================
// REPORTS PAGE COMPONENT
// =============================================================================

/**
 * ReportsPage - Full reports dashboard page
 *
 * Features:
 * - DashboardShell layout wrapper
 * - DateRangePicker at top
 * - Hero metrics row (Meetings, Show Rate, Reply Rate, Active Leads)
 * - Meetings trend chart with target line
 * - Channel breakdown table
 * - Campaign performance section
 * - ALS distribution donut chart
 *
 * This is a PROTOTYPE with static demo data.
 */
export function ReportsPage() {
  const [dateRange, setDateRange] = useState<{ start?: Date; end?: Date }>({});

  const handleDateChange = (start: Date, end: Date) => {
    setDateRange({ start, end });
    // In production, this would trigger data refetch
    console.log("Date range changed:", start, end);
  };

  return (
    <DashboardShell title="Reports" activePath="/reports">
      <div className="space-y-6">
        {/* Date Range Picker */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-[#1E293B]">
              Performance Overview
            </h2>
            <p className="text-sm text-[#64748B]">
              Track your outreach performance and meeting conversions
            </p>
          </div>
          <DateRangePicker
            startDate={dateRange.start}
            endDate={dateRange.end}
            onChange={handleDateChange}
          />
        </div>

        {/* Hero Metrics Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label={demoMetrics.meetings.label}
            value={demoMetrics.meetings.value}
            change={demoMetrics.meetings.change}
            changeLabel="vs last 30 days"
            icon={Calendar}
          />
          <MetricCard
            label={demoMetrics.showRate.label}
            value={demoMetrics.showRate.value}
            change={demoMetrics.showRate.change}
            changeLabel="vs last 30 days"
            icon={Target}
          />
          <MetricCard
            label={demoMetrics.replyRate.label}
            value={demoMetrics.replyRate.value}
            change={demoMetrics.replyRate.change}
            changeLabel="vs last 30 days"
            icon={MessageSquare}
          />
          <MetricCard
            label={demoMetrics.activeLeads.label}
            value={demoMetrics.activeLeads.value.toLocaleString()}
            change={demoMetrics.activeLeads.change}
            changeLabel="vs last 30 days"
            icon={Users}
          />
        </div>

        {/* Meetings Trend Chart */}
        <TrendChart data={demoTrendData} target={2} />

        {/* Channel Breakdown */}
        <ChannelBreakdown channels={demoChannelMetrics} />

        {/* Campaign Performance */}
        <CampaignPerformance campaigns={demoCampaignData} />

        {/* ALS Distribution Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* ALS Distribution Donut */}
          <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-6">
            <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider mb-6">
              ALS Score Distribution
            </h2>
            <div className="flex justify-center">
              <DonutChart
                data={demoALSDistribution}
                size={200}
                centerLabel="Total Leads"
                centerValue={demoALSDistribution.reduce((sum, d) => sum + d.value, 0)}
              />
            </div>
          </div>

          {/* Quick Stats */}
          <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-6">
            <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider mb-6">
              Key Insights
            </h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-[#F8FAFC] rounded-lg">
                <div>
                  <span className="text-sm text-[#64748B]">Best Performing Channel</span>
                  <p className="text-lg font-semibold text-[#1E293B]">LinkedIn</p>
                </div>
                <div className="text-right">
                  <span className="text-sm text-[#64748B]">Reply Rate</span>
                  <p className="text-lg font-semibold text-[#10B981]">8.2%</p>
                </div>
              </div>
              <div className="flex items-center justify-between p-4 bg-[#F8FAFC] rounded-lg">
                <div>
                  <span className="text-sm text-[#64748B]">Top Campaign</span>
                  <p className="text-lg font-semibold text-[#1E293B]">Q1 Tech Startups</p>
                </div>
                <div className="text-right">
                  <span className="text-sm text-[#64748B]">Meetings</span>
                  <p className="text-lg font-semibold text-[#3B82F6]">18</p>
                </div>
              </div>
              <div className="flex items-center justify-between p-4 bg-[#F8FAFC] rounded-lg">
                <div>
                  <span className="text-sm text-[#64748B]">Hot Leads</span>
                  <p className="text-lg font-semibold text-[#1E293B]">124 leads</p>
                </div>
                <div className="text-right">
                  <span className="text-sm text-[#64748B]">% of Total</span>
                  <p className="text-lg font-semibold text-[#EF4444]">10%</p>
                </div>
              </div>
              <div className="flex items-center justify-between p-4 bg-[#F8FAFC] rounded-lg">
                <div>
                  <span className="text-sm text-[#64748B]">Avg Time to Meeting</span>
                  <p className="text-lg font-semibold text-[#1E293B]">12.4 days</p>
                </div>
                <div className="text-right">
                  <span className="text-sm text-[#64748B]">Change</span>
                  <p className="text-lg font-semibold text-[#10B981]">-2.1 days</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}

export default ReportsPage;

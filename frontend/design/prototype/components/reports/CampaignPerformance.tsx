"use client";

import { BarChart } from "./BarChart";

/**
 * Campaign performance data
 */
export interface CampaignPerformanceData {
  id: string;
  name: string;
  status: "active" | "paused" | "completed";
  sent: number;
  delivered: number;
  opened: number;
  replied: number;
  meetings: number;
  replyRate: number;
  meetingRate: number;
}

/**
 * CampaignPerformance props
 */
export interface CampaignPerformanceProps {
  /** Array of campaign data */
  campaigns: CampaignPerformanceData[];
}

/**
 * Status badge component
 */
function StatusBadge({ status }: { status: CampaignPerformanceData["status"] }) {
  const config = {
    active: { bg: "#DCFCE7", text: "#16A34A", label: "Active" },
    paused: { bg: "#FEF3C7", text: "#D97706", label: "Paused" },
    completed: { bg: "#E0E7FF", text: "#4F46E5", label: "Completed" },
  };

  const { bg, text, label } = config[status];

  return (
    <span
      className="px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ backgroundColor: bg, color: text }}
    >
      {label}
    </span>
  );
}

/**
 * CampaignPerformance - Campaign comparison component
 *
 * Features:
 * - Bar chart of meetings per campaign
 * - Table below with full metrics
 * - Status badges
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Background: #FFFFFF (card-bg)
 * - Border: #E2E8F0 (card-border)
 * - Text primary: #1E293B
 * - Text secondary: #64748B
 * - Accent: #3B82F6
 */
export function CampaignPerformance({ campaigns }: CampaignPerformanceProps) {
  // Prepare chart data
  const chartData = campaigns.map((c) => ({
    name: c.name.length > 15 ? c.name.slice(0, 15) + "..." : c.name,
    meetings: c.meetings,
  }));

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
      <div className="px-6 py-4 border-b border-[#E2E8F0]">
        <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
          Campaign Performance
        </h2>
      </div>

      {/* Bar Chart */}
      <div className="p-6 border-b border-[#E2E8F0]">
        <h3 className="text-sm font-medium text-[#1E293B] mb-4">
          Meetings by Campaign
        </h3>
        <BarChart
          data={chartData}
          xKey="name"
          yKey="meetings"
          color="#3B82F6"
          height={200}
        />
      </div>

      {/* Metrics Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-[#F8FAFC]">
              <th className="px-6 py-3 text-left text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Campaign
              </th>
              <th className="px-6 py-3 text-center text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Sent
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Delivered
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Opened
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Replied
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Reply Rate
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Meetings
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Meeting Rate
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E2E8F0]">
            {campaigns.map((campaign) => (
              <tr
                key={campaign.id}
                className="hover:bg-[#F8FAFC] transition-colors"
              >
                <td className="px-6 py-4">
                  <span className="text-sm font-medium text-[#1E293B]">
                    {campaign.name}
                  </span>
                </td>
                <td className="px-6 py-4 text-center">
                  <StatusBadge status={campaign.status} />
                </td>
                <td className="px-6 py-4 text-right text-sm text-[#1E293B]">
                  {campaign.sent.toLocaleString()}
                </td>
                <td className="px-6 py-4 text-right text-sm text-[#1E293B]">
                  {campaign.delivered.toLocaleString()}
                </td>
                <td className="px-6 py-4 text-right text-sm text-[#1E293B]">
                  {campaign.opened.toLocaleString()}
                </td>
                <td className="px-6 py-4 text-right text-sm text-[#1E293B]">
                  {campaign.replied.toLocaleString()}
                </td>
                <td className="px-6 py-4 text-right text-sm text-[#64748B]">
                  {campaign.replyRate}%
                </td>
                <td className="px-6 py-4 text-right text-sm font-semibold text-[#1E293B]">
                  {campaign.meetings}
                </td>
                <td className="px-6 py-4 text-right text-sm text-[#64748B]">
                  {campaign.meetingRate}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default CampaignPerformance;

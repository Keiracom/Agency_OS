/**
 * ReportsContent.tsx - Reports Page Content
 * Phase: Operation Modular Cockpit
 * Per DASHBOARD.md: Client-visible metrics only, NO cost metrics
 */

"use client";

import {
  ArrowUpRight,
  Download,
} from "lucide-react";
import { useCampaigns } from "@/hooks/use-campaigns";
import { useDashboardStats } from "@/hooks/use-dashboard-stats";

interface ReportsContentProps {
  campaignId?: string | null;
}

export function ReportsContent({ campaignId }: ReportsContentProps) {
  const { stats } = useDashboardStats({ campaignId: campaignId ?? undefined });
  const { data: campaignsData } = useCampaigns({ status: "active" });
  const campaigns = campaignsData?.items ?? [];

  // Weekly data (would come from API)
  const weeklyData = [
    { week: "W1", meetings: 2, replies: 15, sent: 180 },
    { week: "W2", meetings: 4, replies: 22, sent: 210 },
    { week: "W3", meetings: 3, replies: 18, sent: 195 },
    { week: "W4", meetings: 5, replies: 28, sent: 240 },
  ];

  // Funnel data (would come from API)
  const funnelData = [
    { stage: "Sourced", count: 1500, pct: 100 },
    { stage: "Enriched", count: 1200, pct: 80 },
    { stage: "Contacted", count: 950, pct: 63 },
    { stage: "Replied", count: 90, pct: 6 },
    { stage: "Meeting Booked", count: 14, pct: 0.9 },
    { stage: "Showed", count: 12, pct: 0.8 },
  ];

  return (
    <div className="p-6 min-h-screen">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Reports</h2>
          <p className="text-sm text-slate-500">Performance analytics and insights</p>
        </div>
        <div className="flex items-center gap-2">
          <select className="px-3 py-2 border border-slate-200 text-slate-700 text-sm rounded-lg bg-white">
            <option>Last 30 days</option>
            <option>Last 7 days</option>
            <option>Last 90 days</option>
            <option>This month</option>
          </select>
          <button className="px-3 py-2 border border-slate-200 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-50 flex items-center gap-2">
            <Download className="w-4 h-4" /> Export
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-4">
          <div className="text-xs text-slate-500 mb-1">Total Meetings</div>
          <div className="text-2xl font-bold text-slate-900">{stats?.meetingsBooked ?? 0}</div>
          <div className="text-xs text-emerald-600 flex items-center gap-1 mt-1">
            <ArrowUpRight className="w-3 h-3" /> +{stats?.meetingsVsLastMonthPct ?? 0}% vs last period
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-4">
          <div className="text-xs text-slate-500 mb-1">Avg Show Rate</div>
          <div className="text-2xl font-bold text-slate-900">{stats?.showRate ?? 0}%</div>
          <div className="text-xs text-emerald-600 flex items-center gap-1 mt-1">
            <ArrowUpRight className="w-3 h-3" /> +5% vs last period
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-4">
          <div className="text-xs text-slate-500 mb-1">Reply Rate</div>
          <div className="text-2xl font-bold text-slate-900">{stats?.replyRate ?? 0}%</div>
          <div className="text-xs text-emerald-600 flex items-center gap-1 mt-1">
            <ArrowUpRight className="w-3 h-3" /> +0.3% vs last period
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-4">
          <div className="text-xs text-slate-500 mb-1">Deals Created</div>
          <div className="text-2xl font-bold text-slate-900">{stats?.dealsCreated ?? 0}</div>
          <div className="text-xs text-emerald-600 flex items-center gap-1 mt-1">
            <ArrowUpRight className="w-3 h-3" /> +50% vs last period
          </div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Weekly Trend */}
        <div className="col-span-8 bg-white rounded-xl border border-slate-200 shadow-lg p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Weekly Performance</h3>
          <div className="h-48 flex items-end gap-4">
            {weeklyData.map((week) => (
              <div key={week.week} className="flex-1 flex flex-col items-center gap-2">
                <div className="w-full flex flex-col gap-1">
                  <div className="w-full bg-blue-500 rounded-t" style={{ height: `${week.meetings * 20}px` }} title={`${week.meetings} meetings`} />
                  <div className="w-full bg-emerald-500" style={{ height: `${week.replies * 2}px` }} title={`${week.replies} replies`} />
                  <div className="w-full bg-slate-200 rounded-b" style={{ height: `${week.sent / 10}px` }} title={`${week.sent} sent`} />
                </div>
                <span className="text-xs text-slate-500">{week.week}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center justify-center gap-6 mt-4 pt-4 border-t border-slate-100">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-blue-500" />
              <span className="text-xs text-slate-600">Meetings</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-emerald-500" />
              <span className="text-xs text-slate-600">Replies</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-slate-200" />
              <span className="text-xs text-slate-600">Sent</span>
            </div>
          </div>
        </div>

        {/* Funnel */}
        <div className="col-span-4 bg-white rounded-xl border border-slate-200 shadow-lg p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Conversion Funnel</h3>
          <div className="space-y-3">
            {funnelData.map((stage) => (
              <div key={stage.stage}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-slate-600">{stage.stage}</span>
                  <span className="font-medium text-slate-900">{stage.count.toLocaleString()}</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full"
                    style={{ width: `${stage.pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Campaign Performance Table */}
        <div className="col-span-12 bg-white rounded-xl border border-slate-200 shadow-lg">
          <div className="px-5 py-4 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-900">Campaign Performance</h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs text-slate-500">
                <th className="text-left p-4 font-medium">Campaign</th>
                <th className="text-right p-4 font-medium">Meetings</th>
                <th className="text-right p-4 font-medium">Open Rate</th>
                <th className="text-right p-4 font-medium">Reply Rate</th>
                <th className="text-right p-4 font-medium">Show Rate</th>
                <th className="text-right p-4 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((campaign) => (
                <tr key={campaign.id} className="border-b border-slate-50">
                  <td className="p-4 font-medium text-slate-900">{campaign.name}</td>
                  <td className="p-4 text-right text-slate-900">{campaign.meetings_booked ?? 0}</td>
                  <td className="p-4 text-right">
                    <span className="text-slate-600">{campaign.open_rate ?? 0}%</span>
                  </td>
                  <td className="p-4 text-right">
                    <span className="text-blue-600 font-medium">{campaign.reply_rate ?? 0}%</span>
                  </td>
                  <td className="p-4 text-right">
                    <span className={`font-medium ${(campaign.show_rate ?? 0) >= 80 ? "text-emerald-600" : "text-orange-600"}`}>
                      {campaign.show_rate ?? 0}%
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      (campaign.show_rate ?? 0) >= 80 ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                    }`}>
                      {(campaign.show_rate ?? 0) >= 80 ? "On Track" : "Needs Review"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default ReportsContent;

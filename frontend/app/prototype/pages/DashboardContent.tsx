/**
 * DashboardContent.tsx - Dashboard Page Content
 * Phase: Operation Modular Cockpit
 * 
 * Uses modular components: StatsGrid, LiveActivityFeed, ChannelIcon, TierBadge
 */

"use client";

import { useState } from "react";
import {
  Play,
  Pause,
  Plus,
  MoreHorizontal,
  Calendar,
} from "lucide-react";
import {
  StatsGrid,
  LiveActivityFeed,
  ChannelIcon,
  TierBadge,
} from "@/components/dashboard";
import { useCampaigns } from "@/hooks/use-campaigns";
import type { Campaign, ChannelType } from "@/lib/api/types";

// Helper to derive active channels from allocation fields
function getActiveChannels(campaign: Campaign): ChannelType[] {
  const channels: ChannelType[] = [];
  if (campaign.allocation_email > 0) channels.push("email");
  if (campaign.allocation_sms > 0) channels.push("sms");
  if (campaign.allocation_linkedin > 0) channels.push("linkedin");
  if (campaign.allocation_voice > 0) channels.push("voice");
  if (campaign.allocation_mail > 0) channels.push("mail");
  return channels.length > 0 ? channels : ["email"]; // Default to email
}

interface DashboardContentProps {
  campaignId?: string | null;
  onConfirmActivate: () => void;
  onNewCampaign: () => void;
}

export function DashboardContent({
  campaignId,
  onConfirmActivate,
  onNewCampaign,
}: DashboardContentProps) {
  const { data: campaignsData } = useCampaigns({ status: "active" });
  const campaigns = campaignsData?.items ?? [];

  // Meetings data (would come from API)
  const meetings = [
    { id: 1, lead: "Sarah Chen", company: "TechCorp", time: "2:00 PM", day: "Today", type: "Discovery", duration: 30 },
    { id: 2, lead: "Mike Johnson", company: "StartupXYZ", time: "10:00 AM", day: "Tomorrow", type: "Demo", duration: 45 },
    { id: 3, lead: "Lisa Park", company: "Acme Inc", time: "3:30 PM", day: "Thu", type: "Follow-up", duration: 30 },
  ];

  // Priority prospects (would come from API)
  const priorityProspects = [
    { id: 1, name: "Sarah Chen", company: "TechCorp", tier: "hot" as const, signals: ["Requested demo", "Opened 3x today", "Clicked pricing"] },
    { id: 2, name: "Lisa Park", company: "Acme Inc", tier: "hot" as const, signals: ["Meeting scheduled", "LinkedIn engaged", "Referral source"] },
    { id: 3, name: "Tom Wilson", company: "DataFlow", tier: "warm" as const, signals: ["Positive reply", "Website visit", "Content download"] },
  ];

  return (
    <div className="p-6 space-y-6 min-h-screen">
      {/* Stats Grid - Uses modular component */}
      <StatsGrid campaignId={campaignId ?? undefined} />

      {/* Main Content Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Column - Campaigns & Activity */}
        <div className="col-span-8 space-y-6">
          {/* Active Campaigns */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-900">Active Campaigns</h2>
                <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded-full">
                  {campaigns.length} of 5 slots
                </span>
              </div>
              <button
                onClick={onNewCampaign}
                className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
              >
                <Plus className="w-3 h-3" /> Add Campaign
              </button>
            </div>
            <div className="divide-y divide-slate-100">
              {campaigns.slice(0, 3).map((campaign) => (
                <div key={campaign.id} className="px-4 py-3 hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="w-48">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${campaign.status === "active" ? "bg-emerald-500" : "bg-slate-300"}`} />
                        <span className="font-medium text-slate-900 text-sm">{campaign.name}</span>
                        {campaign.permission_mode === "autopilot" && (
                          <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 text-[10px] font-medium rounded">AI</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        {getActiveChannels(campaign).map((ch) => (
                          <ChannelIcon key={ch} channel={ch} size="sm" />
                        ))}
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500 w-12">Priority</span>
                        <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full" style={{ width: "40%" }} />
                        </div>
                        <span className="text-xs font-medium text-slate-700 w-10 text-right">40%</span>
                      </div>
                    </div>
                    <button className="p-1 text-slate-400 hover:text-slate-600">
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="px-4 py-3 border-t border-slate-100 flex items-center justify-between">
              <button className="px-3 py-1.5 bg-red-100 text-red-700 text-xs font-medium rounded-lg hover:bg-red-200 flex items-center gap-1.5 border border-red-200">
                <Pause className="w-3 h-3" />
                Emergency Pause All
              </button>
              <button
                onClick={onConfirmActivate}
                className="px-4 py-1.5 bg-emerald-600 text-white text-xs font-medium rounded-lg hover:bg-emerald-700 flex items-center gap-1.5"
              >
                <Play className="w-3 h-3" />
                Confirm & Activate
              </button>
            </div>
          </div>

          {/* Live Activity Feed - Uses modular component */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-900">Live Activity</h2>
                <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs rounded-full">
                  <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                  Live
                </span>
              </div>
              <button className="text-xs text-slate-500 hover:text-slate-700">View All</button>
            </div>
            <div className="p-4">
              <LiveActivityFeed maxVisible={6} />
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="col-span-4 space-y-6">
          {/* On Track Progress */}
          <div className="bg-gradient-to-r from-emerald-500 to-emerald-600 rounded-xl p-4 text-white">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-emerald-100">Monthly Progress</span>
              <span className="px-2 py-0.5 bg-white/20 text-white text-xs rounded-full">On Track</span>
            </div>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold">12</span>
              <span className="text-emerald-100 mb-1">of 15-20 meetings</span>
            </div>
            <div className="mt-3 h-2 bg-emerald-400/30 rounded-full overflow-hidden">
              <div className="h-full bg-white rounded-full" style={{ width: "70%" }} />
            </div>
          </div>

          {/* Upcoming Meetings */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900">Upcoming Meetings</h2>
              <span className="text-xs text-slate-500">{meetings.length} scheduled</span>
            </div>
            <div className="divide-y divide-slate-100">
              {meetings.map((meeting) => (
                <div key={meeting.id} className="px-4 py-3 hover:bg-slate-50">
                  <div className="flex items-start gap-3">
                    <div className="text-center min-w-[50px]">
                      <div className="text-[10px] text-slate-500 uppercase">{meeting.day}</div>
                      <div className="text-sm font-semibold text-slate-900">{meeting.time}</div>
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-slate-900 text-sm">{meeting.lead}</div>
                      <div className="text-xs text-slate-500">{meeting.company}</div>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                        meeting.type === "Discovery" ? "bg-blue-100 text-blue-700" :
                        meeting.type === "Demo" ? "bg-emerald-100 text-emerald-700" :
                        "bg-amber-100 text-amber-700"
                      }`}>
                        {meeting.type}
                      </span>
                      <div className="text-[10px] text-slate-400 mt-1">{meeting.duration}m</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Priority Prospects */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-900">Priority Prospects</h2>
                <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs rounded-full">Needs Attention</span>
              </div>
            </div>
            <div className="divide-y divide-slate-100">
              {priorityProspects.map((lead) => (
                <div key={lead.id} className="px-4 py-3 hover:bg-slate-50">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="font-medium text-slate-900 text-sm">{lead.name}</div>
                      <div className="text-xs text-slate-500">{lead.company}</div>
                    </div>
                    <TierBadge tier={lead.tier} />
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {lead.signals.map((signal, i) => (
                      <span key={i} className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] rounded">
                        {signal}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DashboardContent;

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
          {/* Active Campaigns - Glass styled */}
          <div className="bg-slate-900/40 backdrop-blur-md rounded-xl border border-white/10 shadow-lg shadow-black/20">
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-white drop-shadow-sm">Active Campaigns</h2>
                <span className="px-2 py-0.5 bg-white/10 text-slate-300 text-xs rounded-full border border-white/10">
                  {campaigns.length} of 5 slots
                </span>
              </div>
              <button
                onClick={onNewCampaign}
                className="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1 transition-colors"
              >
                <Plus className="w-3 h-3" /> Add Campaign
              </button>
            </div>
            <div className="divide-y divide-white/5">
              {campaigns.slice(0, 3).map((campaign) => (
                <div key={campaign.id} className="px-4 py-3 hover:bg-white/5 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="w-48">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${campaign.status === "active" ? "bg-emerald-500 shadow-lg shadow-emerald-500/50" : "bg-slate-500"}`} />
                        <span className="font-medium text-white text-sm">{campaign.name}</span>
                        {campaign.permission_mode === "autopilot" && (
                          <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-400 text-[10px] font-medium rounded border border-purple-500/20">AI</span>
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
                        <span className="text-xs text-slate-400 w-12">Priority</span>
                        <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full" style={{ width: "40%" }} />
                        </div>
                        <span className="text-xs font-medium text-slate-300 w-10 text-right">40%</span>
                      </div>
                    </div>
                    <button className="p-1 text-slate-400 hover:text-white transition-colors">
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="px-4 py-3 border-t border-white/10 flex items-center justify-between">
              <button className="px-3 py-1.5 bg-red-500/20 text-red-400 text-xs font-medium rounded-lg hover:bg-red-500/30 flex items-center gap-1.5 border border-red-500/30 transition-colors">
                <Pause className="w-3 h-3" />
                Emergency Pause All
              </button>
              <button
                onClick={onConfirmActivate}
                className="px-4 py-1.5 bg-emerald-600 text-white text-xs font-medium rounded-lg hover:bg-emerald-500 flex items-center gap-1.5 shadow-lg shadow-emerald-600/30 transition-colors"
              >
                <Play className="w-3 h-3" />
                Confirm & Activate
              </button>
            </div>
          </div>

          {/* Live Activity Feed - Glass styled wrapper */}
          <div className="bg-slate-900/40 backdrop-blur-md rounded-xl border border-white/10 shadow-lg shadow-black/20">
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-white drop-shadow-sm">Live Activity</h2>
                <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full border border-emerald-500/30">
                  <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                  Live
                </span>
              </div>
              <button className="text-xs text-slate-400 hover:text-white transition-colors">View All</button>
            </div>
            <div className="p-4">
              <LiveActivityFeed maxVisible={6} />
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="col-span-4 space-y-6">
          {/* On Track Progress - Glass with emerald gradient */}
          <div className="bg-gradient-to-r from-emerald-600/80 to-emerald-500/80 backdrop-blur-md rounded-xl p-4 text-white border border-emerald-400/20 shadow-lg shadow-emerald-900/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-emerald-100">Monthly Progress</span>
              <span className="px-2 py-0.5 bg-white/20 text-white text-xs rounded-full backdrop-blur-sm">On Track</span>
            </div>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold drop-shadow-sm">12</span>
              <span className="text-emerald-100 mb-1">of 15-20 meetings</span>
            </div>
            <div className="mt-3 h-2 bg-emerald-400/30 rounded-full overflow-hidden">
              <div className="h-full bg-white rounded-full shadow-lg shadow-white/30" style={{ width: "70%" }} />
            </div>
          </div>

          {/* Upcoming Meetings - Glass styled */}
          <div className="bg-slate-900/40 backdrop-blur-md rounded-xl border border-white/10 shadow-lg shadow-black/20">
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white drop-shadow-sm">Upcoming Meetings</h2>
              <span className="text-xs text-slate-400">{meetings.length} scheduled</span>
            </div>
            <div className="divide-y divide-white/5">
              {meetings.map((meeting) => (
                <div key={meeting.id} className="px-4 py-3 hover:bg-white/5 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className="text-center min-w-[50px]">
                      <div className="text-[10px] text-slate-400 uppercase">{meeting.day}</div>
                      <div className="text-sm font-semibold text-white">{meeting.time}</div>
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-white text-sm">{meeting.lead}</div>
                      <div className="text-xs text-slate-400">{meeting.company}</div>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium border ${
                        meeting.type === "Discovery" ? "bg-blue-500/20 text-blue-400 border-blue-500/30" :
                        meeting.type === "Demo" ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" :
                        "bg-amber-500/20 text-amber-400 border-amber-500/30"
                      }`}>
                        {meeting.type}
                      </span>
                      <div className="text-[10px] text-slate-500 mt-1">{meeting.duration}m</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Priority Prospects - Glass styled */}
          <div className="bg-slate-900/40 backdrop-blur-md rounded-xl border border-white/10 shadow-lg shadow-black/20">
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-white drop-shadow-sm">Priority Prospects</h2>
                <span className="px-2 py-0.5 bg-orange-500/20 text-orange-400 text-xs rounded-full border border-orange-500/30">Needs Attention</span>
              </div>
            </div>
            <div className="divide-y divide-white/5">
              {priorityProspects.map((lead) => (
                <div key={lead.id} className="px-4 py-3 hover:bg-white/5 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="font-medium text-white text-sm">{lead.name}</div>
                      <div className="text-xs text-slate-400">{lead.company}</div>
                    </div>
                    <TierBadge tier={lead.tier} />
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {lead.signals.map((signal, i) => (
                      <span key={i} className="px-2 py-0.5 bg-white/10 text-slate-300 text-[10px] rounded border border-white/10">
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

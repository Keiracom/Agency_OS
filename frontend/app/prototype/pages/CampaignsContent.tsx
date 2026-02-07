/**
 * CampaignsContent.tsx - Campaigns Page Content
 * Phase: Operation Modular Cockpit
 */

"use client";

import {
  Plus,
  Sparkles,
  Eye,
  MousePointer,
} from "lucide-react";
import { ChannelIcon } from "@/components/dashboard";
import { useCampaigns } from "@/hooks/use-campaigns";

interface CampaignsContentProps {
  campaignId?: string | null;
  onNewCampaign: () => void;
}

export function CampaignsContent({ onNewCampaign }: CampaignsContentProps) {
  const { data: campaignsData, isLoading } = useCampaigns();
  const campaigns = campaignsData?.items ?? [];

  // AI suggestions (would come from CampaignSuggesterEngine)
  const suggestions = [
    {
      name: "C-Suite Tech Leaders",
      description: "CTOs and CIOs at mid-market SaaS companies",
      targets: ["SaaS", "Technology", "CTO", "CIO", "51-200 emp"],
      allocation: 40,
    },
    {
      name: "Series A Founders",
      description: "CEOs and Founders at recently funded startups",
      targets: ["FinTech", "SaaS", "CEO", "Founder", "11-50 emp"],
      allocation: 35,
    },
  ];

  return (
    <div className="p-6 min-h-screen">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Campaigns</h2>
          <p className="text-sm text-slate-500">
            {campaigns.length} active campaigns • {5 - campaigns.length} slots available
          </p>
        </div>
        <button
          onClick={onNewCampaign}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> New Campaign
        </button>
      </div>

      {/* AI Suggestions */}
      <div className="mb-6 bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl border border-purple-200">
        <div className="px-4 py-3 border-b border-purple-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-600" />
            <h3 className="text-sm font-semibold text-slate-900">AI Campaign Suggestions</h3>
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">Based on your ICP</span>
          </div>
          <button className="text-xs text-purple-600 hover:text-purple-700 font-medium">Regenerate</button>
        </div>
        <div className="p-4 space-y-3">
          {suggestions.map((suggestion, idx) => (
            <div key={idx} className="bg-white rounded-lg border border-slate-200 shadow-md p-3 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-purple-100 text-purple-700 text-xs font-medium flex items-center justify-center">
                      {idx + 1}
                    </span>
                    <span className="font-medium text-slate-900 text-sm">{suggestion.name}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 ml-7">{suggestion.description}</p>
                </div>
                <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs font-medium rounded">
                  {suggestion.allocation}%
                </span>
              </div>
              <div className="flex flex-wrap gap-1 ml-7 mb-2">
                {suggestion.targets.map((t) => (
                  <span key={t} className="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-[10px] rounded">{t}</span>
                ))}
              </div>
              <div className="ml-7 flex items-center gap-2">
                <button
                  onClick={onNewCampaign}
                  className="px-3 py-1 bg-purple-600 text-white text-xs font-medium rounded hover:bg-purple-700 flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" /> Create
                </button>
                <button className="px-3 py-1 text-slate-500 text-xs hover:text-slate-700">Dismiss</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Your Campaigns */}
      <h3 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Your Campaigns</h3>
      <div className="grid gap-4">
        {isLoading ? (
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-5 animate-pulse">
            <div className="h-6 bg-slate-200 rounded w-48 mb-2" />
            <div className="h-4 bg-slate-200 rounded w-32" />
          </div>
        ) : campaigns.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-8 text-center">
            <p className="text-slate-500">No campaigns yet. Create your first campaign to get started!</p>
          </div>
        ) : (
          campaigns.map((campaign) => (
            <div key={campaign.id} className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-5">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${campaign.status === "active" ? "bg-emerald-500" : "bg-slate-300"}`} />
                  <div>
                    <h3 className="font-semibold text-slate-900">{campaign.name}</h3>
                    <p className="text-xs text-slate-500">Created {new Date(campaign.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
                <span className={`px-2.5 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 ${
                  campaign.permission_mode === "autopilot" ? "bg-purple-100 text-purple-700" :
                  campaign.permission_mode === "co_pilot" ? "bg-blue-100 text-blue-700" :
                  "bg-slate-100 text-slate-700"
                }`}>
                  {campaign.permission_mode === "autopilot" && <Sparkles className="w-3 h-3" />}
                  {campaign.permission_mode === "co_pilot" && <Eye className="w-3 h-3" />}
                  {campaign.permission_mode === "manual" && <MousePointer className="w-3 h-3" />}
                  {campaign.permission_mode?.replace("_", " ") ?? "autopilot"}
                </span>
              </div>
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-1">
                  {(campaign.channels ?? ["email"]).map((ch) => (
                    <ChannelIcon key={ch} channel={ch} />
                  ))}
                </div>
                <div className="flex items-center gap-6 text-sm">
                  <div>
                    <span className="text-slate-500">Meetings:</span>
                    <span className="ml-1.5 font-semibold text-slate-900">
                      {campaign.meetings_booked ?? 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">Reply Rate:</span>
                    <span className="ml-1.5 font-semibold text-slate-900">
                      {campaign.reply_rate ?? 0}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Empty Slots */}
      <div className="mt-4 grid gap-4">
        {Array.from({ length: Math.max(0, 5 - campaigns.length) }).slice(0, 2).map((_, slot) => (
          <button
            key={slot}
            onClick={onNewCampaign}
            className="border-2 border-dashed border-slate-200 rounded-xl p-6 text-center hover:border-blue-300 hover:bg-blue-50/50 transition-colors group"
          >
            <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-slate-100 group-hover:bg-blue-100 flex items-center justify-center">
              <Plus className="w-5 h-5 text-slate-400 group-hover:text-blue-500" />
            </div>
            <p className="text-sm text-slate-500 group-hover:text-blue-600">Add new campaign</p>
          </button>
        ))}
      </div>
    </div>
  );
}

export default CampaignsContent;

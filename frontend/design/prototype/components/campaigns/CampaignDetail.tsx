"use client";

import { useState } from "react";
import { ArrowLeft, Sparkles, Play, Pause, Mail, MessageSquare, Linkedin, Phone } from "lucide-react";
import { DashboardShell } from "../layout";
import { CampaignMetricsPanel } from "./CampaignMetricsPanel";
import { CampaignTabs, CampaignTab } from "./CampaignTabs";
import { SequenceBuilder, SequenceStep } from "./SequenceBuilder";

/**
 * Demo campaign data for prototype
 */
const demoCampaign = {
  id: "camp-1",
  name: "Tech Decision Makers",
  description: "Targeting Series A-B tech startups with 50-200 employees",
  status: "active" as const,
  is_ai_suggested: true,
  metrics: {
    meetings: 12,
    showRate: 85,
    replyRate: 3.8,
    activeSequences: 5,
  },
  channelAllocations: {
    email: 60,
    sms: 15,
    linkedin: 20,
    voice: 5,
  },
  targetSettings: {
    industries: ["Technology", "SaaS", "Fintech"],
    titles: ["CEO", "CTO", "Founder", "VP Engineering"],
    companySize: ["10-50", "51-200"],
    locations: ["Australia", "New Zealand"],
  },
};

/**
 * Demo sequences for prototype
 */
const demoSequences: SequenceStep[] = [
  {
    id: "seq-1",
    step_number: 1,
    channel: "email",
    name: "Initial Outreach",
    delay_days: 0,
    subject: "Quick question about {{company_name}}'s growth plans",
    content_preview: "Hi {{first_name}}, I noticed {{company_name}} recently expanded into...",
    is_active: true,
  },
  {
    id: "seq-2",
    step_number: 2,
    channel: "linkedin",
    name: "LinkedIn Connection",
    delay_days: 2,
    content_preview: "Hi {{first_name}}, I came across your profile and was impressed by...",
    is_active: true,
  },
  {
    id: "seq-3",
    step_number: 3,
    channel: "email",
    name: "Follow-up Email",
    delay_days: 3,
    subject: "Re: Quick question about {{company_name}}'s growth plans",
    content_preview: "Just circling back on my previous note. Would love to share how we've helped...",
    is_active: true,
  },
  {
    id: "seq-4",
    step_number: 4,
    channel: "sms",
    name: "SMS Touchpoint",
    delay_days: 2,
    content_preview: "Hi {{first_name}}, sent you a note about helping {{company_name}} with...",
    is_active: true,
  },
  {
    id: "seq-5",
    step_number: 5,
    channel: "voice",
    name: "Voice Call",
    delay_days: 3,
    content_preview: "AI-powered call discussing pain points and value proposition",
    is_active: false,
  },
];

/**
 * Channel icon mapping
 */
const channelIcons = {
  email: Mail,
  sms: MessageSquare,
  linkedin: Linkedin,
  voice: Phone,
};

/**
 * Channel colors
 */
const channelColors = {
  email: { bg: "bg-[#DBEAFE]", text: "text-[#1D4ED8]" },
  sms: { bg: "bg-[#D1FAE5]", text: "text-[#059669]" },
  linkedin: { bg: "bg-[#E0F2FE]", text: "text-[#0369A1]" },
  voice: { bg: "bg-[#EDE9FE]", text: "text-[#7C3AED]" },
};

/**
 * CampaignDetail - Campaign detail page
 *
 * Features:
 * - Back button
 * - Campaign name + status badge
 * - AI suggested badge (if applicable)
 * - Metrics panel
 * - Tab navigation (Overview, Sequences, Leads, Activity)
 * - Channel allocation display
 * - Target settings display
 *
 * Uses DashboardShell for layout.
 */
export function CampaignDetail() {
  const [activeTab, setActiveTab] = useState<CampaignTab>("overview");

  const campaign = demoCampaign;

  return (
    <DashboardShell title="Campaign Details" activePath="/campaigns">
      <div className="space-y-6">
        {/* Back Button */}
        <button className="flex items-center gap-2 text-sm font-medium text-[#64748B] hover:text-[#1E293B] transition-colors">
          <ArrowLeft className="h-4 w-4" />
          Back to Campaigns
        </button>

        {/* Campaign Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              {campaign.is_ai_suggested && (
                <span className="flex items-center gap-1 px-2 py-0.5 bg-[#F3E8FF] text-[#7C3AED] rounded-full text-xs font-medium">
                  <Sparkles className="h-3 w-3" />
                  AI Suggested
                </span>
              )}
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  campaign.status === "active"
                    ? "bg-[#DCFCE7] text-[#166534]"
                    : campaign.status === "paused"
                    ? "bg-[#FEF3C7] text-[#92400E]"
                    : "bg-[#F1F5F9] text-[#64748B]"
                }`}
              >
                {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-[#1E293B]">{campaign.name}</h1>
            <p className="text-[#64748B] mt-1">{campaign.description}</p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-3">
            {campaign.status === "active" ? (
              <button className="flex items-center gap-2 px-4 py-2 bg-[#FEF3C7] hover:bg-[#FDE68A] text-[#92400E] text-sm font-medium rounded-lg transition-colors">
                <Pause className="h-4 w-4" />
                Pause Campaign
              </button>
            ) : (
              <button className="flex items-center gap-2 px-4 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-blue-500/25">
                <Play className="h-4 w-4" />
                Activate Campaign
              </button>
            )}
          </div>
        </div>

        {/* Metrics Panel */}
        <CampaignMetricsPanel
          meetings={campaign.metrics.meetings}
          showRate={campaign.metrics.showRate}
          replyRate={campaign.metrics.replyRate}
          activeSequences={campaign.metrics.activeSequences}
        />

        {/* Tabs */}
        <CampaignTabs activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Tab Content */}
        <div className="mt-6">
          {activeTab === "overview" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Channel Allocation */}
              <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
                <div className="px-6 py-4 border-b border-[#E2E8F0]">
                  <h3 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
                    Channel Allocation
                  </h3>
                </div>
                <div className="p-6 space-y-4">
                  {(Object.entries(campaign.channelAllocations) as [keyof typeof channelIcons, number][]).map(
                    ([channel, allocation]) => {
                      const Icon = channelIcons[channel];
                      const colors = channelColors[channel];

                      return (
                        <div key={channel} className="flex items-center gap-4">
                          <div
                            className={`w-10 h-10 rounded-lg ${colors.bg} flex items-center justify-center`}
                          >
                            <Icon className={`h-5 w-5 ${colors.text}`} />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm font-medium text-[#1E293B] capitalize">
                                {channel}
                              </span>
                              <span className="text-sm font-semibold text-[#1E293B]">
                                {allocation}%
                              </span>
                            </div>
                            <div className="h-2 bg-[#E2E8F0] rounded-full overflow-hidden">
                              <div
                                className={`h-full ${colors.bg.replace("bg-", "bg-")} rounded-full`}
                                style={{
                                  width: `${allocation}%`,
                                  backgroundColor:
                                    channel === "email"
                                      ? "#3B82F6"
                                      : channel === "sms"
                                      ? "#10B981"
                                      : channel === "linkedin"
                                      ? "#0077B5"
                                      : "#8B5CF6",
                                }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    }
                  )}
                </div>
              </div>

              {/* Target Settings */}
              <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
                <div className="px-6 py-4 border-b border-[#E2E8F0]">
                  <h3 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
                    Target Settings
                  </h3>
                </div>
                <div className="p-6 space-y-5">
                  {/* Industries */}
                  <div>
                    <span className="text-sm font-medium text-[#64748B] block mb-2">
                      Industries
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {campaign.targetSettings.industries.map((industry) => (
                        <span
                          key={industry}
                          className="px-3 py-1 bg-[#F1F5F9] text-[#475569] text-sm rounded-full"
                        >
                          {industry}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Titles */}
                  <div>
                    <span className="text-sm font-medium text-[#64748B] block mb-2">
                      Titles
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {campaign.targetSettings.titles.map((title) => (
                        <span
                          key={title}
                          className="px-3 py-1 bg-[#F1F5F9] text-[#475569] text-sm rounded-full"
                        >
                          {title}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Company Size */}
                  <div>
                    <span className="text-sm font-medium text-[#64748B] block mb-2">
                      Company Size
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {campaign.targetSettings.companySize.map((size) => (
                        <span
                          key={size}
                          className="px-3 py-1 bg-[#F1F5F9] text-[#475569] text-sm rounded-full"
                        >
                          {size} employees
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Locations */}
                  <div>
                    <span className="text-sm font-medium text-[#64748B] block mb-2">
                      Locations
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {campaign.targetSettings.locations.map((location) => (
                        <span
                          key={location}
                          className="px-3 py-1 bg-[#F1F5F9] text-[#475569] text-sm rounded-full"
                        >
                          {location}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "sequences" && (
            <SequenceBuilder sequences={demoSequences} isReadOnly />
          )}

          {activeTab === "leads" && (
            <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-8 text-center">
              <h3 className="text-lg font-semibold text-[#1E293B] mb-2">
                Leads in Campaign
              </h3>
              <p className="text-[#64748B] mb-4">
                View and manage leads assigned to this campaign
              </p>
              <button className="px-4 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-medium rounded-lg transition-colors">
                View All Leads
              </button>
            </div>
          )}

          {activeTab === "activity" && (
            <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-8 text-center">
              <h3 className="text-lg font-semibold text-[#1E293B] mb-2">
                Campaign Activity
              </h3>
              <p className="text-[#64748B] mb-4">
                Recent actions and events for this campaign
              </p>
              <div className="text-sm text-[#94A3B8]">
                Activity feed coming soon...
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardShell>
  );
}

export default CampaignDetail;

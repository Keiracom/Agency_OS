"use client";

/**
 * FILE: frontend/app/dashboard/campaigns/page.tsx
 * PURPOSE: Campaign War Room - Overview of all campaigns
 * SPRINT: Dashboard Sprint 3a - Campaign Management
 * SSOT: frontend/design/html-prototypes/campaigns-v4.html
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import {
  Plus,
  Filter,
  Pause,
  Play,
  Copy,
  Edit2,
  Mail,
  Linkedin,
  MessageSquare,
  Phone,
  Send,
  ArrowUpRight,
  TrendingUp,
  TrendingDown,
} from "lucide-react";

// Australian mock data - Melbourne digital marketing agency campaigns
const MOCK_CAMPAIGNS = [
  {
    id: "1",
    name: "Q1 Dental Practices Blitz",
    status: "active" as const,
    channels: ["email", "linkedin", "voice"],
    dateRange: "Jan 15 — Mar 31, 2026",
    stats: {
      leads: 847,
      sent: 2134,
      opens: 892,
      replies: 68,
      meetings: 12,
    },
    sequenceProgress: 72,
    replyRate: 3.2,
    replyDelta: 0.8,
    bookRate: 17.6,
    bookDelta: 2.1,
    pipelineValue: 285000,
    lastActivity: "3 min ago",
  },
  {
    id: "2",
    name: "Tradie Services Melbourne",
    status: "active" as const,
    channels: ["email", "linkedin", "sms", "voice"],
    dateRange: "Feb 1 — Apr 30, 2026",
    stats: {
      leads: 1245,
      sent: 3421,
      opens: 1423,
      replies: 112,
      meetings: 18,
    },
    sequenceProgress: 58,
    replyRate: 3.5,
    replyDelta: 1.2,
    bookRate: 16.1,
    bookDelta: -0.5,
    pipelineValue: 412000,
    lastActivity: "8 min ago",
  },
  {
    id: "3",
    name: "Sydney SaaS Founders",
    status: "completed" as const,
    channels: ["email", "linkedin"],
    dateRange: "Oct 1 — Dec 31, 2025",
    stats: {
      leads: 523,
      sent: 1567,
      opens: 689,
      replies: 78,
      meetings: 14,
    },
    sequenceProgress: 100,
    replyRate: 5.0,
    replyDelta: 1.8,
    bookRate: 17.9,
    bookDelta: 3.2,
    pipelineValue: 520000,
    lastActivity: "Completed",
  },
  {
    id: "4",
    name: "Brisbane Agency Outreach",
    status: "paused" as const,
    channels: ["email", "linkedin", "voice"],
    dateRange: "Feb 10 — May 10, 2026",
    stats: {
      leads: 312,
      sent: 624,
      opens: 187,
      replies: 14,
      meetings: 2,
    },
    sequenceProgress: 25,
    replyRate: 2.2,
    replyDelta: -0.6,
    bookRate: 14.3,
    bookDelta: -1.2,
    pipelineValue: 85000,
    lastActivity: "Paused 2d ago",
  },
];

// Summary stats
const SUMMARY_STATS = {
  totalSent: 7746,
  opened: 3191,
  openRate: 41.2,
  replies: 272,
  replyRate: 3.5,
  meetings: 46,
  meetingsDelta: 12,
  pipelineValue: 1302000,
  pipelineDelta: 28,
};

// Get status badge styles
function getStatusStyles(status: "active" | "paused" | "completed") {
  switch (status) {
    case "active":
      return "bg-amber-glow text-amber border-amber/30";
    case "paused":
      return "bg-amber-500/10 text-amber-400 border-amber-500/30";
    case "completed":
      return "bg-amber/10 text-amber border-amber/30";
  }
}

// Channel icon component
function ChannelIcon({ channel }: { channel: string }) {
  const iconClasses = "w-4 h-4";
  switch (channel) {
    case "email":
      return <Mail className={`${iconClasses} text-text-secondary`} />;
    case "linkedin":
      return <Linkedin className={`${iconClasses} text-amber`} />;
    case "sms":
      return <MessageSquare className={`${iconClasses} text-amber`} />;
    case "voice":
      return <Phone className={`${iconClasses} text-amber`} />;
    case "mail":
      return <Send className={`${iconClasses} text-orange-400`} />;
    default:
      return null;
  }
}

// Format AUD currency
function formatAUD(value: number): string {
  return new Intl.NumberFormat("en-AU", {
    style: "currency",
    currency: "AUD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export default function CampaignsPage() {
  const activeCampaigns = MOCK_CAMPAIGNS.filter((c) => c.status === "active").length;
  const totalLeads = MOCK_CAMPAIGNS.reduce((sum, c) => sum + c.stats.leads, 0);

  return (
    <AppShell pageTitle="Campaigns">
      <div className="space-y-6">
        {/* Header Bar */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-serif text-text-primary">
              Campaign War Room
            </h1>
            <p className="text-sm text-text-secondary mt-1">
              {activeCampaigns} active campaigns · {totalLeads.toLocaleString()} leads in pipeline
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-text-secondary bg-bg-surface border border-border-subtle hover:bg-bg-elevated transition-colors">
              <Filter className="w-4 h-4" />
              Filters
            </button>
            <Link
              href="/dashboard/campaigns/new"
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-text-primary gradient-premium hover:opacity-90 transition-opacity"
            >
              <Plus className="w-4 h-4" />
              New Campaign
            </Link>
          </div>
        </div>

        {/* Summary Stats Strip */}
        <div className="grid grid-cols-5 gap-4">
          <div className="glass-surface rounded-xl p-4 text-center">
            <p className="text-2xl font-bold font-mono text-text-primary">
              {SUMMARY_STATS.totalSent.toLocaleString()}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wider mt-1">
              Total Sent
            </p>
          </div>
          <div className="glass-surface rounded-xl p-4 text-center">
            <p className="text-2xl font-bold font-mono text-text-primary">
              {SUMMARY_STATS.opened.toLocaleString()}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wider mt-1">
              Opened ({SUMMARY_STATS.openRate}%)
            </p>
          </div>
          <div className="glass-surface rounded-xl p-4 text-center">
            <p className="text-2xl font-bold font-mono text-text-primary">
              {SUMMARY_STATS.replies}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wider mt-1">
              Replies ({SUMMARY_STATS.replyRate}%)
            </p>
          </div>
          <div className="glass-surface rounded-xl p-4 text-center">
            <p className="text-2xl font-bold font-mono text-text-primary">
              {SUMMARY_STATS.meetings}
            </p>
            <p className="text-xs text-status-success uppercase tracking-wider mt-1 font-medium">
              Meetings (+{SUMMARY_STATS.meetingsDelta} this week)
            </p>
          </div>
          <div className="glass-surface rounded-xl p-4 text-center">
            <p className="text-2xl font-bold font-mono text-accent-primary">
              {formatAUD(SUMMARY_STATS.pipelineValue)}
            </p>
            <p className="text-xs text-status-success uppercase tracking-wider mt-1 font-medium">
              Pipeline (+{SUMMARY_STATS.pipelineDelta}%)
            </p>
          </div>
        </div>

        {/* Campaign Cards Grid */}
        <div className="grid grid-cols-2 gap-5">
          {MOCK_CAMPAIGNS.map((campaign) => (
            <div
              key={campaign.id}
              className="glass-surface rounded-xl overflow-hidden hover:border-accent-primary/50 transition-colors"
            >
              {/* Card Header */}
              <div className="p-5 border-b border-border-subtle">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h3 className="font-serif font-semibold text-text-primary text-lg">
                      {campaign.name}
                    </h3>
                    <span
                      className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${getStatusStyles(
                        campaign.status
                      )}`}
                    >
                      {campaign.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    {campaign.status === "active" ? (
                      <button className="p-1.5 rounded-lg text-text-muted hover:text-amber-400 hover:bg-amber-500/10 transition-colors">
                        <Pause className="w-4 h-4" />
                      </button>
                    ) : campaign.status === "paused" ? (
                      <button className="p-1.5 rounded-lg text-text-muted hover:text-amber hover:bg-amber-glow transition-colors">
                        <Play className="w-4 h-4" />
                      </button>
                    ) : null}
                    <button className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-elevated transition-colors">
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-elevated transition-colors">
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1.5">
                    {campaign.channels.map((channel) => (
                      <div
                        key={channel}
                        className="w-6 h-6 rounded-md bg-bg-elevated flex items-center justify-center"
                      >
                        <ChannelIcon channel={channel} />
                      </div>
                    ))}
                  </div>
                  <span className="text-xs text-text-muted">{campaign.dateRange}</span>
                </div>
              </div>

              {/* Stats Row */}
              <div className="p-5">
                <div className="grid grid-cols-5 gap-2 mb-4">
                  {[
                    { label: "Leads", value: campaign.stats.leads },
                    { label: "Sent", value: campaign.stats.sent },
                    { label: "Opens", value: campaign.stats.opens },
                    { label: "Replies", value: campaign.stats.replies },
                    { label: "Meetings", value: campaign.stats.meetings, highlight: true },
                  ].map((stat) => (
                    <div
                      key={stat.label}
                      className={`text-center py-2 px-1 rounded-lg ${
                        stat.highlight && stat.value > 0
                          ? "bg-accent-primary/10 border border-accent-primary/30"
                          : "bg-bg-elevated"
                      }`}
                    >
                      <p
                        className={`text-base font-bold font-mono ${
                          stat.highlight && stat.value > 0
                            ? "text-accent-primary"
                            : "text-text-primary"
                        }`}
                      >
                        {stat.value.toLocaleString()}
                      </p>
                      <p className="text-[10px] text-text-muted uppercase">{stat.label}</p>
                    </div>
                  ))}
                </div>

                {/* Progress Bar */}
                <div className="mb-4">
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="text-text-muted">Sequence Progress</span>
                    <span className="font-mono font-medium text-text-primary">
                      {campaign.sequenceProgress}%
                    </span>
                  </div>
                  <div className="h-2 bg-bg-elevated rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${campaign.sequenceProgress}%`,
                        background:
                          campaign.status === "completed"
                            ? "linear-gradient(90deg, #7C3AED, #9061F9)"
                            : "linear-gradient(90deg, #D4956A, #E0A87D)",
                      }}
                    />
                  </div>
                </div>

                {/* Rate Indicators */}
                <div className="flex items-center gap-6 mb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-text-muted">Reply Rate</span>
                    <span className="font-mono font-bold text-sm text-text-primary">
                      {campaign.replyRate}%
                    </span>
                    <span
                      className={`flex items-center text-xs font-medium ${
                        campaign.replyDelta >= 0 ? "text-status-success" : "text-status-error"
                      }`}
                    >
                      {campaign.replyDelta >= 0 ? (
                        <TrendingUp className="w-3 h-3 mr-0.5" />
                      ) : (
                        <TrendingDown className="w-3 h-3 mr-0.5" />
                      )}
                      {campaign.replyDelta >= 0 ? "+" : ""}
                      {campaign.replyDelta}%
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-text-muted">Book Rate</span>
                    <span className="font-mono font-bold text-sm text-text-primary">
                      {campaign.bookRate}%
                    </span>
                    <span
                      className={`flex items-center text-xs font-medium ${
                        campaign.bookDelta >= 0 ? "text-status-success" : "text-status-error"
                      }`}
                    >
                      {campaign.bookDelta >= 0 ? (
                        <TrendingUp className="w-3 h-3 mr-0.5" />
                      ) : (
                        <TrendingDown className="w-3 h-3 mr-0.5" />
                      )}
                      {campaign.bookDelta >= 0 ? "+" : ""}
                      {campaign.bookDelta}%
                    </span>
                  </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between pt-3 border-t border-border-subtle">
                  <Link
                    href={`/dashboard/campaigns/${campaign.id}`}
                    className="flex items-center gap-1 text-sm font-medium text-accent-primary hover:underline"
                  >
                    Explore Campaign
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </Link>
                  <span className="text-xs text-text-muted">
                    Last activity: {campaign.lastActivity}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Performance Comparison Table */}
        <div className="glass-surface rounded-xl overflow-hidden">
          <div className="p-5 border-b border-border-subtle">
            <h3 className="font-serif font-semibold text-text-primary">
              Performance Comparison
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border-subtle bg-bg-elevated/50">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Campaign
                  </th>
                  <th className="text-center px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-right px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Open Rate
                  </th>
                  <th className="text-right px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Reply Rate
                  </th>
                  <th className="text-right px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Book Rate
                  </th>
                  <th className="text-right px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Meetings
                  </th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Pipeline
                  </th>
                </tr>
              </thead>
              <tbody>
                {MOCK_CAMPAIGNS.map((campaign) => {
                  const openRate = ((campaign.stats.opens / campaign.stats.sent) * 100).toFixed(1);
                  const bestOpenRate = Math.max(
                    ...MOCK_CAMPAIGNS.map((c) => (c.stats.opens / c.stats.sent) * 100)
                  );
                  const bestReplyRate = Math.max(...MOCK_CAMPAIGNS.map((c) => c.replyRate));
                  const bestBookRate = Math.max(...MOCK_CAMPAIGNS.map((c) => c.bookRate));
                  const bestMeetings = Math.max(...MOCK_CAMPAIGNS.map((c) => c.stats.meetings));
                  const bestPipeline = Math.max(...MOCK_CAMPAIGNS.map((c) => c.pipelineValue));

                  return (
                    <tr
                      key={campaign.id}
                      className="border-b border-border-subtle last:border-b-0 hover:bg-bg-surface transition-colors"
                    >
                      <td className="px-5 py-4">
                        <Link
                          href={`/dashboard/campaigns/${campaign.id}`}
                          className="font-medium text-text-primary hover:text-accent-primary transition-colors"
                        >
                          {campaign.name}
                        </Link>
                      </td>
                      <td className="px-3 py-4 text-center">
                        <span
                          className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${getStatusStyles(
                            campaign.status
                          )}`}
                        >
                          {campaign.status}
                        </span>
                      </td>
                      <td className="px-3 py-4 text-right">
                        <span
                          className={`font-mono font-medium ${
                            parseFloat(openRate) === bestOpenRate
                              ? "text-status-success"
                              : "text-text-primary"
                          }`}
                        >
                          {openRate}%
                        </span>
                      </td>
                      <td className="px-3 py-4 text-right">
                        <span
                          className={`font-mono font-medium ${
                            campaign.replyRate === bestReplyRate
                              ? "text-status-success"
                              : "text-text-primary"
                          }`}
                        >
                          {campaign.replyRate}%
                        </span>
                      </td>
                      <td className="px-3 py-4 text-right">
                        <span
                          className={`font-mono font-medium ${
                            campaign.bookRate === bestBookRate
                              ? "text-status-success"
                              : "text-text-primary"
                          }`}
                        >
                          {campaign.bookRate}%
                        </span>
                      </td>
                      <td className="px-3 py-4 text-right">
                        <span
                          className={`font-mono font-bold ${
                            campaign.stats.meetings === bestMeetings
                              ? "text-status-success"
                              : "text-text-primary"
                          }`}
                        >
                          {campaign.stats.meetings}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-right">
                        <span
                          className={`font-mono font-bold ${
                            campaign.pipelineValue === bestPipeline
                              ? "text-status-success"
                              : "text-accent-primary"
                          }`}
                        >
                          {formatAUD(campaign.pipelineValue)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

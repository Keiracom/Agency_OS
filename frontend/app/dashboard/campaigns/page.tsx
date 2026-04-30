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
  Clock,
} from "lucide-react";
import { useCampaigns } from "@/hooks/use-campaigns";
import type { Campaign, CampaignStatus } from "@/lib/api/types";

// Get status badge styles
function getStatusStyles(status: CampaignStatus) {
  switch (status) {
    case "active":
      return "bg-amber-glow text-amber border-amber/30";
    case "paused":
      return "bg-amber-500/10 text-amber-400 border-amber-500/30";
    case "completed":
      return "bg-amber/10 text-amber border-amber/30";
    case "pending_approval":
      return "bg-yellow-500/10 text-yellow-400 border-yellow-500/30";
    case "approved":
      return "bg-green-500/10 text-green-400 border-green-500/30";
    case "draft":
    default:
      return "bg-bg-elevated text-text-muted border-border-subtle";
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

function getActiveChannels(campaign: Campaign): string[] {
  const channels: string[] = [];
  if (campaign.allocation_email > 0) channels.push("email");
  if (campaign.allocation_linkedin > 0) channels.push("linkedin");
  if (campaign.allocation_sms > 0) channels.push("sms");
  if (campaign.allocation_voice > 0) channels.push("voice");
  if (campaign.allocation_mail > 0) channels.push("mail");
  return channels.length > 0 ? channels : ["email"]; // default to email
}

function formatDateRange(start: string | null, end: string | null): string {
  if (!start) return "No dates set";
  const startStr = new Date(start).toLocaleDateString("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  if (!end) return `From ${startStr}`;
  const endStr = new Date(end).toLocaleDateString("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  return `${startStr} — ${endStr}`;
}

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function CampaignsPage() {
  const { data, isLoading, isError } = useCampaigns();

  const campaigns = data?.items ?? [];
  const activeCampaigns = campaigns.filter((c) => c.status === "active").length;
  const totalLeads = campaigns.reduce((sum, c) => sum + c.total_leads, 0);
  const totalContacted = campaigns.reduce((sum, c) => sum + c.leads_contacted, 0);
  const totalReplied = campaigns.reduce((sum, c) => sum + c.leads_replied, 0);
  const totalMeetings = campaigns.reduce((sum, c) => sum + c.meetings_booked, 0);
  const avgReplyRate =
    campaigns.length > 0
      ? (campaigns.reduce((sum, c) => sum + c.reply_rate, 0) / campaigns.length).toFixed(1)
      : "0.0";

  if (isLoading) {
    return (
      <AppShell pageTitle="Campaigns">
        <div className="space-y-6">
          <div className="flex items-center justify-center h-64">
            <div className="text-text-muted text-sm animate-pulse">Loading campaigns…</div>
          </div>
        </div>
      </AppShell>
    );
  }

  if (isError) {
    return (
      <AppShell pageTitle="Campaigns">
        <div className="space-y-6">
          <div className="flex items-center justify-center h-64">
            <div className="text-status-error text-sm">Failed to load campaigns. Please try again.</div>
          </div>
        </div>
      </AppShell>
    );
  }

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
            <Link
              href="/dashboard/campaigns/approval"
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-yellow-400 bg-yellow-500/10 border border-yellow-500/30 hover:bg-yellow-500/20 transition-colors"
            >
              <Clock className="w-4 h-4" />
              Pending Approval
              {campaigns.filter((c) => c.status === "pending_approval").length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-yellow-500 text-black">
                  {campaigns.filter((c) => c.status === "pending_approval").length}
                </span>
              )}
            </Link>
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
              {totalLeads.toLocaleString()}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wider mt-1">
              Total Leads
            </p>
          </div>
          <div className="glass-surface rounded-xl p-4 text-center">
            <p className="text-2xl font-bold font-mono text-text-primary">
              {totalContacted.toLocaleString()}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wider mt-1">
              Contacted
            </p>
          </div>
          <div className="glass-surface rounded-xl p-4 text-center">
            <p className="text-2xl font-bold font-mono text-text-primary">
              {totalReplied}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wider mt-1">
              Replies ({avgReplyRate}% avg)
            </p>
          </div>
          <div className="glass-surface rounded-xl p-4 text-center">
            <p className="text-2xl font-bold font-mono text-text-primary">
              {totalMeetings}
            </p>
            <p className="text-xs text-status-success uppercase tracking-wider mt-1 font-medium">
              Meetings Booked
            </p>
          </div>
          <div className="glass-surface rounded-xl p-4 text-center">
            <p className="text-2xl font-bold font-mono text-accent-primary">
              {campaigns.length}
            </p>
            <p className="text-xs text-text-muted uppercase tracking-wider mt-1">
              Total Campaigns
            </p>
          </div>
        </div>

        {/* Campaign Cards Grid */}
        {campaigns.length === 0 ? (
          <div className="glass-surface rounded-xl p-12 text-center">
            <p className="text-text-muted text-sm">No campaigns yet.</p>
            <Link
              href="/dashboard/campaigns/new"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-lg text-sm font-medium text-text-primary gradient-premium hover:opacity-90 transition-opacity"
            >
              <Plus className="w-4 h-4" />
              Create your first campaign
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-5">
            {campaigns.map((campaign) => {
              const channels = getActiveChannels(campaign);
              return (
                <div
                  key={campaign.id}
                  className="glass-surface rounded-xl overflow-hidden hover:border-accent-primary/50 transition-colors"
                >
                  {/* Card Header */}
                  <div className="p-5 border-b border-border-subtle">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3 flex-wrap">
                        <h3 className="font-serif font-semibold text-text-primary text-lg">
                          {campaign.name}
                        </h3>
                        <span
                          className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${getStatusStyles(
                            campaign.status
                          )}`}
                        >
                          {campaign.status.replace("_", " ")}
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
                        {channels.map((channel) => (
                          <div
                            key={channel}
                            className="w-6 h-6 rounded-md bg-bg-elevated flex items-center justify-center"
                          >
                            <ChannelIcon channel={channel} />
                          </div>
                        ))}
                      </div>
                      <span className="text-xs text-text-muted">
                        {formatDateRange(campaign.start_date, campaign.end_date)}
                      </span>
                    </div>
                  </div>

                  {/* Stats Row */}
                  <div className="p-5">
                    <div className="grid grid-cols-4 gap-2 mb-4">
                      {[
                        { label: "Leads", value: campaign.total_leads },
                        { label: "Contacted", value: campaign.leads_contacted },
                        { label: "Replies", value: campaign.leads_replied },
                        { label: "Meetings", value: campaign.meetings_booked, highlight: true },
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

                    {/* Rate Indicators */}
                    <div className="flex items-center gap-3 md:gap-6 mb-4">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-text-muted">Reply Rate</span>
                        <span className="font-mono font-bold text-sm text-text-primary">
                          {campaign.reply_rate.toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-text-muted">Conv. Rate</span>
                        <span className="font-mono font-bold text-sm text-text-primary">
                          {campaign.conversion_rate.toFixed(1)}%
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
                        Updated: {formatRelativeTime(campaign.updated_at)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Performance Comparison Table */}
        {campaigns.length > 0 && (
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
                      Total Leads
                    </th>
                    <th className="text-right px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                      Reply Rate
                    </th>
                    <th className="text-right px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                      Conv. Rate
                    </th>
                    <th className="text-right px-5 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                      Meetings
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {campaigns.map((campaign) => {
                    const bestReplyRate = Math.max(...campaigns.map((c) => c.reply_rate));
                    const bestConvRate = Math.max(...campaigns.map((c) => c.conversion_rate));
                    const bestMeetings = Math.max(...campaigns.map((c) => c.meetings_booked));

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
                            {campaign.status.replace("_", " ")}
                          </span>
                        </td>
                        <td className="px-3 py-4 text-right">
                          <span className="font-mono font-medium text-text-primary">
                            {campaign.total_leads.toLocaleString()}
                          </span>
                        </td>
                        <td className="px-3 py-4 text-right">
                          <span
                            className={`font-mono font-medium ${
                              campaign.reply_rate === bestReplyRate && bestReplyRate > 0
                                ? "text-status-success"
                                : "text-text-primary"
                            }`}
                          >
                            {campaign.reply_rate.toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-3 py-4 text-right">
                          <span
                            className={`font-mono font-medium ${
                              campaign.conversion_rate === bestConvRate && bestConvRate > 0
                                ? "text-status-success"
                                : "text-text-primary"
                            }`}
                          >
                            {campaign.conversion_rate.toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-5 py-4 text-right">
                          <span
                            className={`font-mono font-bold ${
                              campaign.meetings_booked === bestMeetings && bestMeetings > 0
                                ? "text-status-success"
                                : "text-text-primary"
                            }`}
                          >
                            {campaign.meetings_booked}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

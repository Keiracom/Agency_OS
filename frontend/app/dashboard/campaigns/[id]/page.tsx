"use client";

/**
 * FILE: frontend/app/dashboard/campaigns/[id]/page.tsx
 * PURPOSE: Campaign Detail - Deep dive into a single campaign
 * SPRINT: Dashboard Sprint 3a - Campaign Management
 * SSOT: frontend/design/html-prototypes/campaign-detail-v2.html
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 * DIRECTIVE: #182 — wired to real data via useCampaign()
 */

import { use, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import {
  ArrowLeft,
  Calendar,
  Users,
  Edit2,
  Pause,
  Play,
  UserPlus,
  Mail,
  Linkedin,
  MessageSquare,
  Phone,
  Send,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldAlert,
} from "lucide-react";
import { useCampaign, useApproveCampaign, useRejectCampaign } from "@/hooks/use-campaigns";
import type { CampaignStatus } from "@/lib/api/types";

// Status badge styles
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

// Channel icon
function ChannelIcon({ type, className = "w-4 h-4" }: { type: string; className?: string }) {
  switch (type) {
    case "email":
      return <Mail className={`${className} text-text-secondary`} />;
    case "linkedin":
      return <Linkedin className={`${className} text-amber`} />;
    case "sms":
      return <MessageSquare className={`${className} text-amber`} />;
    case "voice":
      return <Phone className={`${className} text-amber`} />;
    case "mail":
      return <Send className={`${className} text-orange-400`} />;
    default:
      return null;
  }
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

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface RejectDialogProps {
  campaignName: string;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
  isLoading: boolean;
}

function RejectDialog({ campaignName, onConfirm, onCancel, isLoading }: RejectDialogProps) {
  const [reason, setReason] = useState("");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="glass-surface rounded-xl p-6 w-full max-w-md mx-4 border border-border-strong">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-status-error/20 flex items-center justify-center">
            <XCircle className="w-5 h-5 text-status-error" />
          </div>
          <div>
            <h3 className="font-serif font-semibold text-text-primary">Reject Campaign</h3>
            <p className="text-sm text-text-muted">{campaignName}</p>
          </div>
        </div>
        <p className="text-sm text-text-secondary mb-4">
          Please provide a reason for rejection.
        </p>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Copy needs revision, target audience too broad…"
          className="w-full h-28 px-3 py-2 rounded-lg bg-bg-elevated border border-border-subtle text-text-primary text-sm placeholder:text-text-muted resize-none focus:outline-none focus:border-accent-primary transition-colors"
        />
        <div className="flex items-center gap-3 mt-4">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-text-secondary bg-bg-surface border border-border-subtle hover:bg-bg-elevated transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(reason)}
            disabled={!reason.trim() || isLoading}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-white bg-status-error hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {isLoading ? "Rejecting…" : "Confirm Reject"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CampaignDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: campaign, isLoading, isError } = useCampaign(id);
  const approveMutation = useApproveCampaign();
  const rejectMutation = useRejectCampaign();
  const [showRejectDialog, setShowRejectDialog] = useState(false);

  if (isLoading) {
    return (
      <AppShell pageTitle="Campaign">
        <div className="flex items-center justify-center h-64">
          <div className="text-text-muted text-sm animate-pulse">Loading campaign…</div>
        </div>
      </AppShell>
    );
  }

  if (isError || !campaign) {
    return (
      <AppShell pageTitle="Campaign">
        <div className="space-y-6">
          <div className="flex items-center gap-3 text-sm">
            <Link href="/dashboard/campaigns" className="flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors">
              <ArrowLeft className="w-4 h-4" />
              Back
            </Link>
          </div>
          <div className="glass-surface rounded-xl p-12 text-center">
            <p className="text-status-error text-sm">Campaign not found or failed to load.</p>
          </div>
        </div>
      </AppShell>
    );
  }

  const isPendingApproval = campaign.status === "pending_approval";

  // Channel breakdown from allocation fields
  const channelData = [
    { key: "email", label: "Email", allocation: campaign.allocation_email },
    { key: "linkedin", label: "LinkedIn", allocation: campaign.allocation_linkedin },
    { key: "sms", label: "SMS", allocation: campaign.allocation_sms },
    { key: "voice", label: "Voice AI", allocation: campaign.allocation_voice },
    { key: "mail", label: "Direct Mail", allocation: campaign.allocation_mail },
  ].filter((c) => c.allocation > 0);

  // Funnel from real metrics
  const funnel = [
    { stage: "Total Leads", count: campaign.total_leads, rate: 100 },
    {
      stage: "Contacted",
      count: campaign.leads_contacted,
      rate: campaign.total_leads > 0
        ? ((campaign.leads_contacted / campaign.total_leads) * 100).toFixed(1)
        : "0.0",
    },
    {
      stage: "Replied",
      count: campaign.leads_replied,
      rate: campaign.reply_rate.toFixed(1),
    },
    {
      stage: "Converted",
      count: campaign.leads_converted,
      rate: campaign.conversion_rate.toFixed(1),
    },
  ];

  const funnelColors = [
    "linear-gradient(135deg, #D4956A, #E0A87D)",
    "linear-gradient(135deg, #3B82F6, #60A5FA)",
    "linear-gradient(135deg, #14B8A6, #2DD4BF)",
    "linear-gradient(135deg, #22C55E, #4ADE80)",
  ];

  return (
    <AppShell pageTitle={campaign.name}>
      <div className="space-y-6">
        {/* Breadcrumb Header */}
        <div className="flex items-center gap-3 text-sm">
          <Link
            href="/dashboard/campaigns"
            className="flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
          <span className="text-border-strong">·</span>
          <span className="text-text-muted">Campaigns</span>
          <span className="text-border-strong">/</span>
          <span className="text-text-primary font-medium">{campaign.name}</span>
        </div>

        {/* Pending Approval Banner */}
        {isPendingApproval && (
          <div className="glass-surface rounded-xl p-4 border border-yellow-500/30 bg-yellow-500/5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <ShieldAlert className="w-5 h-5 text-yellow-400 flex-shrink-0" />
                <div>
                  <p className="font-semibold text-yellow-400">Pending Approval</p>
                  <p className="text-sm text-yellow-400/70">
                    This campaign is awaiting admin review before it can be activated.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setShowRejectDialog(true)}
                  disabled={rejectMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-status-error bg-status-error/10 border border-status-error/30 hover:bg-status-error/20 transition-colors disabled:opacity-50"
                >
                  <XCircle className="w-4 h-4" />
                  Reject
                </button>
                <button
                  onClick={() => approveMutation.mutate(campaign.id)}
                  disabled={approveMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-text-primary gradient-premium hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  {approveMutation.isPending ? "Approving…" : "Approve Campaign"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Campaign Hero Header */}
        <div className="glass-surface rounded-xl overflow-hidden">
          {/* Gradient top border */}
          <div className="h-1 gradient-premium" />

          <div className="p-6">
            {/* Top row */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <div className="flex items-center gap-4 mb-3 flex-wrap">
                  <h1 className="text-2xl font-serif font-semibold text-text-primary">
                    {campaign.name}
                  </h1>
                  <span
                    className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider border flex items-center gap-2 ${getStatusStyles(
                      campaign.status
                    )}`}
                  >
                    {campaign.status !== "pending_approval" && (
                      <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
                    )}
                    {campaign.status.replace("_", " ")}
                  </span>
                </div>
                <div className="flex items-center gap-3 md:gap-6 text-sm text-text-secondary flex-wrap">
                  <span className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-text-muted" />
                    {formatDateRange(campaign.start_date, campaign.end_date)}
                  </span>
                  <span className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-text-muted" />
                    {campaign.total_leads.toLocaleString()} leads enrolled
                  </span>
                  <span className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-text-muted" />
                    Created {formatDate(campaign.created_at)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-text-secondary bg-bg-surface border border-border-subtle hover:bg-bg-elevated transition-colors">
                  <Edit2 className="w-4 h-4" />
                  Edit
                </button>
                {campaign.status === "active" && (
                  <button className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-amber-400 bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/20 transition-colors">
                    <Pause className="w-4 h-4" />
                    Pause
                  </button>
                )}
                {campaign.status === "paused" && (
                  <button className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-amber bg-amber-glow border border-amber/30 hover:opacity-90 transition-opacity">
                    <Play className="w-4 h-4" />
                    Resume
                  </button>
                )}
                <button className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-text-primary gradient-premium hover:opacity-90 transition-opacity">
                  <UserPlus className="w-4 h-4" />
                  Add Leads
                </button>
              </div>
            </div>

            {/* Channel Stats */}
            {channelData.length > 0 ? (
              <div className="flex items-center gap-3 pt-5 border-t border-border-subtle">
                {channelData.map(({ key, label, allocation }) => (
                  <div
                    key={key}
                    className="flex flex-col items-center gap-1 px-6 py-3 rounded-xl"
                    style={{ backgroundColor: "rgba(255,255,255,0.03)" }}
                  >
                    <ChannelIcon type={key} className="w-5 h-5" />
                    <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                      {label}
                    </span>
                    <span className="text-lg font-bold font-mono text-text-primary">
                      {allocation}%
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="pt-5 border-t border-border-subtle">
                <p className="text-sm text-text-muted">No channel allocations configured yet.</p>
              </div>
            )}
          </div>
        </div>

        {/* Key Metrics Strip */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Total Leads", value: campaign.total_leads.toLocaleString(), highlight: false },
            { label: "Leads Contacted", value: campaign.leads_contacted.toLocaleString(), highlight: false },
            { label: "Reply Rate", value: `${campaign.reply_rate.toFixed(1)}%`, highlight: false },
            { label: "Meetings Booked", value: campaign.meetings_booked, highlight: true },
          ].map((stat) => (
            <div
              key={stat.label}
              className={`glass-surface rounded-xl p-4 text-center ${
                stat.highlight ? "border border-accent-primary/30" : ""
              }`}
            >
              <p
                className={`text-2xl font-bold font-mono ${
                  stat.highlight ? "text-accent-primary" : "text-text-primary"
                }`}
              >
                {stat.value}
              </p>
              <p className="text-xs text-text-muted uppercase tracking-wider mt-1">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Campaign Funnel */}
        <div className="glass-surface rounded-xl p-6">
          <h3 className="font-serif font-semibold text-text-primary mb-6 flex items-center gap-2">
            <Activity className="w-5 h-5 text-accent-primary" />
            Campaign Funnel
          </h3>
          {campaign.total_leads > 0 ? (
            <div className="flex items-stretch gap-0">
              {funnel.map((stage, idx) => (
                <div key={stage.stage} className="flex-1 text-center relative">
                  <div
                    className="h-20 flex flex-col items-center justify-center text-text-primary mx-[-1px]"
                    style={{
                      background: funnelColors[idx],
                      clipPath:
                        idx === 0
                          ? "polygon(0 0, calc(100% - 20px) 0, 100% 50%, calc(100% - 20px) 100%, 0 100%)"
                          : idx === funnel.length - 1
                          ? "polygon(0 0, 100% 0, 100% 100%, 0 100%, 20px 50%)"
                          : "polygon(0 0, calc(100% - 20px) 0, 100% 50%, calc(100% - 20px) 100%, 0 100%, 20px 50%)",
                      borderRadius:
                        idx === 0
                          ? "12px 0 0 12px"
                          : idx === funnel.length - 1
                          ? "0 12px 12px 0"
                          : "0",
                    }}
                  >
                    <span className="text-2xl font-bold font-mono">{stage.count.toLocaleString()}</span>
                  </div>
                  <p className="text-sm font-semibold text-text-primary mt-3">{stage.stage}</p>
                  <p className="text-xs text-text-muted">{stage.rate}%</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-text-muted text-sm">
              No funnel data yet — campaign hasn&apos;t started.
            </div>
          )}
        </div>

        {/* Two column: Metrics detail + Campaign info */}
        <div className="grid grid-cols-2 gap-3 md:gap-6">
          {/* Conversion Metrics */}
          <div className="glass-surface rounded-xl overflow-hidden">
            <div className="p-5 border-b border-border-subtle">
              <h3 className="font-serif font-semibold text-text-primary flex items-center gap-2">
                <Activity className="w-5 h-5 text-accent-primary" />
                Conversion Metrics
              </h3>
            </div>
            <div className="p-5 space-y-4">
              {[
                {
                  label: "Reply Rate",
                  value: `${campaign.reply_rate.toFixed(2)}%`,
                  subtext: `${campaign.leads_replied} of ${campaign.leads_contacted} contacted`,
                },
                {
                  label: "Conversion Rate",
                  value: `${campaign.conversion_rate.toFixed(2)}%`,
                  subtext: `${campaign.leads_converted} converted`,
                },
                {
                  label: "Show Rate",
                  value: `${campaign.show_rate.toFixed(2)}%`,
                  subtext: "Meetings attended vs. booked",
                },
                {
                  label: "Active Sequences",
                  value: campaign.active_sequences.toLocaleString(),
                  subtext: "Leads in active sequence steps",
                },
              ].map((metric) => (
                <div key={metric.label} className="flex items-center justify-between py-2 border-b border-border-subtle last:border-b-0">
                  <div>
                    <p className="text-sm font-medium text-text-primary">{metric.label}</p>
                    <p className="text-xs text-text-muted">{metric.subtext}</p>
                  </div>
                  <span className="font-mono font-bold text-lg text-text-primary">{metric.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Campaign Info */}
          <div className="glass-surface rounded-xl overflow-hidden">
            <div className="p-5 border-b border-border-subtle">
              <h3 className="font-serif font-semibold text-text-primary flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-accent-primary" />
                Campaign Info
              </h3>
            </div>
            <div className="p-5 space-y-4">
              {campaign.description && (
                <div>
                  <p className="text-xs text-text-muted uppercase tracking-wider mb-1">Description</p>
                  <p className="text-sm text-text-secondary">{campaign.description}</p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-text-muted uppercase tracking-wider mb-1">Status</p>
                  <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${getStatusStyles(campaign.status)}`}>
                    {campaign.status.replace("_", " ")}
                  </span>
                </div>
                <div>
                  <p className="text-xs text-text-muted uppercase tracking-wider mb-1">Daily Limit</p>
                  <p className="font-mono font-semibold text-text-primary">{campaign.daily_limit}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted uppercase tracking-wider mb-1">Lead Allocation</p>
                  <p className="font-mono font-semibold text-text-primary">{campaign.lead_allocation_pct}%</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted uppercase tracking-wider mb-1">AI Suggested</p>
                  <p className="text-sm text-text-primary">{campaign.is_ai_suggested ? "Yes" : "No"}</p>
                </div>
              </div>
              <div>
                <p className="text-xs text-text-muted uppercase tracking-wider mb-1">Date Range</p>
                <p className="text-sm text-text-primary">{formatDateRange(campaign.start_date, campaign.end_date)}</p>
              </div>
              <div className="pt-2 border-t border-border-subtle">
                <p className="text-xs text-text-muted">
                  Created: {formatDate(campaign.created_at)}
                </p>
                <p className="text-xs text-text-muted">
                  Last updated: {formatDate(campaign.updated_at)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Unavailable sections notice */}
        <div className="glass-surface rounded-xl p-5 border border-border-subtle/50">
          <p className="text-sm text-text-muted text-center">
            📊 Sequence flow, A/B test results, and per-lead activity feed will appear here as campaign data is collected.
          </p>
        </div>
      </div>

      {/* Reject dialog */}
      {showRejectDialog && (
        <RejectDialog
          campaignName={campaign.name}
          onConfirm={(reason) =>
            rejectMutation.mutate(
              { campaignId: campaign.id, reason },
              { onSuccess: () => setShowRejectDialog(false) }
            )
          }
          onCancel={() => setShowRejectDialog(false)}
          isLoading={rejectMutation.isPending}
        />
      )}
    </AppShell>
  );
}

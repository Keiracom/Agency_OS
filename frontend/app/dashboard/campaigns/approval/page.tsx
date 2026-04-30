"use client";

/**
 * FILE: frontend/app/dashboard/campaigns/approval/page.tsx
 * PURPOSE: Campaign approval queue — review and approve/reject pending campaigns
 * DIRECTIVE: #182
 * THEME: Bloomberg Terminal dark mode
 */

import { useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Clock,
  Users,
  Calendar,
  ShieldAlert,
  Inbox,
} from "lucide-react";
import { useCampaigns, useApproveCampaign, useRejectCampaign } from "@/hooks/use-campaigns";
import type { Campaign } from "@/lib/api/types";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

interface RejectDialogProps {
  campaign: Campaign;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
  isLoading: boolean;
}

function RejectDialog({ campaign, onConfirm, onCancel, isLoading }: RejectDialogProps) {
  const [reason, setReason] = useState("");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="glass-surface rounded-xl p-6 w-full max-w-md mx-4 border border-border-strong">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-status-error/20 flex items-center justify-center">
            <XCircle className="w-5 h-5 text-status-error" />
          </div>
          <div>
            <h3 className="font-serif font-semibold text-ink">Reject Campaign</h3>
            <p className="text-sm text-ink-3">{campaign.name}</p>
          </div>
        </div>
        <p className="text-sm text-ink-2 mb-4">
          Please provide a reason for rejection. This will be sent back to the campaign creator.
        </p>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Copy needs revision, target audience too broad…"
          className="w-full h-28 px-3 py-2 rounded-lg bg-panel border border-rule text-ink text-sm placeholder:text-ink-3 resize-none focus:outline-none focus:border-accent-primary transition-colors"
        />
        <div className="flex items-center gap-3 mt-4">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium text-ink-2 bg-bg-panel border border-rule hover:bg-panel transition-colors disabled:opacity-50"
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

interface CampaignApprovalCardProps {
  campaign: Campaign;
  onApprove: (id: string) => void;
  onReject: (campaign: Campaign) => void;
  isApproving: boolean;
}

function CampaignApprovalCard({
  campaign,
  onApprove,
  onReject,
  isApproving,
}: CampaignApprovalCardProps) {
  return (
    <div className="glass-surface rounded-xl overflow-hidden border border-yellow-500/20 hover:border-yellow-500/40 transition-colors">
      {/* Yellow accent top border */}
      <div className="h-0.5 bg-gradient-to-r from-yellow-500/60 to-yellow-500/20" />

      <div className="p-5">
        {/* Header row */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-1.5">
              <h3 className="font-serif font-semibold text-ink text-lg">
                {campaign.name}
              </h3>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border bg-yellow-500/10 text-yellow-400 border-yellow-500/30">
                Pending Approval
              </span>
            </div>
            {campaign.description && (
              <p className="text-sm text-ink-2">{campaign.description}</p>
            )}
          </div>
        </div>

        {/* Meta info grid */}
        <div className="grid grid-cols-3 gap-4 mb-5">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-ink-3 flex-shrink-0" />
            <div>
              <p className="text-xs text-ink-3">Total Leads</p>
              <p className="font-mono font-semibold text-ink">
                {campaign.total_leads.toLocaleString()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-ink-3 flex-shrink-0" />
            <div>
              <p className="text-xs text-ink-3">Created</p>
              <p className="font-mono text-sm text-ink">
                {formatDate(campaign.created_at)}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-ink-3 flex-shrink-0" />
            <div>
              <p className="text-xs text-ink-3">Submitted</p>
              <p className="font-mono text-sm text-ink">
                {formatDate(campaign.updated_at)}
              </p>
            </div>
          </div>
        </div>

        {/* Channel allocations */}
        {(campaign.allocation_email + campaign.allocation_linkedin + campaign.allocation_sms + campaign.allocation_voice + campaign.allocation_mail) > 0 && (
          <div className="flex items-center gap-3 mb-5 p-3 rounded-lg bg-panel/50">
            <span className="text-xs text-ink-3 uppercase tracking-wider">Channels:</span>
            {campaign.allocation_email > 0 && (
              <span className="text-xs font-medium text-ink-2">Email {campaign.allocation_email}%</span>
            )}
            {campaign.allocation_linkedin > 0 && (
              <span className="text-xs font-medium text-amber">LinkedIn {campaign.allocation_linkedin}%</span>
            )}
            {campaign.allocation_sms > 0 && (
              <span className="text-xs font-medium text-ink-2">SMS {campaign.allocation_sms}%</span>
            )}
            {campaign.allocation_voice > 0 && (
              <span className="text-xs font-medium text-amber">Voice {campaign.allocation_voice}%</span>
            )}
            {campaign.allocation_mail > 0 && (
              <span className="text-xs font-medium text-orange-400">Mail {campaign.allocation_mail}%</span>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-3 pt-4 border-t border-rule">
          <Link
            href={`/dashboard/campaigns/${campaign.id}`}
            className="text-sm font-medium text-accent-primary hover:underline mr-auto"
          >
            View Details →
          </Link>
          <button
            onClick={() => onReject(campaign)}
            disabled={isApproving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-status-error bg-status-error/10 border border-status-error/30 hover:bg-status-error/20 transition-colors disabled:opacity-50"
          >
            <XCircle className="w-4 h-4" />
            Reject
          </button>
          <button
            onClick={() => onApprove(campaign.id)}
            disabled={isApproving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-ink gradient-premium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            <CheckCircle2 className="w-4 h-4" />
            {isApproving ? "Approving…" : "Approve"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CampaignApprovalPage() {
  const { data, isLoading, isError } = useCampaigns({ status: "pending_approval" });
  const approveMutation = useApproveCampaign();
  const rejectMutation = useRejectCampaign();

  const [rejectTarget, setRejectTarget] = useState<Campaign | null>(null);
  const [approvedIds, setApprovedIds] = useState<Set<string>>(new Set());
  const [rejectedIds, setRejectedIds] = useState<Set<string>>(new Set());

  const pendingCampaigns = (data?.items ?? []).filter(
    (c) => !approvedIds.has(c.id) && !rejectedIds.has(c.id)
  );

  function handleApprove(campaignId: string) {
    approveMutation.mutate(campaignId, {
      onSuccess: () => {
        setApprovedIds((prev) => new Set(Array.from(prev).concat(campaignId)));
      },
    });
  }

  function handleRejectConfirm(reason: string) {
    if (!rejectTarget) return;
    const campaignId = rejectTarget.id;
    rejectMutation.mutate(
      { campaignId, reason },
      {
        onSuccess: () => {
          setRejectedIds((prev) => new Set(Array.from(prev).concat(campaignId)));
          setRejectTarget(null);
        },
      }
    );
  }

  return (
    <AppShell pageTitle="Campaign Approval">
      <div className="space-y-6">
        {/* Breadcrumb */}
        <div className="flex items-center gap-3 text-sm">
          <Link
            href="/dashboard/campaigns"
            className="flex items-center gap-2 text-ink-3 hover:text-ink transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Campaigns
          </Link>
          <span className="text-border-strong">·</span>
          <span className="text-ink font-medium">Pending Approval</span>
        </div>

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-serif text-ink">Campaign Approval Queue</h1>
            <p className="text-sm text-ink-2 mt-1">
              Review and approve campaigns before they go live
            </p>
          </div>

          {/* Manual Mode indicator */}
          <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-yellow-500/10 border border-yellow-500/30">
            <ShieldAlert className="w-4 h-4 text-yellow-400 flex-shrink-0" />
            <div>
              <p className="text-xs font-bold text-yellow-400 uppercase tracking-wider">Manual Mode</p>
              <p className="text-xs text-yellow-400/70">All campaigns require approval before activation</p>
            </div>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="glass-surface rounded-xl p-12 text-center">
            <div className="text-ink-3 text-sm animate-pulse">Loading pending campaigns…</div>
          </div>
        ) : isError ? (
          <div className="glass-surface rounded-xl p-12 text-center">
            <div className="text-status-error text-sm">Failed to load campaigns. Please try again.</div>
          </div>
        ) : pendingCampaigns.length === 0 ? (
          <div className="glass-surface rounded-xl p-16 text-center">
            <div className="w-16 h-16 rounded-full bg-panel flex items-center justify-center mx-auto mb-4">
              <Inbox className="w-8 h-8 text-ink-3" />
            </div>
            <h3 className="font-serif font-semibold text-ink mb-2">All clear!</h3>
            <p className="text-sm text-ink-3">No campaigns are pending approval right now.</p>
            <Link
              href="/dashboard/campaigns"
              className="inline-flex items-center gap-2 mt-6 px-4 py-2 rounded-lg text-sm font-medium text-ink-2 bg-bg-panel border border-rule hover:bg-panel transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Campaigns
            </Link>
          </div>
        ) : (
          <>
            <p className="text-sm text-ink-3">
              {pendingCampaigns.length} campaign{pendingCampaigns.length !== 1 ? "s" : ""} awaiting review
            </p>
            <div className="space-y-4">
              {pendingCampaigns.map((campaign) => (
                <CampaignApprovalCard
                  key={campaign.id}
                  campaign={campaign}
                  onApprove={handleApprove}
                  onReject={(c) => setRejectTarget(c)}
                  isApproving={
                    approveMutation.isPending && approveMutation.variables === campaign.id
                  }
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Reject dialog overlay */}
      {rejectTarget && (
        <RejectDialog
          campaign={rejectTarget}
          onConfirm={handleRejectConfirm}
          onCancel={() => setRejectTarget(null)}
          isLoading={rejectMutation.isPending}
        />
      )}
    </AppShell>
  );
}

"use client";

/**
 * FILE: frontend/app/dashboard/campaigns/[id]/page.tsx
 * PURPOSE: Campaign Detail - Deep dive into a single campaign
 * SPRINT: Dashboard Sprint 3a - Campaign Management
 * SSOT: frontend/design/html-prototypes/campaign-detail-v2.html
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import { use } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import {
  ArrowLeft,
  Calendar,
  Users,
  CheckCircle2,
  Edit2,
  Pause,
  UserPlus,
  Mail,
  Linkedin,
  MessageSquare,
  Phone,
  Send,
  Check,
  Activity,
  Trophy,
} from "lucide-react";

// Australian mock campaign data
const MOCK_CAMPAIGN = {
  id: "1",
  name: "Q1 Dental Practices Blitz",
  status: "active" as const,
  dateRange: "Jan 15 — Mar 31, 2026",
  leadsEnrolled: 847,
  sequenceProgress: 72,
  channels: {
    email: 2134,
    linkedin: 423,
    sms: 156,
    voice: 67,
    mail: 0,
  },
  funnel: [
    { stage: "Leads", count: 847, rate: 100 },
    { stage: "Contacted", count: 672, rate: 79.3 },
    { stage: "Engaged", count: 96, rate: 11.3 },
    { stage: "Meetings", count: 12, rate: 1.4 },
  ],
  sequence: [
    {
      step: 1,
      type: "email" as const,
      day: 0,
      title: "Personalized intro with dental practice pain points",
      sent: 847,
      opened: 398,
      replied: 24,
      status: "completed" as const,
    },
    {
      step: 2,
      type: "linkedin" as const,
      day: 1,
      title: "Connection request with personalized note",
      sent: 823,
      opened: null,
      replied: 31,
      accepted: 298,
      status: "completed" as const,
    },
    {
      step: 3,
      type: "email" as const,
      day: 3,
      title: "Case study follow-up — Melbourne dental clinic success",
      sent: 792,
      opened: 312,
      replied: 28,
      status: "completed" as const,
    },
    {
      step: 4,
      type: "voice" as const,
      day: 5,
      title: "AI call to engaged leads (opened 2+ times)",
      sent: 67,
      opened: null,
      replied: null,
      connected: 42,
      booked: 8,
      status: "active" as const,
    },
    {
      step: 5,
      type: "sms" as const,
      day: 6,
      title: "Quick check-in for hot leads only",
      sent: 0,
      opened: null,
      replied: null,
      status: "pending" as const,
    },
    {
      step: 6,
      type: "email" as const,
      day: 10,
      title: "Break-up email — final touch",
      sent: 0,
      opened: null,
      replied: null,
      status: "pending" as const,
    },
  ],
  channelPerformance: {
    email: { openRate: 42.3, replyRate: 3.1 },
    linkedin: { acceptRate: 36.2, replyRate: 10.4 },
    voice: { connectRate: 62.7, bookRate: 19.0 },
  },
  abTest: {
    label: "Email Subject Line Test",
    variantA: {
      subject: '"Quick question about {{practice}}\'s growth"',
      openRate: 46.2,
      replyRate: 3.8,
      isWinner: true,
    },
    variantB: {
      subject: '"Saw your Google reviews — impressive!"',
      openRate: 38.1,
      replyRate: 2.4,
      isWinner: false,
    },
  },
  leads: [
    {
      id: "l1",
      initials: "SC",
      name: "Sarah Chen",
      company: "Smile Dental Fitzroy",
      status: "meeting" as const,
      step: 4,
      score: 94,
      tier: "hot" as const,
      lastActivity: "2 min ago",
    },
    {
      id: "l2",
      initials: "MJ",
      name: "Michael Nguyen",
      company: "Melbourne Dental Care",
      status: "replied" as const,
      step: 3,
      score: 87,
      tier: "hot" as const,
      lastActivity: "15 min ago",
    },
    {
      id: "l3",
      initials: "LW",
      name: "Lisa Wong",
      company: "Bright Smiles Clinic",
      status: "opened" as const,
      step: 4,
      score: 72,
      tier: "warm" as const,
      lastActivity: "1 hour ago",
    },
    {
      id: "l4",
      initials: "DP",
      name: "David Park",
      company: "Family Dental Brunswick",
      status: "replied" as const,
      step: 3,
      score: 68,
      tier: "warm" as const,
      lastActivity: "2 hours ago",
    },
    {
      id: "l5",
      initials: "AS",
      name: "Anna Smith",
      company: "Coastal Dental Frankston",
      status: "sent" as const,
      step: 4,
      score: 45,
      tier: "cool" as const,
      lastActivity: "5 hours ago",
    },
  ],
  activityFeed: [
    {
      type: "meeting" as const,
      text: "Sarah Chen booked meeting",
      detail: "Via Voice AI",
      time: "2 min ago",
    },
    {
      type: "reply" as const,
      text: "Michael Nguyen replied to email",
      detail: "Positive intent",
      time: "15 min ago",
    },
    {
      type: "open" as const,
      text: "Lisa Wong opened email (3rd time)",
      detail: "Hot signal",
      time: "1 hour ago",
    },
    {
      type: "call" as const,
      text: "Voice AI completed 5 calls",
      detail: "2 meetings booked",
      time: "2 hours ago",
    },
    {
      type: "reply" as const,
      text: "David Park replied to LinkedIn",
      detail: "Requested info",
      time: "2 hours ago",
    },
  ],
};

// Status badge styles
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

// Lead status badge styles
function getLeadStatusStyles(status: "meeting" | "replied" | "opened" | "sent") {
  switch (status) {
    case "meeting":
      return "bg-amber-glow text-amber";
    case "replied":
      return "bg-bg-elevated/15 text-text-secondary";
    case "opened":
      return "bg-amber/15 text-amber";
    case "sent":
      return "bg-bg-surface0/15 text-text-muted";
  }
}

// Tier colors
function getTierColor(tier: "hot" | "warm" | "cool") {
  switch (tier) {
    case "hot":
      return "text-tier-hot";
    case "warm":
      return "text-tier-warm";
    case "cool":
      return "text-tier-cool";
  }
}

// Avatar gradient
function getAvatarGradient(tier: "hot" | "warm" | "cool") {
  switch (tier) {
    case "hot":
      return "linear-gradient(135deg, #EF4444, #F97316)";
    case "warm":
      return "linear-gradient(135deg, #F59E0B, #FBBF24)";
    case "cool":
      return "linear-gradient(135deg, #3B82F6, #60A5FA)";
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

// Activity icon
function ActivityIcon({ type }: { type: string }) {
  const baseClass = "w-9 h-9 rounded-full flex items-center justify-center";
  switch (type) {
    case "meeting":
      return (
        <div className={`${baseClass} bg-amber-glow`}>
          <Calendar className="w-4 h-4 text-amber" />
        </div>
      );
    case "reply":
      return (
        <div className={`${baseClass} bg-bg-elevated/15`}>
          <Mail className="w-4 h-4 text-text-secondary" />
        </div>
      );
    case "open":
      return (
        <div className={`${baseClass} bg-amber/15`}>
          <Mail className="w-4 h-4 text-amber" />
        </div>
      );
    case "call":
      return (
        <div className={`${baseClass} bg-amber-500/15`}>
          <Phone className="w-4 h-4 text-amber-400" />
        </div>
      );
    default:
      return (
        <div className={`${baseClass} bg-bg-elevated`}>
          <Activity className="w-4 h-4 text-text-muted" />
        </div>
      );
  }
}

// Step type badge
function StepTypeBadge({ type }: { type: string }) {
  const styles: Record<string, string> = {
    email: "bg-bg-elevated/15 text-text-secondary",
    linkedin: "bg-amber-glow text-amber",
    sms: "bg-amber-glow text-amber",
    voice: "bg-amber/15 text-amber",
  };
  return (
    <span
      className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider ${
        styles[type] || "bg-bg-elevated text-text-muted"
      }`}
    >
      {type === "voice" ? "Voice AI" : type}
    </span>
  );
}

export default function CampaignDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const campaign = MOCK_CAMPAIGN;

  // Funnel colors
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

        {/* Campaign Hero Header */}
        <div className="glass-surface rounded-xl overflow-hidden">
          {/* Gradient top border */}
          <div className="h-1 gradient-premium" />

          <div className="p-6">
            {/* Top row */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <div className="flex items-center gap-4 mb-3">
                  <h1 className="text-2xl font-serif font-semibold text-text-primary">
                    {campaign.name}
                  </h1>
                  <span
                    className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider border flex items-center gap-2 ${getStatusStyles(
                      campaign.status
                    )}`}
                  >
                    <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
                    {campaign.status}
                  </span>
                </div>
                <div className="flex items-center gap-6 text-sm text-text-secondary">
                  <span className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-text-muted" />
                    {campaign.dateRange}
                  </span>
                  <span className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-text-muted" />
                    {campaign.leadsEnrolled.toLocaleString()} leads enrolled
                  </span>
                  <span className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-text-muted" />
                    {campaign.sequenceProgress}% through sequence
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-text-secondary bg-bg-surface border border-border-subtle hover:bg-bg-elevated transition-colors">
                  <Edit2 className="w-4 h-4" />
                  Edit
                </button>
                <button className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-amber-400 bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/20 transition-colors">
                  <Pause className="w-4 h-4" />
                  Pause
                </button>
                <button className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-text-primary gradient-premium hover:opacity-90 transition-opacity">
                  <UserPlus className="w-4 h-4" />
                  Add Leads
                </button>
              </div>
            </div>

            {/* Channel Stats */}
            <div className="flex items-center gap-3 pt-5 border-t border-border-subtle">
              {Object.entries(campaign.channels).map(([channel, count]) => (
                <div
                  key={channel}
                  className={`flex flex-col items-center gap-1 px-6 py-3 rounded-xl ${
                    count === 0 ? "opacity-40" : ""
                  }`}
                  style={{ backgroundColor: "rgba(255,255,255,0.03)" }}
                >
                  <ChannelIcon type={channel} className="w-5 h-5" />
                  <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                    {channel === "voice" ? "Voice AI" : channel === "mail" ? "Direct Mail" : channel}
                  </span>
                  <span className="text-lg font-bold font-mono text-text-primary">
                    {count.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Campaign Funnel */}
        <div className="glass-surface rounded-xl p-6">
          <h3 className="font-serif font-semibold text-text-primary mb-6 flex items-center gap-2">
            <Activity className="w-5 h-5 text-accent-primary" />
            Campaign Funnel
          </h3>
          <div className="flex items-stretch gap-0">
            {campaign.funnel.map((stage, idx) => (
              <div key={stage.stage} className="flex-1 text-center relative">
                <div
                  className="h-20 flex flex-col items-center justify-center text-text-primary mx-[-1px]"
                  style={{
                    background: funnelColors[idx],
                    clipPath:
                      idx === 0
                        ? "polygon(0 0, calc(100% - 20px) 0, 100% 50%, calc(100% - 20px) 100%, 0 100%)"
                        : idx === campaign.funnel.length - 1
                        ? "polygon(0 0, 100% 0, 100% 100%, 0 100%, 20px 50%)"
                        : "polygon(0 0, calc(100% - 20px) 0, 100% 50%, calc(100% - 20px) 100%, 0 100%, 20px 50%)",
                    borderRadius: idx === 0 ? "12px 0 0 12px" : idx === campaign.funnel.length - 1 ? "0 12px 12px 0" : "0",
                  }}
                >
                  <span className="text-2xl font-bold font-mono">{stage.count.toLocaleString()}</span>
                </div>
                <p className="text-sm font-semibold text-text-primary mt-3">{stage.stage}</p>
                <p className="text-xs text-text-muted">{stage.rate}%</p>
              </div>
            ))}
          </div>
        </div>

        {/* Two Column: Sequence Flow + Channel Performance */}
        <div className="grid grid-cols-2 gap-6">
          {/* Sequence Flow */}
          <div className="glass-surface rounded-xl overflow-hidden">
            <div className="p-5 border-b border-border-subtle">
              <h3 className="font-serif font-semibold text-text-primary flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-accent-primary" />
                Sequence Flow
              </h3>
            </div>
            <div className="p-5 space-y-3">
              {campaign.sequence.map((step) => (
                <div
                  key={step.step}
                  className={`flex items-start gap-4 p-4 rounded-xl border transition-colors ${
                    step.status === "completed"
                      ? "bg-amber/5 border-amber/30"
                      : step.status === "active"
                      ? "bg-accent-primary/5 border-accent-primary/30"
                      : "bg-bg-surface border-border-subtle"
                  }`}
                >
                  <div
                    className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 ${
                      step.status === "completed"
                        ? "bg-amber text-text-primary"
                        : step.status === "active"
                        ? "bg-accent-primary text-text-primary"
                        : "bg-bg-elevated text-text-muted"
                    }`}
                  >
                    {step.status === "completed" ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      step.step
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <StepTypeBadge type={step.type} />
                      <span className="text-xs text-text-muted">Day {step.day}</span>
                    </div>
                    <p className="text-sm font-medium text-text-primary mb-2">{step.title}</p>
                    <div className="flex items-center gap-4 text-xs text-text-secondary">
                      {step.sent > 0 && <span>📤 {step.sent.toLocaleString()} sent</span>}
                      {step.opened && <span>👀 {step.opened} opened</span>}
                      {step.replied && <span>↩️ {step.replied} replied</span>}
                      {step.accepted && <span>✓ {step.accepted} accepted</span>}
                      {step.connected && <span>📱 {step.connected} connected</span>}
                      {step.booked && (
                        <span className="text-accent-primary font-medium">
                          📅 {step.booked} booked
                        </span>
                      )}
                      {step.status === "pending" && (
                        <span className="text-text-muted">Pending...</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Channel Performance */}
          <div className="glass-surface rounded-xl overflow-hidden">
            <div className="p-5 border-b border-border-subtle">
              <h3 className="font-serif font-semibold text-text-primary flex items-center gap-2">
                <Activity className="w-5 h-5 text-accent-primary" />
                Channel Performance
              </h3>
            </div>
            <div className="p-5 space-y-4">
              {/* Channel Stats Grid */}
              <div className="grid grid-cols-3 gap-3">
                {/* Email */}
                <div className="bg-bg-surface rounded-xl p-4 text-center">
                  <Mail className="w-6 h-6 text-text-secondary mx-auto mb-2" />
                  <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                    Email
                  </p>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Open Rate</span>
                      <span className="font-mono font-semibold text-text-primary">
                        {campaign.channelPerformance.email.openRate}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Reply Rate</span>
                      <span className="font-mono font-semibold text-text-primary">
                        {campaign.channelPerformance.email.replyRate}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* LinkedIn */}
                <div className="bg-bg-surface rounded-xl p-4 text-center">
                  <Linkedin className="w-6 h-6 text-amber mx-auto mb-2" />
                  <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                    LinkedIn
                  </p>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Accept Rate</span>
                      <span className="font-mono font-semibold text-text-primary">
                        {campaign.channelPerformance.linkedin.acceptRate}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Reply Rate</span>
                      <span className="font-mono font-semibold text-text-primary">
                        {campaign.channelPerformance.linkedin.replyRate}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Voice */}
                <div className="bg-bg-surface rounded-xl p-4 text-center">
                  <Phone className="w-6 h-6 text-amber mx-auto mb-2" />
                  <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                    Smart Calls
                  </p>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Connect Rate</span>
                      <span className="font-mono font-semibold text-text-primary">
                        {campaign.channelPerformance.voice.connectRate}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">Book Rate</span>
                      <span className="font-mono font-semibold text-text-primary">
                        {campaign.channelPerformance.voice.bookRate}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* A/B Test Results */}
              <div className="bg-bg-surface rounded-xl p-4">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm font-semibold text-text-primary flex items-center gap-2">
                    <Trophy className="w-4 h-4 text-accent-primary" />
                    {campaign.abTest.label}
                  </span>
                  <span className="px-2 py-1 rounded text-[10px] font-bold uppercase bg-amber-glow text-amber flex items-center gap-1">
                    <Trophy className="w-3 h-3" />
                    Winner
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {[campaign.abTest.variantA, campaign.abTest.variantB].map((variant, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border ${
                        variant.isWinner
                          ? "bg-amber/5 border-amber/30"
                          : "bg-bg-elevated border-border-subtle"
                      }`}
                    >
                      <p className="text-[10px] font-semibold text-text-muted uppercase mb-1">
                        Variant {idx === 0 ? "A" : "B"} {variant.isWinner && "(Winner)"}
                      </p>
                      <p className="text-xs text-text-primary italic mb-3">{variant.subject}</p>
                      <div className="flex items-center gap-4">
                        <div className="text-center">
                          <p className="text-lg font-bold font-mono text-text-primary">
                            {variant.openRate}%
                          </p>
                          <p className="text-[10px] text-text-muted uppercase">Open</p>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-bold font-mono text-text-primary">
                            {variant.replyRate}%
                          </p>
                          <p className="text-[10px] text-text-muted uppercase">Reply</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Two Column: Leads Table + Activity Feed */}
        <div className="grid grid-cols-3 gap-6">
          {/* Leads in Campaign */}
          <div className="col-span-2 glass-surface rounded-xl overflow-hidden">
            <div className="p-5 border-b border-border-subtle flex items-center justify-between">
              <h3 className="font-serif font-semibold text-text-primary flex items-center gap-2">
                <Users className="w-5 h-5 text-accent-primary" />
                Leads in Campaign
              </h3>
              <span className="text-sm text-text-muted">
                {campaign.leadsEnrolled.toLocaleString()} total
              </span>
            </div>
            <table className="w-full">
              <thead>
                <tr className="border-b border-border-subtle bg-bg-elevated/50">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Lead
                  </th>
                  <th className="text-left px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-center px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Step
                  </th>
                  <th className="text-center px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    ALS Score
                  </th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Last Activity
                  </th>
                </tr>
              </thead>
              <tbody>
                {campaign.leads.map((lead) => (
                  <tr
                    key={lead.id}
                    className="border-b border-border-subtle last:border-b-0 hover:bg-bg-surface transition-colors"
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-9 h-9 rounded-lg flex items-center justify-center text-text-primary text-xs font-semibold"
                          style={{ background: getAvatarGradient(lead.tier) }}
                        >
                          {lead.initials}
                        </div>
                        <div>
                          <Link
                            href={`/dashboard/leads/${lead.id}`}
                            className="font-medium text-text-primary hover:text-accent-primary transition-colors"
                          >
                            {lead.name}
                          </Link>
                          <p className="text-xs text-text-muted">{lead.company}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase ${getLeadStatusStyles(
                          lead.status
                        )}`}
                      >
                        {lead.status === "meeting" && <Calendar className="w-3 h-3" />}
                        {lead.status}
                      </span>
                    </td>
                    <td className="px-3 py-4 text-center">
                      <span className="text-sm text-text-secondary">Step {lead.step}</span>
                    </td>
                    <td className="px-3 py-4 text-center">
                      <span className={`font-mono font-bold text-lg ${getTierColor(lead.tier)}`}>
                        {lead.score}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <span className="text-xs text-text-muted">{lead.lastActivity}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Link
              href="/dashboard/leads"
              className="block text-center py-4 text-sm font-medium text-accent-primary hover:bg-bg-surface transition-colors border-t border-border-subtle"
            >
              Explore All Leads →
            </Link>
          </div>

          {/* Activity Feed */}
          <div className="glass-surface rounded-xl overflow-hidden">
            <div className="p-5 border-b border-border-subtle flex items-center justify-between">
              <h3 className="font-serif font-semibold text-text-primary flex items-center gap-2">
                <Activity className="w-5 h-5 text-amber-400" />
                Activity Feed
              </h3>
              <span className="text-xs text-text-muted">Live</span>
            </div>
            <div className="p-5 space-y-4">
              {campaign.activityFeed.map((activity, idx) => (
                <div key={idx} className="flex items-start gap-4">
                  <ActivityIcon type={activity.type} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-text-primary">
                      <strong>{activity.text.split(" ")[0]} {activity.text.split(" ")[1]}</strong>
                      {" "}
                      {activity.text.split(" ").slice(2).join(" ")}
                    </p>
                    <p className="text-xs text-text-muted mt-0.5">
                      {activity.time} · {activity.detail}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

/**
 * CampaignDetail.tsx - Campaign Detail View
 * Phase: Operation Modular Cockpit
 *
 * Full campaign detail page with:
 * - Hero section with campaign info and actions
 * - Funnel visualization (Leads → Contacted → Engaged → Meetings)
 * - Sequence flow diagram with step progress
 * - A/B test results display
 * - Channel performance metrics
 * - Leads table
 * - Activity feed
 *
 * Ported from: agency-os-html/campaign-detail-v2.html
 */

"use client";

import { useState } from "react";
import {
  ArrowLeft,
  Calendar,
  Users,
  CheckCircle,
  Edit2,
  Pause,
  Play,
  Plus,
  Mail,
  Linkedin,
  MessageCircle,
  Phone,
  Package,
  Trophy,
  Zap,
  Shield,
  Check,
  Activity,
  BarChart3,
  ChevronRight,
  Clock,
  Send,
  Eye,
  Reply,
  type LucideIcon,
} from "lucide-react";

// ============================================
// Types
// ============================================

export type CampaignStatus = "active" | "paused" | "completed" | "draft";
export type ChannelType = "email" | "linkedin" | "sms" | "voice" | "mail";
export type StepStatus = "completed" | "active" | "pending";
export type LeadStatus = "meeting" | "replied" | "opened" | "sent";
export type LeadTier = "hot" | "warm" | "cool";

export interface SequenceStep {
  id: string;
  stepNumber: number;
  type: ChannelType;
  title: string;
  day: number;
  status: StepStatus;
  stats: {
    sent?: number;
    opened?: number;
    replied?: number;
    accepted?: number;
    called?: number;
    connected?: number;
    booked?: number;
  };
}

export interface ChannelStats {
  channel: ChannelType;
  stats: { label: string; value: string }[];
}

export interface ABTestVariant {
  id: string;
  label: string;
  subject: string;
  openRate: number;
  replyRate: number;
  isWinner: boolean;
}

export interface ABTest {
  id: string;
  name: string;
  variants: ABTestVariant[];
}

export interface Lead {
  id: string;
  name: string;
  company: string;
  initials: string;
  tier: LeadTier;
  status: LeadStatus;
  step: number;
  score: number;
  lastActivity: string;
}

export interface ActivityItem {
  id: string;
  type: "meeting" | "reply" | "open" | "sent" | "call";
  text: string;
  detail: string;
  time: string;
}

export interface FunnelStep {
  label: string;
  value: number;
  rate: string;
  color: string;
}

export interface Campaign {
  id: string;
  name: string;
  status: CampaignStatus;
  dateRange: { start: string; end: string };
  totalLeads: number;
  progress: number;
  channels: { type: ChannelType; count: number; active: boolean }[];
  funnel: FunnelStep[];
  sequence: SequenceStep[];
  channelPerformance: ChannelStats[];
  abTests: ABTest[];
  leads: Lead[];
  activities: ActivityItem[];
}

interface CampaignDetailProps {
  campaign?: Campaign;
  onBack?: () => void;
  onEdit?: () => void;
  onPause?: () => void;
  onAddLeads?: () => void;
  onViewAllLeads?: () => void;
  isLoading?: boolean;
}

// ============================================
// Mock Data
// ============================================

const mockCampaign: Campaign = {
  id: "1",
  name: "Q1 Agency Blitz",
  status: "active",
  dateRange: { start: "Jan 15", end: "Mar 31, 2026" },
  totalLeads: 1245,
  progress: 68,
  channels: [
    { type: "email", count: 2847, active: true },
    { type: "linkedin", count: 892, active: true },
    { type: "sms", count: 234, active: true },
    { type: "voice", count: 67, active: true },
    { type: "mail", count: 48, active: true },
  ],
  funnel: [
    { label: "Leads", value: 1245, rate: "100%", color: "from-violet-600 to-amber" },
    { label: "Contacted", value: 987, rate: "79.3%", color: "from-amber to-text-secondary" },
    { label: "Engaged", value: 142, rate: "11.4%", color: "from-amber to-amber" },
    { label: "Meetings", value: 12, rate: "0.96%", color: "from-amber to-amber" },
  ],
  sequence: [
    {
      id: "1",
      stepNumber: 1,
      type: "email",
      title: "Personalized intro with pain point hook",
      day: 0,
      status: "completed",
      stats: { sent: 1245, opened: 512, replied: 28 },
    },
    {
      id: "2",
      stepNumber: 2,
      type: "linkedin",
      title: "Connection request with personalized note",
      day: 1,
      status: "completed",
      stats: { sent: 1217, accepted: 423 },
    },
    {
      id: "3",
      stepNumber: 3,
      type: "email",
      title: "Case study follow-up with social proof",
      day: 3,
      status: "completed",
      stats: { sent: 1189, opened: 398, replied: 32 },
    },
    {
      id: "4",
      stepNumber: 4,
      type: "voice",
      title: "AI call to engaged leads (opened 2+ times)",
      day: 5,
      status: "active",
      stats: { called: 67, connected: 42, booked: 8 },
    },
    {
      id: "5",
      stepNumber: 5,
      type: "sms",
      title: "Quick check-in for hot leads only",
      day: 6,
      status: "pending",
      stats: {},
    },
    {
      id: "6",
      stepNumber: 6,
      type: "email",
      title: "Break-up email — final touch",
      day: 10,
      status: "pending",
      stats: {},
    },
  ],
  channelPerformance: [
    { channel: "email", stats: [{ label: "Open Rate", value: "40.1%" }, { label: "Reply Rate", value: "2.4%" }] },
    { channel: "linkedin", stats: [{ label: "Accept Rate", value: "34.7%" }, { label: "Reply Rate", value: "8.2%" }] },
    { channel: "voice", stats: [{ label: "Connect Rate", value: "62.7%" }, { label: "Book Rate", value: "19.0%" }] },
  ],
  abTests: [
    {
      id: "1",
      name: "Email Subject Line Test",
      variants: [
        { id: "a", label: "Variant A (Winner)", subject: "Quick question about {{company}}'s growth", openRate: 44.2, replyRate: 3.1, isWinner: true },
        { id: "b", label: "Variant B", subject: "Saw your recent funding — congrats!", openRate: 36.8, replyRate: 1.9, isWinner: false },
      ],
    },
  ],
  leads: [
    { id: "1", name: "Sarah Chen", company: "Bloom Digital", initials: "SC", tier: "hot", status: "meeting", step: 4, score: 94, lastActivity: "2 min ago" },
    { id: "2", name: "Michael Jones", company: "Growth Labs", initials: "MJ", tier: "hot", status: "replied", step: 3, score: 87, lastActivity: "15 min ago" },
    { id: "3", name: "Lisa Wong", company: "Pixel Perfect", initials: "LW", tier: "warm", status: "opened", step: 4, score: 72, lastActivity: "1 hour ago" },
    { id: "4", name: "David Park", company: "Momentum Media", initials: "DP", tier: "warm", status: "replied", step: 3, score: 68, lastActivity: "2 hours ago" },
    { id: "5", name: "Anna Smith", company: "Digital First", initials: "AS", tier: "cool", status: "sent", step: 4, score: 45, lastActivity: "5 hours ago" },
  ],
  activities: [
    { id: "1", type: "meeting", text: "Sarah Chen booked meeting", detail: "Via Voice AI", time: "2 min ago" },
    { id: "2", type: "reply", text: "Michael Jones replied to email", detail: "Positive intent", time: "15 min ago" },
    { id: "3", type: "open", text: "Lisa Wong opened email (3rd time)", detail: "Hot signal", time: "1 hour ago" },
    { id: "4", type: "call", text: "Voice AI completed 5 calls", detail: "2 meetings booked", time: "2 hours ago" },
    { id: "5", type: "reply", text: "David Park replied to email", detail: "Interested", time: "2 hours ago" },
  ],
};

// ============================================
// Subcomponents
// ============================================

const channelIcons: Record<ChannelType, LucideIcon> = {
  email: Mail,
  linkedin: Linkedin,
  sms: MessageCircle,
  voice: Phone,
  mail: Package,
};

const channelLabels: Record<ChannelType, string> = {
  email: "Email",
  linkedin: "LinkedIn",
  sms: "SMS",
  voice: "Voice AI",
  mail: "Direct Mail",
};

const stepTypeColors: Record<ChannelType, string> = {
  email: "bg-amber/20 text-amber",
  linkedin: "bg-bg-elevated/20 text-text-secondary",
  sms: "bg-amber/20 text-amber",
  voice: "bg-amber-500/20 text-amber-400",
  mail: "bg-amber-light/20 text-amber-light",
};

const tierColors: Record<LeadTier, string> = {
  hot: "from-amber to-amber-light",
  warm: "from-amber-500 to-yellow-500",
  cool: "from-amber to-amber",
};

const scoreColors: Record<LeadTier, string> = {
  hot: "text-amber",
  warm: "text-amber-400",
  cool: "text-text-secondary",
};

const statusConfig: Record<LeadStatus, { label: string; icon: LucideIcon; class: string }> = {
  meeting: { label: "Meeting", icon: Calendar, class: "bg-amber/20 text-amber" },
  replied: { label: "Replied", icon: Reply, class: "bg-bg-elevated/20 text-text-secondary" },
  opened: { label: "Opened", icon: Eye, class: "bg-amber/20 text-amber" },
  sent: { label: "Sent", icon: Send, class: "bg-slate-500/20 text-text-secondary" },
};

const activityIcons: Record<string, { icon: LucideIcon; bg: string }> = {
  meeting: { icon: Calendar, bg: "bg-amber/20" },
  reply: { icon: Reply, bg: "bg-bg-elevated/20" },
  open: { icon: Eye, bg: "bg-amber/20" },
  sent: { icon: Send, bg: "bg-slate-500/20" },
  call: { icon: Phone, bg: "bg-amber-500/20" },
};

// ============================================
// Hero Section
// ============================================

function CampaignHero({
  campaign,
  onEdit,
  onPause,
  onAddLeads,
}: {
  campaign: Campaign;
  onEdit?: () => void;
  onPause?: () => void;
  onAddLeads?: () => void;
}) {
  const isPaused = campaign.status === "paused";

  return (
    <div className="relative bg-bg-void/40 backdrop-blur-md border border-white/10 rounded-2xl p-8 overflow-hidden">
      {/* Top gradient bar */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-violet-600 via-amber to-amber" />

      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-4 mb-3">
            <h1 className="text-3xl font-bold text-text-primary">{campaign.name}</h1>
            <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide ${
              campaign.status === "active"
                ? "bg-amber/20 text-amber border border-amber/30"
                : campaign.status === "paused"
                ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                : "bg-slate-500/20 text-text-secondary border border-slate-500/30"
            }`}>
              {campaign.status === "active" && (
                <span className="w-2 h-2 bg-amber rounded-full animate-pulse" />
              )}
              {campaign.status}
            </span>
          </div>
          <div className="flex items-center gap-8 text-text-secondary text-sm">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              <span>{campaign.dateRange.start} — {campaign.dateRange.end}</span>
            </div>
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4" />
              <span>{campaign.totalLeads.toLocaleString()} leads enrolled</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              <span>{campaign.progress}% through sequence</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onEdit}
            className="flex items-center gap-2 px-4 py-2 bg-bg-base/60 hover:bg-slate-700/60 border border-white/10 rounded-lg text-sm text-text-primary transition-colors"
          >
            <Edit2 className="w-4 h-4" />
            Edit
          </button>
          <button
            onClick={onPause}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
              isPaused
                ? "bg-amber/20 text-amber border border-amber/30 hover:bg-amber/30"
                : "bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30"
            }`}
          >
            {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            {isPaused ? "Resume" : "Pause"}
          </button>
          <button
            onClick={onAddLeads}
            className="flex items-center gap-2 px-4 py-2 bg-amber hover:bg-amber rounded-lg text-sm text-text-primary font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Leads
          </button>
        </div>
      </div>

      {/* Channel stats */}
      <div className="flex gap-3 pt-6 border-t border-white/10">
        {campaign.channels.map((channel) => {
          const Icon = channelIcons[channel.type];
          return (
            <div
              key={channel.type}
              className={`flex flex-col items-center gap-2 px-6 py-4 bg-slate-950/40 rounded-xl min-w-[100px] ${
                !channel.active ? "opacity-40" : ""
              }`}
            >
              <Icon className="w-6 h-6 text-text-secondary" />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                {channelLabels[channel.type]}
              </span>
              <span className="text-lg font-bold font-mono text-text-primary">
                {channel.count.toLocaleString()}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================
// Funnel Visualization
// ============================================

function FunnelVisualization({ funnel }: { funnel: FunnelStep[] }) {
  return (
    <div className="bg-bg-void/40 backdrop-blur-md border border-white/10 rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <Shield className="w-5 h-5 text-amber" />
        <h3 className="text-lg font-semibold text-text-primary">Campaign Funnel</h3>
      </div>
      
      <div className="flex items-stretch gap-0">
        {funnel.map((step, idx) => (
          <div key={step.label} className="flex-1 text-center relative">
            <div
              className={`h-20 flex items-center justify-center bg-gradient-to-br ${step.color} ${
                idx === 0 ? "rounded-l-xl" : ""
              } ${idx === funnel.length - 1 ? "rounded-r-xl" : ""}`}
              style={{
                clipPath: idx === 0
                  ? "polygon(0 0, calc(100% - 20px) 0, 100% 50%, calc(100% - 20px) 100%, 0 100%)"
                  : idx === funnel.length - 1
                  ? "polygon(0 0, 100% 0, 100% 100%, 0 100%, 20px 50%)"
                  : "polygon(0 0, calc(100% - 20px) 0, 100% 50%, calc(100% - 20px) 100%, 0 100%, 20px 50%)",
                marginLeft: idx === 0 ? 0 : "-20px",
              }}
            >
              <span className="text-3xl font-bold font-mono text-text-primary">
                {step.value.toLocaleString()}
              </span>
            </div>
            <p className="mt-3 text-sm font-semibold text-text-primary">{step.label}</p>
            <p className="text-xs text-text-muted">{step.rate}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================
// Sequence Flow
// ============================================

function SequenceFlow({ steps }: { steps: SequenceStep[] }) {
  return (
    <div className="bg-bg-void/40 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
      <div className="flex items-center gap-3 p-5 border-b border-white/10">
        <Activity className="w-5 h-5 text-amber" />
        <h3 className="text-base font-semibold text-text-primary">Sequence Flow</h3>
      </div>
      <div className="p-5 space-y-3">
        {steps.map((step) => {
          const Icon = channelIcons[step.type];
          const isCompleted = step.status === "completed";
          const isActive = step.status === "active";

          return (
            <div
              key={step.id}
              className={`flex items-start gap-4 p-4 rounded-xl transition-colors ${
                isActive
                  ? "bg-amber/10 border border-amber/30"
                  : isCompleted
                  ? "bg-amber/5 border border-amber/20"
                  : "bg-slate-950/40 border border-transparent hover:border-white/10"
              }`}
            >
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${
                  isCompleted
                    ? "bg-amber text-text-primary"
                    : isActive
                    ? "bg-amber text-text-primary"
                    : "bg-slate-700 text-text-secondary"
                }`}
              >
                {isCompleted ? (
                  <Check className="w-5 h-5" />
                ) : (
                  <span className="text-sm font-bold">{step.stepNumber}</span>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${stepTypeColors[step.type]}`}>
                    {channelLabels[step.type]}
                  </span>
                  <span className="text-xs text-text-muted">Day {step.day}</span>
                </div>
                <p className="text-sm font-medium text-text-primary mb-2">{step.title}</p>
                <div className="flex items-center gap-4 text-xs text-text-secondary">
                  {step.stats.sent && <span>📤 {step.stats.sent.toLocaleString()} sent</span>}
                  {step.stats.opened && <span>👀 {step.stats.opened.toLocaleString()} opened</span>}
                  {step.stats.replied && <span>↩️ {step.stats.replied.toLocaleString()} replied</span>}
                  {step.stats.accepted && <span>✅ {step.stats.accepted.toLocaleString()} accepted</span>}
                  {step.stats.called && <span>📞 {step.stats.called.toLocaleString()} called</span>}
                  {step.stats.connected && <span>📱 {step.stats.connected.toLocaleString()} connected</span>}
                  {step.stats.booked && <span>📅 {step.stats.booked.toLocaleString()} booked</span>}
                  {step.status === "pending" && <span className="text-text-muted">Pending...</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================
// Channel Performance
// ============================================

function ChannelPerformance({
  channels,
  abTests,
}: {
  channels: ChannelStats[];
  abTests: ABTest[];
}) {
  return (
    <div className="bg-bg-void/40 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
      <div className="flex items-center gap-3 p-5 border-b border-white/10">
        <BarChart3 className="w-5 h-5 text-amber" />
        <h3 className="text-base font-semibold text-text-primary">Channel Performance</h3>
      </div>
      <div className="p-5">
        {/* Channel grid */}
        <div className="grid grid-cols-3 gap-3 mb-5">
          {channels.map((channel) => {
            const Icon = channelIcons[channel.channel];
            return (
              <div key={channel.channel} className="bg-slate-950/40 rounded-xl p-4 text-center">
                <Icon className="w-7 h-7 mx-auto mb-3 text-text-secondary" />
                <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-2">
                  {channelLabels[channel.channel]}
                </p>
                <div className="space-y-2">
                  {channel.stats.map((stat) => (
                    <div key={stat.label} className="flex justify-between items-center text-xs">
                      <span className="text-text-secondary">{stat.label}</span>
                      <span className="font-mono font-semibold text-text-primary">{stat.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* A/B Tests */}
        <div className="pt-4 border-t border-white/10">
          <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-text-primary">
            <Zap className="w-4 h-4 text-amber" />
            A/B Test Results
          </div>
          {abTests.map((test) => (
            <div key={test.id} className="bg-slate-950/40 rounded-xl p-4">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-semibold text-text-primary">{test.name}</span>
                <span className="flex items-center gap-1.5 px-2 py-1 bg-amber/20 text-amber rounded text-[10px] font-semibold uppercase">
                  <Trophy className="w-3 h-3" />
                  Winner
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {test.variants.map((variant) => (
                  <div
                    key={variant.id}
                    className={`p-4 rounded-lg border ${
                      variant.isWinner
                        ? "bg-amber/5 border-amber/30"
                        : "bg-bg-base/40 border-white/5"
                    }`}
                  >
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-text-muted mb-2">
                      {variant.label}
                    </p>
                    <p className="text-xs text-text-secondary italic mb-3">"{variant.subject}"</p>
                    <div className="flex gap-4">
                      <div className="text-center">
                        <p className="text-xl font-bold font-mono text-text-primary">{variant.openRate}%</p>
                        <p className="text-[9px] uppercase text-text-muted">Open</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xl font-bold font-mono text-text-primary">{variant.replyRate}%</p>
                        <p className="text-[9px] uppercase text-text-muted">Reply</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================
// Leads Table
// ============================================

function LeadsTable({
  leads,
  totalLeads,
  onViewAll,
}: {
  leads: Lead[];
  totalLeads: number;
  onViewAll?: () => void;
}) {
  return (
    <div className="bg-bg-void/40 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between p-5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <Users className="w-5 h-5 text-amber" />
          <h3 className="text-base font-semibold text-text-primary">Leads in Campaign</h3>
        </div>
        <span className="text-sm text-text-muted">{totalLeads.toLocaleString()} total</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-bg-base/40">
              <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Lead</th>
              <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Status</th>
              <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Step</th>
              <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Score</th>
              <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Last Activity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {leads.map((lead) => {
              const status = statusConfig[lead.status];
              const StatusIcon = status.icon;
              return (
                <tr key={lead.id} className="hover:bg-bg-base/20 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${tierColors[lead.tier]} flex items-center justify-center text-text-primary text-xs font-bold`}>
                        {lead.initials}
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-text-primary">{lead.name}</p>
                        <p className="text-xs text-text-muted">{lead.company}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-semibold uppercase ${status.class}`}>
                      <StatusIcon className="w-3 h-3" />
                      {status.label}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-text-secondary">Step {lead.step}</td>
                  <td className="px-4 py-3">
                    <span className={`text-base font-bold font-mono ${scoreColors[lead.tier]}`}>{lead.score}</span>
                  </td>
                  <td className="px-4 py-3 text-xs text-text-muted">{lead.lastActivity}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <button
        onClick={onViewAll}
        className="w-full py-4 text-sm font-medium text-amber hover:text-violet-300 hover:bg-bg-base/20 transition-colors border-t border-white/10"
      >
        Explore All Leads →
      </button>
    </div>
  );
}

// ============================================
// Activity Feed
// ============================================

function ActivityFeed({ activities }: { activities: ActivityItem[] }) {
  return (
    <div className="bg-bg-void/40 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between p-5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <Zap className="w-5 h-5 text-amber-400" />
          <h3 className="text-base font-semibold text-text-primary">Activity Feed</h3>
        </div>
        <span className="text-xs text-text-muted">Live</span>
      </div>
      <div className="p-5 space-y-0">
        {activities.map((item, idx) => {
          const config = activityIcons[item.type];
          const Icon = config.icon;
          return (
            <div key={item.id} className={`flex gap-4 py-4 ${idx < activities.length - 1 ? "border-b border-white/5" : ""}`}>
              <div className={`w-9 h-9 rounded-full ${config.bg} flex items-center justify-center flex-shrink-0`}>
                <Icon className="w-4 h-4 text-text-secondary" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-text-primary">
                  <span className="font-semibold">{item.text.split(" ")[0]} {item.text.split(" ")[1]}</span>
                  {" "}{item.text.split(" ").slice(2).join(" ")}
                </p>
                <p className="text-xs text-text-muted">{item.time} • {item.detail}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================
// Loading Skeleton
// ============================================

function CampaignDetailSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-64 bg-bg-void/40 rounded-2xl" />
      <div className="h-40 bg-bg-void/40 rounded-2xl" />
      <div className="grid grid-cols-2 gap-6">
        <div className="h-96 bg-bg-void/40 rounded-2xl" />
        <div className="h-96 bg-bg-void/40 rounded-2xl" />
      </div>
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function CampaignDetail({
  campaign = mockCampaign,
  onBack,
  onEdit,
  onPause,
  onAddLeads,
  onViewAllLeads,
  isLoading = false,
}: CampaignDetailProps) {
  if (isLoading) {
    return <CampaignDetailSkeleton />;
  }

  return (
    <div className="space-y-6">
      {/* Back navigation */}
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-sm text-text-muted hover:text-text-secondary transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Campaigns</span>
        <span className="mx-2 text-text-muted">/</span>
        <span className="text-text-secondary">{campaign.name}</span>
      </button>

      {/* Hero */}
      <CampaignHero
        campaign={campaign}
        onEdit={onEdit}
        onPause={onPause}
        onAddLeads={onAddLeads}
      />

      {/* Funnel */}
      <FunnelVisualization funnel={campaign.funnel} />

      {/* Sequence + Channel Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SequenceFlow steps={campaign.sequence} />
        <ChannelPerformance
          channels={campaign.channelPerformance}
          abTests={campaign.abTests}
        />
      </div>

      {/* Leads Table + Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
        <LeadsTable
          leads={campaign.leads}
          totalLeads={campaign.totalLeads}
          onViewAll={onViewAllLeads}
        />
        <ActivityFeed activities={campaign.activities} />
      </div>
    </div>
  );
}

export default CampaignDetail;

/**
 * DashboardMain.tsx - Command Center Dashboard
 * Phase: Operation Modular Cockpit
 * 
 * Main dashboard view featuring:
 * - Hero metrics with meetings booked gauge
 * - 5-Channel Orchestration Wheel (Email, LinkedIn, SMS, Voice AI, Direct Mail)
 * - Channel status indicators (active/paused/error)
 * - Voice AI status card
 * - "What's Working" insights panel
 * - Hot prospects list
 * - Recent activity summary
 * - Week ahead calendar
 * 
 * Bloomberg dark mode + glassmorphic styling throughout.
 */

"use client";

import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  EnvelopeIcon,
  PhoneIcon,
  ChatBubbleLeftRightIcon,
  CalendarIcon,
  LightBulbIcon,
  FireIcon,
  CheckCircleIcon,
  ClockIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  PlayIcon,
  DocumentTextIcon,
  PauseIcon,
  ExclamationTriangleIcon,
  BoltIcon,
  EnvelopeOpenIcon,
  CursorArrowRaysIcon,
  SparklesIcon,
} from "@heroicons/react/24/outline";
import { cn } from "@/lib/utils";
import { useUpcomingMeetings, type Meeting as APIMeeting } from "@/hooks/use-meetings";

// ============================================
// Types
// ============================================

type ChannelStatus = "active" | "paused" | "error" | "warming";

interface ChannelConfig {
  key: string;
  label: string;
  icon: typeof EnvelopeIcon;
  color: string;
  bgColor: string;
  borderColor: string;
  status: ChannelStatus;
  count: number;
  metrics?: {
    sent?: number;
    opened?: number;
    replied?: number;
    rate?: string;
  };
}

interface ChannelStats {
  email: number;
  linkedin: number;
  sms: number;
  voice: number;
  directMail: number;
}

interface ChannelStatusData {
  email: { status: ChannelStatus; health: number };
  linkedin: { status: ChannelStatus; health: number };
  sms: { status: ChannelStatus; health: number };
  voice: { status: ChannelStatus; health: number };
  directMail: { status: ChannelStatus; health: number };
}

interface RecentActivity {
  id: string;
  type: "email_sent" | "email_opened" | "linkedin_sent" | "sms_sent" | "call_completed" | "meeting_booked";
  channel: keyof ChannelStats;
  contactName: string;
  company: string;
  description: string;
  timestamp: Date;
  status: "success" | "pending" | "failed";
}

interface Prospect {
  id: string;
  name: string;
  initials: string;
  company: string;
  title: string;
  score: number;
  tier: "hot" | "warm" | "cool";
  badges: Array<{ label: string; type: "hot" | "ceo" | "active" | "founder" }>;
}

interface VoiceCall {
  id: string;
  name: string;
  outcome: "booked" | "followup" | "no-answer";
  summary: string;
  duration: string;
  scheduledDate?: string;
}

interface Meeting {
  id: string;
  title: string;
  time: string;
  contact: string;
  company: string;
  dealValue?: string;
  status: "today" | "upcoming";
}

interface Insight {
  label: string;
  value: string;
}

// ============================================
// Mock Data (replace with real API hooks)
// ============================================

const mockChannelStats: ChannelStats = {
  email: 847,
  linkedin: 423,
  sms: 127,
  voice: 47,
  directMail: 23,
};

const mockChannelStatus: ChannelStatusData = {
  email: { status: "active", health: 98 },
  linkedin: { status: "active", health: 92 },
  sms: { status: "warming", health: 75 },
  voice: { status: "active", health: 100 },
  directMail: { status: "paused", health: 0 },
};

const mockRecentActivity: RecentActivity[] = [
  {
    id: "1",
    type: "meeting_booked",
    channel: "voice",
    contactName: "Sarah Chen",
    company: "Bloom Digital",
    description: "Demo scheduled for Thursday 2:00 PM",
    timestamp: new Date(Date.now() - 1000 * 60 * 2),
    status: "success",
  },
  {
    id: "2",
    type: "email_opened",
    channel: "email",
    contactName: "Michael Jones",
    company: "Growth Labs",
    description: "Opened 'Q1 Proposal' 3 times",
    timestamp: new Date(Date.now() - 1000 * 60 * 8),
    status: "success",
  },
  {
    id: "3",
    type: "linkedin_sent",
    channel: "linkedin",
    contactName: "Lisa Wong",
    company: "Pixel Perfect",
    description: "Connection request accepted",
    timestamp: new Date(Date.now() - 1000 * 60 * 15),
    status: "success",
  },
  {
    id: "4",
    type: "call_completed",
    channel: "voice",
    contactName: "Tom Brown",
    company: "Scale Agency",
    description: "3:45 call - Follow up in Q2",
    timestamp: new Date(Date.now() - 1000 * 60 * 32),
    status: "success",
  },
  {
    id: "5",
    type: "sms_sent",
    channel: "sms",
    contactName: "Emma Wilson",
    company: "Brand Forward",
    description: "Reminder sent for tomorrow's call",
    timestamp: new Date(Date.now() - 1000 * 60 * 45),
    status: "pending",
  },
];

const mockProspects: Prospect[] = [
  {
    id: "1",
    name: "Sarah Chen",
    initials: "SC",
    company: "Bloom Digital",
    title: "Marketing Director",
    score: 94,
    tier: "hot",
    badges: [
      { label: "HOT", type: "hot" },
      { label: "5 opens today", type: "active" },
    ],
  },
  {
    id: "2",
    name: "Michael Jones",
    initials: "MJ",
    company: "Growth Labs",
    title: "CEO",
    score: 87,
    tier: "hot",
    badges: [
      { label: "CEO", type: "ceo" },
      { label: "Pricing page", type: "active" },
    ],
  },
  {
    id: "3",
    name: "Lisa Wong",
    initials: "LW",
    company: "Pixel Perfect",
    title: "Founder",
    score: 82,
    tier: "warm",
    badges: [{ label: "Founder", type: "founder" }],
  },
];

const mockVoiceCalls: VoiceCall[] = [
  {
    id: "1",
    name: "Sarah Chen",
    outcome: "booked",
    summary: '"Interested in learning more"',
    duration: "3:12",
  },
  {
    id: "2",
    name: "Mike Ross",
    outcome: "followup",
    summary: '"Call back in Q2"',
    duration: "1:45",
    scheduledDate: "Feb 10",
  },
];

// Transform API meetings to WeekAhead display format
function transformMeetingsForWeekAhead(apiMeetings: APIMeeting[]): Meeting[] {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const todayEnd = new Date(todayStart.getTime() + 24 * 60 * 60 * 1000);

  return apiMeetings.map((m) => {
    const scheduledDate = m.scheduled_at ? new Date(m.scheduled_at) : null;
    const isToday = scheduledDate && scheduledDate >= todayStart && scheduledDate < todayEnd;
    
    // Format time string
    let timeStr = "TBD";
    if (scheduledDate) {
      const dayName = isToday ? "Today" : scheduledDate.toLocaleDateString("en-US", { weekday: "long" });
      const timeOfDay = scheduledDate.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
      timeStr = `${dayName} ${timeOfDay}`;
    }

    // Map meeting_type to display title
    const typeLabels: Record<string, string> = {
      discovery: "Discovery Call",
      demo: "Demo",
      follow_up: "Follow-up",
      close: "Closing Call",
      onboarding: "Onboarding",
      other: "Meeting",
    };

    return {
      id: m.id,
      title: typeLabels[m.meeting_type] || "Meeting",
      time: timeStr,
      contact: m.lead_name || "Unknown",
      company: m.lead_company || "Unknown",
      status: isToday ? "today" : "upcoming",
    } as Meeting;
  });
}

const mockWhoConverts: Insight[] = [
  { label: "CEO/Founder", value: "2.3x ↑" },
  { label: "Marketing Dir", value: "1.8x ↑" },
];

const mockChannelMix: Insight[] = [
  { label: "Email → LinkedIn", value: "68%" },
  { label: "+Voice", value: "+41%" },
];

// ============================================
// Sub-Components
// ============================================

/**
 * Glassmorphic card wrapper
 */
function GlassCard({
  children,
  className,
  gradient = false,
}: {
  children: React.ReactNode;
  className?: string;
  gradient?: boolean;
}) {
  return (
    <div
      className={cn(
        "relative bg-bg-cream/40 backdrop-blur-md rounded-xl border border-white/10",
        "shadow-lg shadow-black/20 overflow-hidden",
        className
      )}
    >
      {gradient && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-amber to-amber" />
      )}
      {children}
    </div>
  );
}

/**
 * Channel Status Indicator - Shows active/paused/error/warming status
 */
function ChannelStatusIndicator({ 
  status, 
  size = "sm" 
}: { 
  status: ChannelStatus; 
  size?: "sm" | "md" | "lg" 
}) {
  const config = {
    active: { 
      color: "bg-amber", 
      ring: "ring-amber/30",
      label: "Active",
      pulse: true 
    },
    paused: { 
      color: "bg-slate-400", 
      ring: "ring-slate-400/30",
      label: "Paused",
      pulse: false 
    },
    error: { 
      color: "bg-amber", 
      ring: "ring-amber/30",
      label: "Error",
      pulse: true 
    },
    warming: { 
      color: "bg-amber-400", 
      ring: "ring-amber-400/30",
      label: "Warming",
      pulse: true 
    },
  };

  const sizeConfig = {
    sm: "w-2 h-2",
    md: "w-2.5 h-2.5",
    lg: "w-3 h-3",
  };

  const c = config[status];
  return (
    <div className="relative">
      <div 
        className={cn(
          sizeConfig[size],
          "rounded-full",
          c.color,
          c.pulse && "animate-pulse"
        )} 
      />
      {c.pulse && (
        <div 
          className={cn(
            "absolute inset-0 rounded-full ring-2",
            c.ring,
            "animate-ping opacity-75"
          )} 
        />
      )}
    </div>
  );
}

/**
 * 5-Channel Status Panel - Shows all channels with status
 */
function ChannelStatusPanel({
  stats,
  channelStatus,
}: {
  stats: ChannelStats;
  channelStatus: ChannelStatusData;
}) {
  const channels: Array<{
    key: keyof ChannelStats;
    label: string;
    fullLabel: string;
    icon: typeof EnvelopeIcon;
    color: string;
    bgColor: string;
  }> = [
    { 
      key: "email", 
      label: "Email", 
      fullLabel: "Cold Email",
      icon: EnvelopeIcon, 
      color: "text-amber", 
      bgColor: "bg-amber/15" 
    },
    { 
      key: "linkedin", 
      label: "LinkedIn", 
      fullLabel: "LinkedIn",
      icon: ChatBubbleLeftRightIcon, 
      color: "text-ink-2", 
      bgColor: "bg-panel/15" 
    },
    { 
      key: "sms", 
      label: "SMS", 
      fullLabel: "SMS/Text",
      icon: ChatBubbleLeftRightIcon, 
      color: "text-amber", 
      bgColor: "bg-amber-glow" 
    },
    { 
      key: "voice", 
      label: "Voice", 
      fullLabel: "Voice AI",
      icon: PhoneIcon, 
      color: "text-amber-400", 
      bgColor: "bg-amber-500/15" 
    },
    { 
      key: "directMail", 
      label: "Mail", 
      fullLabel: "Direct Mail",
      icon: EnvelopeOpenIcon, 
      color: "text-amber-light", 
      bgColor: "bg-amber-glow" 
    },
  ];

  const getStatusLabel = (status: ChannelStatus) => {
    switch (status) {
      case "active": return "Active";
      case "paused": return "Paused";
      case "error": return "Error";
      case "warming": return "Warming Up";
    }
  };

  return (
    <GlassCard gradient>
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
        <div className="flex items-center gap-2.5 text-sm font-semibold text-ink">
          <SparklesIcon className="w-5 h-5 text-amber" />
          5-Channel Orchestration
        </div>
        <div className="flex items-center gap-2 text-xs text-ink-2">
          <span className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-amber" />
            {Object.values(channelStatus).filter(c => c.status === "active").length} Active
          </span>
        </div>
      </div>
      <div className="p-4 grid grid-cols-5 gap-3">
        {channels.map(({ key, label, fullLabel, icon: Icon, color, bgColor }) => {
          const status = channelStatus[key];
          return (
            <div
              key={key}
              className={cn(
                "relative p-4 rounded-xl border transition-all cursor-pointer group",
                "bg-panel/40 hover:bg-panel/60",
                status.status === "active" 
                  ? "border-white/10 hover:border-amber/30" 
                  : "border-white/5 opacity-75 hover:opacity-100"
              )}
            >
              {/* Status Indicator */}
              <div className="absolute top-3 right-3">
                <ChannelStatusIndicator status={status.status} size="sm" />
              </div>

              {/* Icon */}
              <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center mb-3", bgColor)}>
                <Icon className={cn("w-5 h-5", color)} />
              </div>

              {/* Stats */}
              <div className="text-xl font-bold font-mono text-ink">
                {stats[key].toLocaleString()}
              </div>
              <div className="text-[10px] text-ink-2 uppercase tracking-wider mt-0.5">
                {label}
              </div>

              {/* Health Bar */}
              <div className="mt-3 h-1 bg-slate-700 rounded-full overflow-hidden">
                <div 
                  className={cn(
                    "h-full rounded-full transition-all",
                    status.status === "active" ? "bg-amber" :
                    status.status === "warming" ? "bg-amber-500" :
                    status.status === "error" ? "bg-amber" : "bg-slate-500"
                  )}
                  style={{ width: `${status.health}%` }}
                />
              </div>

              {/* Hover Tooltip */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-bg-cream rounded-lg border border-white/10 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                <div className="text-xs font-medium text-ink">{fullLabel}</div>
                <div className="text-[10px] text-ink-2">{getStatusLabel(status.status)} • {status.health}% health</div>
              </div>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}

/**
 * Recent Activity Summary - Live activity stream
 */
function RecentActivitySummary({ activities }: { activities: RecentActivity[] }) {
  const getActivityIcon = (type: RecentActivity["type"]) => {
    switch (type) {
      case "email_sent": return EnvelopeIcon;
      case "email_opened": return EnvelopeOpenIcon;
      case "linkedin_sent": return ChatBubbleLeftRightIcon;
      case "sms_sent": return ChatBubbleLeftRightIcon;
      case "call_completed": return PhoneIcon;
      case "meeting_booked": return CalendarIcon;
    }
  };

  const getActivityColor = (channel: keyof ChannelStats) => {
    switch (channel) {
      case "email": return { bg: "bg-amber/15", text: "text-amber" };
      case "linkedin": return { bg: "bg-panel/15", text: "text-ink-2" };
      case "sms": return { bg: "bg-amber-glow", text: "text-amber" };
      case "voice": return { bg: "bg-amber-500/15", text: "text-amber-400" };
      case "directMail": return { bg: "bg-amber-glow", text: "text-amber-light" };
    }
  };

  const formatTimeAgo = (date: Date) => {
    const diff = Date.now() - date.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <GlassCard className="h-full">
      <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
        <div className="flex items-center gap-2.5 text-sm font-semibold text-ink">
          <BoltIcon className="w-5 h-5 text-ink-2" />
          Recent Activity
        </div>
        <div className="flex items-center gap-1.5 text-xs font-medium text-amber bg-amber-glow px-2.5 py-1 rounded-full">
          <span className="w-2 h-2 bg-amber rounded-full animate-pulse" />
          Live
        </div>
      </div>
      <div className="px-4 py-3 max-h-[320px] overflow-y-auto custom-scrollbar">
        {activities.map((activity, idx) => {
          const Icon = getActivityIcon(activity.type);
          const color = getActivityColor(activity.channel);
          return (
            <div
              key={activity.id}
              className={cn(
                "flex items-start gap-3 py-3 cursor-pointer transition-colors hover:bg-panel/30 -mx-4 px-4",
                idx !== activities.length - 1 && "border-b border-white/5"
              )}
            >
              <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0", color.bg)}>
                <Icon className={cn("w-4 h-4", color.text)} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-ink truncate">
                    {activity.contactName}
                  </span>
                  <span className="text-xs text-ink-3">•</span>
                  <span className="text-xs text-ink-2 truncate">
                    {activity.company}
                  </span>
                </div>
                <div className="text-sm text-ink-2 mt-0.5 truncate">
                  {activity.description}
                </div>
              </div>
              <div className="text-xs text-ink-3 flex-shrink-0">
                {formatTimeAgo(activity.timestamp)}
              </div>
            </div>
          );
        })}
      </div>
      <div className="px-6 py-3 border-t border-white/10">
        <a 
          href="/activity" 
          className="text-sm text-amber hover:text-amber-light transition-colors"
        >
          View All Activity →
        </a>
      </div>
    </GlassCard>
  );
}

/**
 * Hero Metrics Card - Meetings booked with target gauge
 */
function HeroMeetingsCard({
  booked = 12,
  target = 10,
  changePercent = 25,
}: {
  booked?: number;
  target?: number;
  changePercent?: number;
}) {
  const exceeded = booked >= target;

  return (
    <GlassCard className="p-8" gradient>
      <div className="text-xs font-semibold text-ink-2 uppercase tracking-wider mb-3">
        Meetings Booked
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-6xl font-extrabold text-ink font-mono tracking-tighter">
          {booked}
        </span>
        <span className="text-3xl font-bold text-ink-3 font-mono">
          /{target}
        </span>
      </div>
      <div className="mt-3 text-base text-ink-2">
        {exceeded ? (
          <span className="text-amber font-medium">Target exceeded</span>
        ) : (
          <span className="text-ink-2">
            {target - booked} more to target
          </span>
        )}{" "}
        — 3 days early
      </div>
      <div className="mt-4 pt-4 border-t border-white/10 flex items-center gap-2 text-sm">
        <span className="text-amber font-medium flex items-center gap-1">
          <ArrowTrendingUpIcon className="w-4 h-4" />↑ {changePercent}%
        </span>
        <span className="text-ink-2">vs last month</span>
      </div>
    </GlassCard>
  );
}

/**
 * 5-Channel Orchestration Wheel
 */
function ChannelOrchestrationWheel({
  stats,
  totalTouches = 1800,
}: {
  stats: ChannelStats;
  totalTouches?: number;
}) {
  const total = Object.values(stats).reduce((a, b) => a + b, 0);
  const percentage = Math.round((total / totalTouches) * 100);
  const strokeDasharray = `${(percentage / 100) * 380} 503`;

  const channels = [
    { key: "email", icon: EnvelopeIcon, label: "Email", color: "bg-amber/15 text-amber" },
    { key: "linkedin", icon: ChatBubbleLeftRightIcon, label: "LinkedIn", color: "bg-panel/15 text-ink-2" },
    { key: "sms", icon: ChatBubbleLeftRightIcon, label: "SMS", color: "bg-amber-glow text-amber" },
    { key: "voice", icon: PhoneIcon, label: "Calls", color: "bg-amber-500/15 text-amber-400" },
    { key: "directMail", icon: EnvelopeIcon, label: "Mail", color: "bg-amber-glow text-amber-light" },
  ];

  return (
    <GlassCard className="p-8 flex flex-col items-center" gradient>
      <div className="text-xs font-semibold text-ink-2 uppercase tracking-wider mb-4">
        5-Channel Orchestration
      </div>

      {/* Wheel Container */}
      <div className="relative w-48 h-48">
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 200 200">
          {/* Background ring */}
          <circle
            cx="100"
            cy="100"
            r="80"
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="12"
          />
          {/* Gradient ring */}
          <circle
            cx="100"
            cy="100"
            r="80"
            fill="none"
            stroke="url(#channelGradient)"
            strokeWidth="12"
            strokeDasharray={strokeDasharray}
            strokeLinecap="round"
            transform="rotate(-90 100 100)"
          />
          <defs>
            <linearGradient id="channelGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#7C3AED" />
              <stop offset="100%" stopColor="#3B82F6" />
            </linearGradient>
          </defs>
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-5xl font-extrabold font-mono bg-gradient-to-r from-amber to-text-secondary bg-clip-text text-transparent">
            {(totalTouches / 1000).toFixed(1)}K
          </span>
          <span className="text-xs text-ink-2 uppercase tracking-wider">
            Touches
          </span>
        </div>
      </div>

      {/* Channel Icons */}
      <div className="flex justify-center gap-3 mt-6">
        {channels.map(({ key, icon: Icon, color }) => (
          <div
            key={key}
            className={cn(
              "w-10 h-10 rounded-lg flex items-center justify-center",
              color
            )}
          >
            <Icon className="w-5 h-5" />
          </div>
        ))}
      </div>

      {/* Channel Stats Grid */}
      <div className="grid grid-cols-5 gap-2 mt-6 w-full">
        {channels.map(({ key, label }) => (
          <div
            key={key}
            className="text-center py-3 px-2 bg-panel/50 rounded-lg"
          >
            <div className="text-lg font-bold font-mono text-ink">
              {stats[key as keyof ChannelStats]}
            </div>
            <div className="text-[10px] text-ink-2 uppercase mt-1">
              {label}
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

/**
 * Hot Prospects Card
 */
function HotProspectsCard({ prospects }: { prospects: Prospect[] }) {
  const getBadgeColor = (type: Prospect["badges"][0]["type"]) => {
    switch (type) {
      case "hot":
        return "bg-amber-glow text-amber";
      case "ceo":
      case "founder":
        return "bg-amber/15 text-amber";
      case "active":
        return "bg-amber-glow text-amber";
      default:
        return "bg-bg-panel text-ink-2";
    }
  };

  const getAvatarGradient = (tier: Prospect["tier"]) => {
    switch (tier) {
      case "hot":
        return "bg-gradient-to-br from-amber to-amber-light";
      case "warm":
        return "bg-gradient-to-br from-amber-500 to-yellow-500";
      default:
        return "bg-gradient-to-br from-amber to-amber";
    }
  };

  const getScoreColor = (tier: Prospect["tier"]) => {
    switch (tier) {
      case "hot":
        return "text-amber";
      case "warm":
        return "text-amber-400";
      default:
        return "text-ink-2";
    }
  };

  return (
    <GlassCard className="h-full">
      <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
        <div className="flex items-center gap-2.5 text-sm font-semibold text-ink">
          <FireIcon className="w-5 h-5 text-amber" />
          Hot Right Now
        </div>
        <a
          href="/leads"
          className="text-sm text-amber hover:text-amber-light transition-colors"
        >
          See All →
        </a>
      </div>
      <div className="px-6 py-4">
        {prospects.map((prospect, idx) => (
          <div
            key={prospect.id}
            className={cn(
              "flex items-center gap-4 py-4 cursor-pointer transition-colors hover:bg-panel/30 -mx-6 px-6",
              idx !== prospects.length - 1 && "border-b border-white/5"
            )}
          >
            <div
              className={cn(
                "w-11 h-11 rounded-lg flex items-center justify-center text-sm font-semibold text-ink",
                getAvatarGradient(prospect.tier)
              )}
            >
              {prospect.initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-sm text-ink truncate">
                {prospect.name}
              </div>
              <div className="text-sm text-ink-2 truncate">
                {prospect.company} • {prospect.title}
              </div>
              <div className="flex gap-1.5 mt-1.5">
                {prospect.badges.map((badge, i) => (
                  <span
                    key={i}
                    className={cn(
                      "text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wide",
                      getBadgeColor(badge.type)
                    )}
                  >
                    {badge.label}
                  </span>
                ))}
              </div>
            </div>
            <div className="text-right">
              <div
                className={cn(
                  "text-2xl font-extrabold font-mono",
                  getScoreColor(prospect.tier)
                )}
              >
                {prospect.score}
              </div>
              <div className="text-[10px] text-ink-3 uppercase">Score</div>
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

/**
 * Voice AI / Smart Calling Card
 */
function VoiceAICard({ calls }: { calls: VoiceCall[] }) {
  const stats = [
    { value: 47, label: "Calls" },
    { value: 31, label: "Connect" },
    { value: 8, label: "Booked" },
    { value: "26%", label: "Rate" },
  ];

  const getOutcomeStyle = (outcome: VoiceCall["outcome"]) => {
    switch (outcome) {
      case "booked":
        return {
          bg: "bg-amber-glow",
          text: "text-amber",
          icon: CheckCircleIcon,
        };
      case "followup":
        return {
          bg: "bg-panel/15",
          text: "text-ink-2",
          icon: ClockIcon,
        };
      default:
        return {
          bg: "bg-bg-panel",
          text: "text-ink-2",
          icon: PhoneIcon,
        };
    }
  };

  return (
    <GlassCard className="h-full">
      <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
        <div className="flex items-center gap-2.5 text-sm font-semibold text-ink">
          <PhoneIcon className="w-5 h-5 text-amber-400" />
          Smart Calling
        </div>
        <div className="flex items-center gap-1.5 text-xs font-medium text-amber bg-amber-glow px-2.5 py-1 rounded-full">
          <span className="w-2 h-2 bg-amber rounded-full animate-pulse" />
          Active
        </div>
      </div>
      <div className="px-6 py-4">
        {/* Stats Grid */}
        <div className="grid grid-cols-4 gap-3 mb-5">
          {stats.map(({ value, label }) => (
            <div
              key={label}
              className="text-center py-4 px-2 bg-panel/50 rounded-lg"
            >
              <div className="text-2xl font-bold font-mono text-ink">
                {value}
              </div>
              <div className="text-xs text-ink-2 mt-1">{label}</div>
            </div>
          ))}
        </div>

        {/* Call List */}
        {calls.map((call, idx) => {
          const style = getOutcomeStyle(call.outcome);
          const Icon = style.icon;
          return (
            <div
              key={call.id}
              className={cn(
                "flex items-start gap-3 py-3.5",
                idx !== calls.length - 1 && "border-b border-white/5"
              )}
            >
              <div
                className={cn(
                  "w-8 h-8 rounded-lg flex items-center justify-center",
                  style.bg
                )}
              >
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <div className="text-sm font-semibold text-ink">
                  {call.name}{" "}
                  <span
                    className={cn(
                      "text-xs font-medium uppercase ml-2",
                      style.text
                    )}
                  >
                    {call.outcome.replace("-", " ")}
                  </span>
                </div>
                <div className="text-sm text-ink-2 mt-0.5">
                  {call.summary}
                </div>
                <div className="flex gap-4 mt-2">
                  <button className="text-xs text-amber hover:text-amber-light flex items-center gap-1">
                    <PlayIcon className="w-3 h-3" /> Listen
                  </button>
                  <button className="text-xs text-amber hover:text-amber-light flex items-center gap-1">
                    <DocumentTextIcon className="w-3 h-3" /> Transcript
                  </button>
                </div>
              </div>
              <div className="text-sm text-ink-3 font-mono">
                {call.duration}
              </div>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}

/**
 * What's Working Insights Card
 */
function WhatsWorkingCard({
  whoConverts,
  channelMix,
  discovery,
}: {
  whoConverts: Insight[];
  channelMix: Insight[];
  discovery: string;
}) {
  return (
    <GlassCard className="h-full">
      <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
        <div className="flex items-center gap-2.5 text-sm font-semibold text-ink">
          <LightBulbIcon className="w-5 h-5 text-amber" />
          What's Working
        </div>
        <span className="text-xs text-ink-3">Updated 2h ago</span>
      </div>
      <div className="px-6 py-4">
        <div className="grid grid-cols-2 gap-4">
          {/* Who Converts */}
          <div className="bg-panel/50 rounded-lg p-4">
            <div className="text-[11px] font-semibold text-ink-2 uppercase tracking-wide mb-3">
              Who Converts
            </div>
            {whoConverts.map((item) => (
              <div
                key={item.label}
                className="flex justify-between items-center py-2"
              >
                <span className="text-sm text-ink-2">{item.label}</span>
                <span className="text-sm font-semibold text-amber">
                  {item.value}
                </span>
              </div>
            ))}
          </div>

          {/* Best Channel Mix */}
          <div className="bg-panel/50 rounded-lg p-4">
            <div className="text-[11px] font-semibold text-ink-2 uppercase tracking-wide mb-3">
              Best Channel Mix
            </div>
            {channelMix.map((item) => (
              <div
                key={item.label}
                className="flex justify-between items-center py-2"
              >
                <span className="text-sm text-ink-2">{item.label}</span>
                <span className="text-sm font-semibold text-amber">
                  {item.value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Discovery Banner */}
        <div className="mt-5 p-4 rounded-lg bg-gradient-to-r from-amber/10 to-amber/10 border border-amber/30">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-amber uppercase tracking-wide mb-2">
            <FireIcon className="w-3.5 h-3.5 text-amber" />
            This Week's Discovery
          </div>
          <p className="text-sm text-ink leading-relaxed">{discovery}</p>
        </div>
      </div>
    </GlassCard>
  );
}

/**
 * Week Ahead Calendar Card
 */
function WeekAheadCard({ meetings }: { meetings: Meeting[] }) {
  return (
    <GlassCard className="h-full">
      <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
        <div className="flex items-center gap-2.5 text-sm font-semibold text-ink">
          <CalendarIcon className="w-5 h-5 text-ink-2" />
          Week Ahead
        </div>
        <span className="text-xs text-ink-3">
          {meetings.length} meetings
        </span>
      </div>
      <div className="px-6 py-4">
        {meetings.map((meeting, idx) => (
          <div
            key={meeting.id}
            className={cn(
              "flex items-start gap-3 py-3.5",
              idx !== meetings.length - 1 && "border-b border-white/5"
            )}
          >
            <div
              className={cn(
                "w-2.5 h-2.5 rounded-full mt-1.5",
                meeting.status === "today"
                  ? "bg-amber"
                  : "bg-text-secondary"
              )}
            />
            <div className="flex-1">
              <div className="text-sm text-ink">
                <span className="font-semibold">{meeting.time}</span> —{" "}
                {meeting.title}
              </div>
              <div className="text-sm text-ink-2 mt-0.5">
                {meeting.contact} • {meeting.company}
                {meeting.dealValue && (
                  <span className="text-amber ml-2">
                    {meeting.dealValue} deal
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

/**
 * Stats Summary Row
 */
function StatsSummaryRow() {
  const stats = [
    { value: "68%", label: "Show Rate", change: "↑ 5% vs avg", positive: true },
    { value: "4", label: "Deals Started", change: "↑ 2 this week", positive: true },
    { value: "$47K", label: "Pipeline Value", change: "↑ $12K added", positive: true },
    { value: "8.2x", label: "ROI", change: "Lifetime", neutral: true },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map(({ value, label, change, positive, neutral }) => (
        <GlassCard key={label} className="p-6 hover:bg-bg-cream/50 transition-colors cursor-pointer">
          <div className="text-3xl font-extrabold font-mono text-ink">
            {value}
          </div>
          <div className="text-xs font-medium text-ink-2 uppercase tracking-wide mt-2">
            {label}
          </div>
          <div
            className={cn(
              "text-sm font-medium mt-2",
              neutral ? "text-ink-3" : positive ? "text-amber" : "text-amber"
            )}
          >
            {change}
          </div>
        </GlassCard>
      ))}
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export interface DashboardMainProps {
  className?: string;
}

export function DashboardMain({ className }: DashboardMainProps) {
  // Fetch real meetings data
  const { data: meetingsData, isLoading: meetingsLoading } = useUpcomingMeetings(5);
  
  // Transform API meetings to WeekAhead display format
  const weekAheadMeetings = useMemo(() => {
    if (!meetingsData?.items) return [];
    return transformMeetingsForWeekAhead(meetingsData.items);
  }, [meetingsData?.items]);

  return (
    <div className={cn("space-y-6", className)}>
      {/* Hero Section - Metrics + Channel Status */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-3 md:gap-6">
        <HeroMeetingsCard booked={meetingsData?.total ?? 0} target={10} changePercent={25} />
        <div className="xl:col-span-2">
          <ChannelStatusPanel stats={mockChannelStats} channelStatus={mockChannelStatus} />
        </div>
      </div>

      {/* Stats Summary */}
      <StatsSummaryRow />

      {/* Main Grid - 2 columns for orchestration + activity */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3 md:gap-6">
        <div className="lg:col-span-2">
          <ChannelOrchestrationWheel stats={mockChannelStats} totalTouches={1800} />
        </div>
        <div className="lg:col-span-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-6 h-full">
            <HotProspectsCard prospects={mockProspects} />
            <RecentActivitySummary activities={mockRecentActivity} />
          </div>
        </div>
      </div>

      {/* Secondary Grid - Voice AI + Insights + Calendar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 md:gap-6">
        <VoiceAICard calls={mockVoiceCalls} />
        <WhatsWorkingCard
          whoConverts={mockWhoConverts}
          channelMix={mockChannelMix}
          discovery="Prospects are most responsive on Tuesdays. Pipeline momentum is strongest mid-week."
        />
        <WeekAheadCard meetings={weekAheadMeetings} />
      </div>
    </div>
  );
}

export default DashboardMain;

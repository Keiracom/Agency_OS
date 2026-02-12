"use client";

/**
 * FILE: frontend/app/dashboard/page.tsx
 * PURPOSE: Main dashboard home - customer command center
 * SPRINT: Dashboard Sprint 2 - Dashboard Home
 * SSOT: frontend/design/html-prototypes/dashboard-v4-customer.html
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { 
  Flame, 
  Calendar, 
  Lightbulb, 
  ArrowUpRight,
  TrendingUp,
  Mail,
  Linkedin,
  Phone,
  MessageSquare
} from "lucide-react";

// Australian mock data - Melbourne digital marketing agency
const MOCK_DATA = {
  meetings: {
    current: 18,
    goal: 20,
    percentChange: 28,
  },
  stats: [
    { label: "Show Rate", value: "87%", change: "↑ vs 65% avg", positive: true },
    { label: "Deals Started", value: "4", change: "↑ 2 this week", positive: true },
    { label: "Pipeline Value", value: "$285K", change: "↑ 28% vs last month", positive: true },
    { label: "ROI", value: "38x", change: "$285K from $7.5K", positive: true },
  ],
  hotProspects: [
    {
      id: "1",
      initials: "SC",
      name: "Sarah Chen",
      company: "Bloom Digital",
      title: "Marketing Director",
      signal: "Opened 5x, clicked case study, replied \"interested\"",
      score: 94,
      tier: "hot" as const,
    },
    {
      id: "2",
      initials: "MJ",
      name: "Marcus Johnson",
      company: "TradeFlow Plumbing",
      title: "Owner",
      signal: "LinkedIn reply: \"Let's chat this week\"",
      score: 87,
      tier: "hot" as const,
    },
    {
      id: "3",
      initials: "LP",
      name: "Lisa Park",
      company: "Smile Dental Fitzroy",
      title: "Practice Manager",
      signal: "Opened email 3x in the last hour",
      score: 82,
      tier: "warm" as const,
    },
  ],
  meetings_upcoming: [
    {
      day: "Today",
      date: 12,
      name: "Sarah Chen",
      company: "Bloom Digital",
      time: "2:00 PM",
      type: "Discovery • 30min",
      value: 85000,
    },
    {
      day: "Thu",
      date: 13,
      name: "Marcus Johnson",
      company: "TradeFlow Plumbing",
      time: "10:00 AM",
      type: "Demo • 45min",
      value: 45000,
    },
    {
      day: "Fri",
      date: 14,
      name: "Emma Wilson",
      company: "Coastal Electrical",
      time: "3:30 PM",
      type: "Follow-up • 30min",
      value: 62000,
    },
  ],
  warmReplies: [
    {
      initials: "JK",
      name: "James Kim",
      company: "Velocity Trades",
      preview: "\"Can you send more details about pricing?\"",
    },
    {
      initials: "RN",
      name: "Rachel Nguyen",
      company: "Growth Dental",
      preview: "\"Interested, but timing is Q2. Follow up then?\"",
    },
    {
      initials: "DL",
      name: "David Lee",
      company: "Nexus Plumbing",
      preview: "\"This looks relevant. Can we do a quick call?\"",
    },
  ],
};

// Get tier color classes
function getTierColors(tier: "hot" | "warm" | "cool" | "cold") {
  switch (tier) {
    case "hot":
      return { bg: "rgba(239, 68, 68, 0.1)", border: "rgba(239, 68, 68, 0.3)", text: "#EF4444" };
    case "warm":
      return { bg: "rgba(245, 158, 11, 0.1)", border: "rgba(245, 158, 11, 0.3)", text: "#F59E0B" };
    case "cool":
      return { bg: "rgba(59, 130, 246, 0.1)", border: "rgba(59, 130, 246, 0.3)", text: "#3B82F6" };
    default:
      return { bg: "rgba(107, 114, 128, 0.1)", border: "rgba(107, 114, 128, 0.3)", text: "#6B7280" };
  }
}

// Format currency for AUD
function formatAUD(value: number): string {
  return new Intl.NumberFormat("en-AU", {
    style: "currency",
    currency: "AUD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export default function DashboardPage() {
  const { meetings, stats, hotProspects, meetings_upcoming, warmReplies } = MOCK_DATA;
  const gaugePercent = Math.min((meetings.current / meetings.goal) * 100, 100);
  
  // Calculate SVG arc for gauge
  const gaugeArcLength = 251.2; // Circumference of semicircle
  const gaugeDashOffset = gaugeArcLength - (gaugeArcLength * gaugePercent) / 100;

  return (
    <AppShell pageTitle="Dashboard">
      <div className="space-y-6">
        {/* Greeting Header */}
        <div className="mb-2">
          <h1 className="text-2xl font-serif text-text-primary">
            Good morning, Dave
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            February 12, 2026 • Here's what's happening with your pipeline
          </p>
        </div>

        {/* Hero Card - Meetings vs Goal */}
        <div className="glass-surface rounded-2xl p-8">
          <div className="flex items-center gap-12">
            {/* Left: Meeting count */}
            <div className="flex-1">
              <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
                Meetings This Month
              </p>
              <p className="text-6xl font-bold font-mono text-text-primary leading-none">
                {meetings.current}
              </p>
              <p className="text-base text-text-secondary mt-2">
                Goal: {meetings.goal} •{" "}
                <span className="text-status-success font-medium">
                  {gaugePercent >= 100 ? "Target hit ✓" : `${gaugePercent.toFixed(0)}% complete`}
                </span>
              </p>
              <div className="flex items-center gap-3 mt-5 pt-5 border-t border-border-subtle">
                <TrendingUp className="w-5 h-5 text-status-success" />
                <p className="text-sm text-text-secondary">
                  <span className="text-status-success font-medium">↑ {meetings.percentChange}% vs last month</span>
                  {" "}• Momentum is strong
                </p>
              </div>
            </div>

            {/* Right: Gauge */}
            <div className="w-[200px]">
              <svg viewBox="0 0 200 120" width="200" height="120">
                {/* Background arc */}
                <path
                  d="M 20 100 A 80 80 0 0 1 180 100"
                  fill="none"
                  stroke="rgba(255,255,255,0.08)"
                  strokeWidth="20"
                  strokeLinecap="round"
                />
                {/* Filled arc - amber gradient */}
                <path
                  d="M 20 100 A 80 80 0 0 1 180 100"
                  fill="none"
                  stroke="url(#gaugeGradientAmber)"
                  strokeWidth="20"
                  strokeLinecap="round"
                  strokeDasharray={gaugeArcLength}
                  strokeDashoffset={gaugeDashOffset}
                />
                <defs>
                  <linearGradient id="gaugeGradientAmber" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#D4956A" />
                    <stop offset="100%" stopColor="#E0A87D" />
                  </linearGradient>
                </defs>
              </svg>
              <p className="text-center text-sm font-semibold text-accent-primary mt-2">
                {gaugePercent.toFixed(0)}%{gaugePercent >= 100 ? " — Target Hit" : ""}
              </p>
            </div>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-4 gap-4">
          {stats.map((stat) => (
            <div key={stat.label} className="glass-surface rounded-xl p-5 text-center">
              <p className="text-2xl font-bold font-mono text-text-primary">{stat.value}</p>
              <p className="text-xs text-text-muted uppercase tracking-wider mt-1">{stat.label}</p>
              <p className={`text-xs mt-2 font-medium ${stat.positive ? "text-status-success" : "text-status-error"}`}>
                {stat.change}
              </p>
            </div>
          ))}
        </div>

        {/* Two Column Grid: Hot Prospects + Week Ahead */}
        <div className="grid grid-cols-2 gap-6">
          {/* Hot Right Now */}
          <div className="glass-surface rounded-xl overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-border-subtle">
              <div className="flex items-center gap-2">
                <Flame className="w-5 h-5 text-tier-hot" />
                <h3 className="font-serif font-semibold text-text-primary">Hot Right Now</h3>
              </div>
              <Link href="/dashboard/leads" className="text-sm text-accent-primary hover:underline">
                View all →
              </Link>
            </div>
            <div className="p-5 space-y-3">
              {hotProspects.map((prospect) => {
                const colors = getTierColors(prospect.tier);
                return (
                  <Link
                    key={prospect.id}
                    href={`/dashboard/leads/${prospect.id}`}
                    className="flex items-center gap-4 p-4 rounded-xl transition-all hover:translate-x-1"
                    style={{
                      backgroundColor: colors.bg,
                      borderLeft: `4px solid ${colors.text}`,
                    }}
                  >
                    <div
                      className="w-11 h-11 rounded-full flex items-center justify-center text-white font-semibold text-sm"
                      style={{
                        background: prospect.tier === "hot" 
                          ? "linear-gradient(135deg, #EF4444, #F97316)" 
                          : "linear-gradient(135deg, #F59E0B, #FBBF24)",
                      }}
                    >
                      {prospect.initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-text-primary text-sm">{prospect.name}</p>
                      <p className="text-xs text-text-secondary">{prospect.company} • {prospect.title}</p>
                      <p className="text-xs mt-1" style={{ color: colors.text }}>{prospect.signal}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xl font-bold font-mono" style={{ color: colors.text }}>
                        {prospect.score}
                      </p>
                      <p className="text-[10px] text-text-muted uppercase">Score</p>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Your Week Ahead */}
          <div className="glass-surface rounded-xl overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-border-subtle">
              <div className="flex items-center gap-2">
                <Calendar className="w-5 h-5 text-accent-primary" />
                <h3 className="font-serif font-semibold text-text-primary">Your Week Ahead</h3>
              </div>
              <Link href="/meetings" className="text-sm text-accent-primary hover:underline">
                See calendar →
              </Link>
            </div>
            <div className="p-5 space-y-3">
              {meetings_upcoming.map((meeting, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-4 p-4 rounded-xl"
                  style={{ backgroundColor: "rgba(255,255,255,0.03)" }}
                >
                  <div className="text-center min-w-[50px]">
                    <p className="text-xs text-text-muted uppercase">{meeting.day}</p>
                    <p className="text-2xl font-bold font-mono text-text-primary">{meeting.date}</p>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-text-primary text-sm">{meeting.name}</p>
                    <p className="text-xs text-text-secondary">{meeting.company}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <p className="text-xs text-accent-primary font-medium">{meeting.time}</p>
                      <p className="text-xs text-text-muted">{meeting.type}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold font-mono text-status-success">
                      {formatAUD(meeting.value)}
                    </p>
                    <p className="text-[10px] text-text-muted">Potential</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Two Column Grid: Insight + Warm Replies */}
        <div className="grid grid-cols-2 gap-6">
          {/* What's Working - Insight Card */}
          <div 
            className="rounded-xl p-6"
            style={{
              background: "linear-gradient(135deg, rgba(212, 149, 106, 0.1), rgba(124, 58, 237, 0.05))",
              border: "1px solid rgba(212, 149, 106, 0.2)",
            }}
          >
            <Lightbulb className="w-8 h-8 text-accent-primary mb-4" />
            <h3 className="font-serif text-xl font-semibold text-text-primary mb-2">
              LinkedIn is your best channel
            </h3>
            <p className="text-sm text-text-secondary leading-relaxed">
              Your LinkedIn outreach is booking{" "}
              <strong className="text-text-primary">2.4x more meetings</strong> than email this month.
              We've shifted 60% of your outreach there automatically.
            </p>
          </div>

          {/* Warm Replies */}
          <div className="glass-surface rounded-xl overflow-hidden">
            <div className="flex items-center gap-3 p-5 border-b border-border-subtle">
              <span className="px-3 py-1 rounded-full text-sm font-bold bg-status-success text-white">
                {warmReplies.length}
              </span>
              <h3 className="font-serif font-semibold text-text-primary">Warm replies to review</h3>
            </div>
            <div className="divide-y divide-border-subtle">
              {warmReplies.map((reply, idx) => (
                <div key={idx} className="flex items-center gap-3 p-4">
                  <div className="w-10 h-10 rounded-full bg-bg-elevated flex items-center justify-center text-text-muted font-semibold text-sm">
                    {reply.initials}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text-primary">
                      {reply.name} • {reply.company}
                    </p>
                    <p className="text-xs text-text-secondary truncate">{reply.preview}</p>
                  </div>
                  <button className="px-4 py-2 rounded-lg text-sm font-medium gradient-premium text-white hover:opacity-90 transition-opacity">
                    Reply
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

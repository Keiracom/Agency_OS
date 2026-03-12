"use client";

/**
 * Dashboard (Command Center)
 * CEO Directive #027 — Pure Bloomberg Design System
 * Warm Charcoal + Amber ONLY
 */

import { AppShell } from "@/components/layout/AppShell";
import { GlassCard, HeroMetricCard } from "@/components/ui/GlassCard";
import {
  Flame,
  PhoneCall,
  Lightbulb,
  Zap,
  Calendar,
  CheckCircle2,
  Clock,
  Mail,
  Linkedin,
  MessageSquare,
  Phone,
  Send,
  Play,
  FileText,
  TrendingUp,
  ArrowUpRight,
} from "lucide-react";
// TODO: wire channel-orchestration when API exposes per-channel touch counts
import { mockChannelOrchestration } from "@/data/mock-dashboard";
// TODO: wire smart-calling when voice AI call data API is available
import { mockVoiceStats, mockRecentCalls } from "@/data/mock-dashboard";
// TODO: wire what's-working insights (who-converts + best-channel-mix) when segment analytics API is available
import { mockInsights } from "@/data/mock-dashboard";
// TODO: wire activity-feed when activity stream API is available
import { mockActivityFeed } from "@/data/mock-dashboard";
import { useDashboardV4 } from "@/hooks/use-dashboard-v4";
import Link from "next/link";

// Channel icon component
const ChannelIcon = ({ type }: { type: string }) => {
  const icons: Record<string, React.ReactNode> = {
    email: <Mail className="w-4 h-4" strokeWidth={1.5} />,
    linkedin: <Linkedin className="w-4 h-4" strokeWidth={1.5} />,
    sms: <MessageSquare className="w-4 h-4" strokeWidth={1.5} />,
    voice: <Phone className="w-4 h-4" strokeWidth={1.5} />,
    mail: <Send className="w-4 h-4" strokeWidth={1.5} />,
  };
  return <>{icons[type] || icons.email}</>;
};

export default function DashboardPage() {
  // Fetch real dashboard data (meetings goal, stats, hot prospects, week ahead, warm replies)
  const { data: dashboardData, isLoading: dashboardLoading } = useDashboardV4();

  const meetingsBooked = dashboardData?.meetingsGoal.current ?? 0;
  const meetingsTarget = dashboardData?.meetingsGoal.target ?? 10;

  // Map quickStats changeDirection → positive flag used by the card
  const statsGrid = dashboardData?.quickStats.map((s, i) => ({
    id: `stat-${i}`,
    value: s.value,
    label: s.label,
    change: s.change,
    positive:
      s.changeDirection === "up"
        ? true
        : s.changeDirection === "down"
        ? false
        : null,
  })) ?? [];

  return (
    <AppShell>
      {/* Page background with ambient radials */}
      <div 
        className="relative p-8 min-h-screen overflow-hidden"
        style={{
          background: `
            radial-gradient(ellipse at 20% 0%, rgba(212,149,106,0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 100%, rgba(212,149,106,0.04) 0%, transparent 50%),
            var(--bg-void)
          `,
        }}
      >
        <div className="relative z-10">
          {/* ROW 1: Hero Section - 2 column grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Meetings Booked Hero - Accent Glass Card */}
            <HeroMetricCard className="p-8">
              <div className="text-[11px] font-mono font-semibold uppercase tracking-wider text-text-muted mb-3">
                Meetings Booked
              </div>
              <div className="flex items-baseline gap-0">
                <span className="text-6xl font-extrabold text-text-primary font-mono tracking-tight">
                  {meetingsBooked}
                </span>
                <span className="text-3xl font-extrabold text-text-muted font-mono">
                  /{meetingsTarget}
                </span>
              </div>
              <div className="text-base text-text-secondary mt-3">
                {meetingsBooked >= meetingsTarget ? (
                  <span className="text-amber font-semibold">Target exceeded</span>
                ) : (
                  <span className="text-text-muted">{meetingsTarget - meetingsBooked} to go</span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-4 pt-4 border-t border-amber/20 text-sm">
                <ArrowUpRight className="w-4 h-4 text-amber" strokeWidth={1.5} />
                <span className="text-amber font-mono">{Math.round((meetingsBooked / Math.max(meetingsTarget, 1)) * 100)}%</span>
                <span className="text-text-secondary">of target</span>
              </div>
            </HeroMetricCard>

            {/* Channel Orchestration — TODO: wire to real per-channel touch counts */}
            <GlassCard className="p-8">
              <div className="text-[11px] font-mono font-semibold uppercase tracking-wider text-text-muted mb-4 text-center">
                5-Channel Orchestration
              </div>
              
              {/* Donut Chart Container */}
              <div className="flex justify-center mb-6">
                <div className="relative w-48 h-48">
                  <svg className="w-full h-full" viewBox="0 0 200 200">
                    <circle cx="100" cy="100" r="80" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="12"/>
                    <circle 
                      cx="100" cy="100" r="80" 
                      fill="none" 
                      stroke="url(#donut-gradient)" 
                      strokeWidth="12" 
                      strokeDasharray="380 503" 
                      strokeLinecap="round" 
                      transform="rotate(-90 100 100)"
                    />
                    <defs>
                      <linearGradient id="donut-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#D4956A"/>
                        <stop offset="100%" stopColor="#E8B48A"/>
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                    <div className="text-4xl font-extrabold font-mono text-amber">
                      1.8K
                    </div>
                    <div className="text-xs text-text-muted uppercase tracking-wider font-mono">Touches</div>
                  </div>
                </div>
              </div>

              {/* Channel Icons - All amber */}
              <div className="flex justify-center gap-4 mb-6">
                {['email', 'linkedin', 'sms', 'voice', 'mail'].map((channel) => (
                  <div key={channel} className="w-10 h-10 rounded-lg bg-amber-glow flex items-center justify-center text-amber">
                    <ChannelIcon type={channel} />
                  </div>
                ))}
              </div>

              {/* Channel Stats */}
              <div className="grid grid-cols-5 gap-2">
                {mockChannelOrchestration.channels.map((channel) => (
                  <div key={channel.id} className="text-center p-3 bg-bg-elevated rounded-lg">
                    <div className="text-lg font-bold font-mono text-text-primary">{channel.value}</div>
                    <div className="text-[10px] text-text-muted uppercase mt-1 font-mono">{channel.label}</div>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>

          {/* ROW 2: Stats Grid - 4 column */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {statsGrid.map((stat) => (
              <GlassCard key={stat.id} glow className="p-6">
                <div className="text-3xl font-extrabold font-mono text-text-primary">{stat.value}</div>
                <div className="text-xs font-mono text-text-muted uppercase tracking-wider mt-2">
                  {stat.label}
                </div>
                <div className={`text-sm font-mono mt-2 ${
                  stat.positive === true ? 'text-amber' : 
                  stat.positive === false ? 'text-error' : 'text-text-muted'
                }`}>
                  {stat.change}
                </div>
              </GlassCard>
            ))}
          </div>

          {/* ROW 3: Main Grid - 3 column */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Hot Prospects — wired to useDashboardV4 */}
            <GlassCard className="p-0 overflow-hidden">
              <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-sm font-semibold text-text-primary">
                  <Flame className="w-5 h-5 text-amber" strokeWidth={1.5} />
                  Hot Right Now
                </div>
                <Link href="/dashboard/leads" className="text-sm text-amber hover:underline">
                  See All →
                </Link>
              </div>
              <div className="px-6 py-4">
                {(dashboardData?.hotProspects ?? []).map((prospect) => (
                  <div 
                    key={prospect.id}
                    className="flex items-center gap-4 py-4 border-b border-border-subtle last:border-0 cursor-pointer hover:bg-bg-elevated hover:-mx-6 hover:px-6 transition-all"
                  >
                    <div className="w-11 h-11 rounded-lg flex items-center justify-center text-bg-void text-sm font-semibold bg-gradient-to-br from-amber to-amber-light">
                      {prospect.initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm text-text-primary">{prospect.name}</div>
                      <div className="text-sm text-text-secondary mt-0.5">
                        {prospect.company} • {prospect.title}
                      </div>
                      <div className="flex gap-1.5 mt-1.5">
                        <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded uppercase tracking-wide bg-amber-glow text-amber">
                          {prospect.signal}
                        </span>
                        {prospect.isVeryHot && (
                          <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded uppercase tracking-wide bg-amber-glow text-amber">
                            Very Hot
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-extrabold font-mono text-amber">
                        {prospect.score}
                      </div>
                      <div className="text-[10px] text-text-muted uppercase font-mono">Score</div>
                    </div>
                  </div>
                ))}
                {!dashboardLoading && (dashboardData?.hotProspects ?? []).length === 0 && (
                  <div className="py-8 text-center text-text-muted text-sm">
                    No hot prospects yet
                  </div>
                )}
              </div>
            </GlassCard>

            {/* Smart Calling — TODO: wire smart-calling when voice AI call data API is available */}
            <GlassCard className="p-0 overflow-hidden">
              <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-sm font-semibold text-text-primary">
                  <PhoneCall className="w-5 h-5 text-amber" strokeWidth={1.5} />
                  Smart Calling
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-glow border border-amber/30 rounded-full text-xs font-mono font-medium text-amber">
                  <div className="w-2 h-2 bg-amber rounded-full animate-pulse" />
                  Active
                </div>
              </div>
              <div className="p-6">
                {/* Voice Stats */}
                <div className="grid grid-cols-4 gap-3 mb-5">
                  <div className="text-center p-4 bg-bg-elevated rounded-lg">
                    <div className="text-2xl font-bold font-mono text-text-primary">{mockVoiceStats.calls}</div>
                    <div className="text-[11px] text-text-muted mt-1 font-mono">Calls</div>
                  </div>
                  <div className="text-center p-4 bg-bg-elevated rounded-lg">
                    <div className="text-2xl font-bold font-mono text-text-primary">{mockVoiceStats.connected}</div>
                    <div className="text-[11px] text-text-muted mt-1 font-mono">Connect</div>
                  </div>
                  <div className="text-center p-4 bg-bg-elevated rounded-lg">
                    <div className="text-2xl font-bold font-mono text-text-primary">{mockVoiceStats.booked}</div>
                    <div className="text-[11px] text-text-muted mt-1 font-mono">Booked</div>
                  </div>
                  <div className="text-center p-4 bg-bg-elevated rounded-lg">
                    <div className="text-2xl font-bold font-mono text-text-primary">{mockVoiceStats.rate}</div>
                    <div className="text-[11px] text-text-muted mt-1 font-mono">Rate</div>
                  </div>
                </div>

                {/* Recent Calls */}
                {mockRecentCalls.map((call) => (
                  <div key={call.id} className="flex items-start gap-3 py-3.5 border-b border-border-subtle last:border-0">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      call.outcome === 'BOOKED' ? 'bg-amber-glow text-amber' : 'bg-bg-elevated text-text-secondary'
                    }`}>
                      {call.outcome === 'BOOKED' ? <CheckCircle2 className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm">
                        <span className="font-semibold text-text-primary">{call.name}</span>
                        <span className={`ml-2 text-xs font-mono font-medium ${
                          call.outcome === 'BOOKED' ? 'text-amber' : 'text-text-secondary'
                        }`}>
                          {call.outcome}
                        </span>
                      </div>
                      <div className="text-sm text-text-secondary mt-1">{call.summary}</div>
                      <div className="flex gap-4 mt-2">
                        <button className="text-xs text-amber flex items-center gap-1 hover:underline">
                          <Play className="w-3 h-3" /> Listen
                        </button>
                        <button className="text-xs text-amber flex items-center gap-1 hover:underline">
                          <FileText className="w-3 h-3" /> Transcript
                        </button>
                      </div>
                    </div>
                    <div className="text-sm text-text-muted font-mono">{call.duration}</div>
                  </div>
                ))}
              </div>
            </GlassCard>

            {/* What's Working — TODO: wire who-converts + best-channel-mix when segment analytics API is available */}
            <GlassCard className="p-0 overflow-hidden">
              <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-sm font-semibold text-text-primary">
                  <Lightbulb className="w-5 h-5 text-amber" strokeWidth={1.5} />
                  What's Working
                </div>
                <span className="text-xs text-text-muted font-mono">Updated 2h ago</span>
              </div>
              <div className="p-6">
                {/* Insights Grid */}
                <div className="grid grid-cols-2 gap-4 mb-5">
                  <div className="bg-bg-elevated rounded-lg p-4">
                    <div className="text-[11px] font-mono font-semibold uppercase tracking-wider text-text-muted mb-3">
                      Who Converts
                    </div>
                    {mockInsights.whoConverts.map((item: { label: string; value: string }, i: number) => (
                      <div key={i} className="flex justify-between items-center py-2">
                        <span className="text-sm text-text-secondary">{item.label}</span>
                        <span className="text-sm font-semibold font-mono text-amber">{item.value}</span>
                      </div>
                    ))}
                  </div>
                  <div className="bg-bg-elevated rounded-lg p-4">
                    <div className="text-[11px] font-mono font-semibold uppercase tracking-wider text-text-muted mb-3">
                      Best Channel Mix
                    </div>
                    {mockInsights.bestChannelMix.map((item: { label: string; value: string }, i: number) => (
                      <div key={i} className="flex justify-between items-center py-2">
                        <span className="text-sm text-text-secondary">{item.label}</span>
                        <span className="text-sm font-semibold font-mono text-amber">{item.value}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Discovery Banner — wired to useDashboardV4 insight */}
                <div className="p-4 rounded-lg bg-amber-glow border border-amber/30">
                  <div className="flex items-center gap-1.5 text-[11px] font-mono font-semibold uppercase tracking-wider text-amber mb-2">
                    <Flame className="w-4 h-4" strokeWidth={1.5} />
                    This Week's Discovery
                  </div>
                  <div className="text-sm text-text-primary leading-relaxed">
                    {dashboardData?.insight.detail ?? mockInsights.discovery}
                  </div>
                </div>
              </div>
            </GlassCard>
          </div>

          {/* ROW 4: Bottom Grid - 3 column */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Recent Activity — TODO: wire activity-feed when activity stream API is available */}
            <GlassCard className="p-0 overflow-hidden">
              <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-sm font-semibold text-text-primary">
                  <Zap className="w-5 h-5 text-amber" strokeWidth={1.5} />
                  Recent Activity
                </div>
                <Link href="/activity" className="text-sm text-amber hover:underline">
                  View All →
                </Link>
              </div>
              <div className="px-6 py-4 max-h-80 overflow-y-auto">
                {mockActivityFeed.map((item) => (
                  <div key={item.id} className="flex items-start gap-3 py-3 border-b border-border-subtle last:border-0">
                    <div className="w-8 h-8 rounded-lg bg-amber-glow flex items-center justify-center text-amber">
                      <ChannelIcon type={item.type || 'email'} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-text-primary">{item.text}</div>
                      <div className="text-xs text-text-muted mt-1 font-mono">{item.time}</div>
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>

            {/* Week Ahead — wired to useDashboardV4 weekAhead */}
            <GlassCard className="p-0 overflow-hidden">
              <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-sm font-semibold text-text-primary">
                  <Calendar className="w-5 h-5 text-amber" strokeWidth={1.5} />
                  Week Ahead
                </div>
                <Link href="/calendar" className="text-sm text-amber hover:underline">
                  Full Calendar →
                </Link>
              </div>
              <div className="px-6 py-4">
                {(dashboardData?.weekAhead ?? []).map((meeting) => (
                  <div key={meeting.id} className="flex items-center gap-4 py-3.5 border-b border-border-subtle last:border-0">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold text-text-primary">{meeting.type}</div>
                      <div className="text-sm text-text-secondary mt-0.5">
                        {meeting.name} • {meeting.company}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-amber font-mono">
                        {meeting.dayLabel} {meeting.time}
                      </div>
                      {meeting.potentialValue > 0 && (
                        <div className="text-xs text-text-muted font-mono">
                          ${meeting.potentialValue.toLocaleString()}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {!dashboardLoading && (dashboardData?.weekAhead ?? []).length === 0 && (
                  <div className="py-8 text-center text-text-muted text-sm">
                    No upcoming meetings
                  </div>
                )}
              </div>
            </GlassCard>

            {/* Warm Replies — wired to useDashboardV4 warmReplies */}
            <GlassCard className="p-0 overflow-hidden">
              <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-sm font-semibold text-text-primary">
                  <MessageSquare className="w-5 h-5 text-amber" strokeWidth={1.5} />
                  Warm Replies
                </div>
                <Link href="/replies" className="text-sm text-amber hover:underline">
                  See All →
                </Link>
              </div>
              <div className="px-6 py-4">
                {(dashboardData?.warmReplies ?? []).map((reply) => (
                  <div key={reply.id} className="py-3.5 border-b border-border-subtle last:border-0">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber to-amber-light flex items-center justify-center text-bg-void text-xs font-semibold">
                          {reply.initials}
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-text-primary">{reply.name}</div>
                          <div className="text-xs text-text-muted">{reply.company}</div>
                        </div>
                      </div>
                    </div>
                    <p className="text-sm text-text-secondary line-clamp-2 italic">{reply.preview}</p>
                  </div>
                ))}
                {!dashboardLoading && (dashboardData?.warmReplies ?? []).length === 0 && (
                  <div className="py-8 text-center text-text-muted text-sm">
                    No warm replies yet
                  </div>
                )}
              </div>
            </GlassCard>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

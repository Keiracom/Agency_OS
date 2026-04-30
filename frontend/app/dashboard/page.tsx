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
// PR4 — mock-data imports removed. The Channel Orchestration / Smart
// Calling / What's Working slots now render a `TodoMockPanel` until
// their endpoints exist. See ./TodoMockPanel.tsx + the JSX below.
import { useLiveActivityFeed } from "@/lib/useLiveActivityFeed";
import { providerLabel } from "@/lib/provider-labels";
import { useDashboardV4 } from "@/hooks/use-dashboard-v4";
import { HeroStrip } from "@/components/dashboard/HeroStrip";
import { TodayStrip } from "@/components/dashboard/TodayStrip";
import { FunnelBar } from "@/components/dashboard/FunnelBar";
import { AttentionCards } from "@/components/dashboard/AttentionCards";
import { ProspectDrawer } from "@/components/dashboard/ProspectDrawer";
// PR2 — dashboard rebuild core components (cream/amber palette, Playfair Display)
import { CycleProgress } from "@/components/dashboard/CycleProgress";
import { PerformanceMetrics } from "@/components/dashboard/PerformanceMetrics";
import { HotReplies } from "@/components/dashboard/HotReplies";
import { SystemHealth } from "@/components/dashboard/SystemHealth";
// PR4 — placeholder for slots whose backend endpoints don't exist yet
import { TodoMockPanel } from "@/components/dashboard/TodoMockPanel";
import Link from "next/link";
import { useState } from "react";

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
  const { activities: activityFeed, isLoading: activityLoading } = useLiveActivityFeed({ limit: 8 });
  const [drawerLeadId, setDrawerLeadId] = useState<string | null>(null);

  // A3: TODO · MOCK badges removed entirely; the underlying empty
  // states are honest now, so the demo-mode hide-badge query is no
  // longer needed by this page.

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
        className="relative p-4 md:p-8 min-h-screen overflow-hidden"
        style={{
          background: `
            radial-gradient(ellipse at 20% 0%, rgba(212,149,106,0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 100%, rgba(212,149,106,0.04) 0%, transparent 50%),
            var(--bg-cream)
          `,
        }}
      >
        <div className="relative z-10">
          {/* PR2 — Cycle progress + performance + hot replies + health */}
          <section className="mb-6 grid gap-5 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-5">
              <CycleProgress />
              <PerformanceMetrics />
              <SystemHealth />
            </div>
            <div className="lg:col-span-1">
              <HotReplies />
            </div>
          </section>

          {/* v10 HOME SURFACES — BDR hero + today + funnel + attention */}
          <section className="mb-8 space-y-6">
            <HeroStrip />
            <TodayStrip />
            <div>
              <div className="text-[11px] font-mono uppercase tracking-[0.16em] text-gray-500 mb-2">
                Cycle funnel
              </div>
              <FunnelBar />
            </div>
            <div>
              <div className="text-[11px] font-mono uppercase tracking-[0.16em] text-gray-500 mb-3">
                Needs your attention
              </div>
              <AttentionCards onLeadClick={(id) => setDrawerLeadId(id)} />
            </div>
          </section>

          {/* ROW 1: Hero Section - 2 column grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 md:gap-6 mb-8">
            {/* Meetings Booked Hero - Accent Glass Card */}
            <HeroMetricCard className="p-8">
              <div className="text-[11px] font-mono font-semibold uppercase tracking-wider text-ink-3 mb-3">
                Meetings Booked
              </div>
              <div className="flex items-baseline gap-0">
                <span className="text-4xl md:text-6xl font-extrabold text-ink font-mono tracking-tight">
                  {meetingsBooked}
                </span>
                <span className="text-2xl md:text-3xl font-extrabold text-ink-3 font-mono">
                  /{meetingsTarget}
                </span>
              </div>
              <div className="text-base text-ink-2 mt-3">
                {meetingsBooked >= meetingsTarget ? (
                  <span className="text-amber font-semibold">Target exceeded</span>
                ) : (
                  <span className="text-ink-3">{meetingsTarget - meetingsBooked} to go</span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-4 pt-4 border-t border-amber/20 text-sm">
                <ArrowUpRight className="w-4 h-4 text-amber" strokeWidth={1.5} />
                <span className="text-amber font-mono">{Math.round((meetingsBooked / Math.max(meetingsTarget, 1)) * 100)}%</span>
                <span className="text-ink-2">of target</span>
              </div>
            </HeroMetricCard>

            {/* Channel Orchestration — TODO: wire to real per-channel touch counts */}
            <GlassCard className="p-8">
              <div className="text-[11px] font-mono font-semibold uppercase tracking-wider text-ink-3 mb-4 text-center">
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
                    <div className="text-xs text-ink-3 uppercase tracking-wider font-mono">Touches</div>
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

              {/* Channel Stats — A3: honest empty state, not fabricated numbers */}
              <TodoMockPanel
                icon={<Zap className="w-4 h-4" strokeWidth={1.6} />}
                eyebrow="Channel breakdown"
                title="Per-channel breakdown coming soon"
                description="Detailed per-channel touch counts will appear here once your campaigns send their first 50 touches."
              />
            </GlassCard>
          </div>

          {/* ROW 2: Stats Grid - 4 column */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 mb-6 md:mb-8">
            {statsGrid.map((stat) => (
              <GlassCard key={stat.id} glow className="p-6">
                <div className="text-3xl font-extrabold font-mono text-ink">{stat.value}</div>
                <div className="text-xs font-mono text-ink-3 uppercase tracking-wider mt-2">
                  {stat.label}
                </div>
                <div className={`text-sm font-mono mt-2 ${
                  stat.positive === true ? 'text-amber' : 
                  stat.positive === false ? 'text-error' : 'text-ink-3'
                }`}>
                  {stat.change}
                </div>
              </GlassCard>
            ))}
          </div>

          {/* ROW 3: Main Grid - 3 column */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 md:gap-6 mb-8">
            {/* Hot Prospects — wired to useDashboardV4 */}
            <GlassCard className="p-0 overflow-hidden">
              <div className="px-6 py-5 border-b border-rule flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-sm font-semibold text-ink">
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
                    className="flex items-center gap-4 py-4 border-b border-rule last:border-0 cursor-pointer hover:bg-panel hover:-mx-6 hover:px-6 transition-all"
                  >
                    <div className="w-11 h-11 rounded-lg flex items-center justify-center text-bg-cream text-sm font-semibold bg-gradient-to-br from-amber to-amber-light">
                      {prospect.initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm text-ink">{prospect.name}</div>
                      <div className="text-sm text-ink-2 mt-0.5">
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
                      <div className="text-[10px] text-ink-3 uppercase font-mono">Score</div>
                    </div>
                  </div>
                ))}
                {!dashboardLoading && (dashboardData?.hotProspects ?? []).length === 0 && (
                  <div className="py-8 text-center text-ink-3 text-sm">
                    No hot prospects yet
                  </div>
                )}
              </div>
            </GlassCard>

            {/* Smart Calling — A3: honest empty state, not fabricated numbers */}
            <TodoMockPanel
              icon={<PhoneCall className="w-4 h-4" strokeWidth={1.6} />}
              eyebrow="Smart calling"
              title="Voice AI call summary coming soon"
              description="Once voice campaigns are active you'll see call outcomes, connect rates, and recent recordings here."
            />

            {/* What's Working — PR4: insight is live, who-converts/channel-mix are mocks */}
            <GlassCard className="p-0 overflow-hidden">
              <div className="px-6 py-5 border-b border-rule flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-sm font-semibold text-ink">
                  <Lightbulb className="w-5 h-5 text-amber" strokeWidth={1.5} />
                  What's Working
                </div>
                <span className="text-xs text-ink-3 font-mono">Updated 2h ago</span>
              </div>
              <div className="p-6 space-y-5">
                {/* Who-converts + channel-mix — A3: honest empty state */}
                <TodoMockPanel
                  icon={<Lightbulb className="w-4 h-4" strokeWidth={1.6} />}
                  eyebrow="Segment analytics"
                  title="Insights coming soon"
                  description="After your first cycle of replies we'll surface which segments convert and which channel mix produces the best meeting yield."
                />

                {/* Discovery Banner — already wired to useDashboardV4 insight */}
                {dashboardData?.insight.detail && (
                  <div className="p-4 rounded-lg bg-amber-glow border border-amber/30">
                    <div className="flex items-center gap-1.5 text-[11px] font-mono font-semibold uppercase tracking-wider text-amber mb-2">
                      <Flame className="w-4 h-4" strokeWidth={1.5} />
                      This Week's Discovery
                    </div>
                    <div className="text-sm text-ink leading-relaxed">
                      {dashboardData.insight.detail}
                    </div>
                  </div>
                )}
              </div>
            </GlassCard>
          </div>

          {/* ROW 4: Bottom Grid - 3 column */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 md:gap-6">
            {/* Recent Activity — wired to useLiveActivityFeed (30s polling) */}
            <GlassCard className="p-0 overflow-hidden">
              <div className="px-6 py-5 border-b border-rule flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-sm font-semibold text-ink">
                  <Zap className="w-5 h-5 text-amber" strokeWidth={1.5} />
                  Recent Activity
                </div>
                <Link href="/activity" className="text-sm text-amber hover:underline">
                  View All →
                </Link>
              </div>
              <div className="px-6 py-4 max-h-80 overflow-y-auto">
                {activityFeed.map((item) => (
                  <div key={item.id} className="flex items-start gap-3 py-3 border-b border-rule last:border-0">
                    <div className="w-8 h-8 rounded-lg bg-amber-glow flex items-center justify-center text-amber">
                      <ChannelIcon type={item.channel || 'email'} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-ink">
                        <span className="font-medium">{item.leadName}</span>
                        {item.company ? <span className="text-ink-2"> · {item.company}</span> : null}
                      </div>
                      <div className="text-xs text-ink-2 mt-0.5">{providerLabel(item.action)}</div>
                      <div className="text-xs text-ink-3 mt-1 font-mono">
                        {new Date(item.createdAt).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
                {!activityLoading && activityFeed.length === 0 && (
                  <div className="py-8 text-center text-ink-3 text-sm">
                    No recent activity
                  </div>
                )}
              </div>
            </GlassCard>

            {/* Week Ahead — wired to useDashboardV4 weekAhead */}
            <GlassCard className="p-0 overflow-hidden">
              <div className="px-6 py-5 border-b border-rule flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-sm font-semibold text-ink">
                  <Calendar className="w-5 h-5 text-amber" strokeWidth={1.5} />
                  Week Ahead
                </div>
                <Link href="/calendar" className="text-sm text-amber hover:underline">
                  Full Calendar →
                </Link>
              </div>
              <div className="px-6 py-4">
                {(dashboardData?.weekAhead ?? []).map((meeting) => (
                  <div key={meeting.id} className="flex items-center gap-4 py-3.5 border-b border-rule last:border-0">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold text-ink">{meeting.type}</div>
                      <div className="text-sm text-ink-2 mt-0.5">
                        {meeting.name} • {meeting.company}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-amber font-mono">
                        {meeting.dayLabel} {meeting.time}
                      </div>
                      {meeting.potentialValue > 0 && (
                        <div className="text-xs text-ink-3 font-mono">
                          ${meeting.potentialValue.toLocaleString()}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {!dashboardLoading && (dashboardData?.weekAhead ?? []).length === 0 && (
                  <div className="py-8 text-center text-ink-3 text-sm">
                    No upcoming meetings
                  </div>
                )}
              </div>
            </GlassCard>

            {/* Warm Replies — wired to useDashboardV4 warmReplies */}
            <GlassCard className="p-0 overflow-hidden">
              <div className="px-6 py-5 border-b border-rule flex items-center justify-between">
                <div className="flex items-center gap-2.5 text-sm font-semibold text-ink">
                  <MessageSquare className="w-5 h-5 text-amber" strokeWidth={1.5} />
                  Warm Replies
                </div>
                <Link href="/replies" className="text-sm text-amber hover:underline">
                  See All →
                </Link>
              </div>
              <div className="px-6 py-4">
                {(dashboardData?.warmReplies ?? []).map((reply) => (
                  <div key={reply.id} className="py-3.5 border-b border-rule last:border-0">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber to-amber-light flex items-center justify-center text-bg-cream text-xs font-semibold">
                          {reply.initials}
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-ink">{reply.name}</div>
                          <div className="text-xs text-ink-3">{reply.company}</div>
                        </div>
                      </div>
                    </div>
                    <p className="text-sm text-ink-2 line-clamp-2 italic">{reply.preview}</p>
                  </div>
                ))}
                {!dashboardLoading && (dashboardData?.warmReplies ?? []).length === 0 && (
                  <div className="py-8 text-center text-ink-3 text-sm">
                    No warm replies yet
                  </div>
                )}
              </div>
            </GlassCard>
          </div>
        </div>
      </div>
      <ProspectDrawer leadId={drawerLeadId} onClose={() => setDrawerLeadId(null)} />
    </AppShell>
  );
}

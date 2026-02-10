"use client";

/**
 * Dashboard (Command Center) v2
 * Glassmorphism visual overhaul based on dashboard-v2.html prototype
 */

import { AppShell } from "@/components/layout/AppShell";
import { GlassCard } from "@/components/ui/GlassCard";
import {
  mockMeetingsHero,
  mockChannelOrchestration,
  mockStatsGrid,
  mockHotProspects,
  mockVoiceStats,
  mockRecentCalls,
  mockInsights,
  mockActivityFeed,
  mockWeekAhead,
  mockWarmReplies,
} from "@/data/mock-dashboard";
import Link from "next/link";

// Icons
const FireIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" className="w-5 h-5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" />
  </svg>
);

const PhoneIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" className="w-5 h-5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
  </svg>
);

const LightbulbIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" className="w-5 h-5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
  </svg>
);

const BoltIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" className="w-5 h-5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
);

const CalendarIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" className="w-5 h-5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
  </svg>
);

const CheckIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24" className="w-3.5 h-3.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
  </svg>
);

const ClockIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" className="w-3.5 h-3.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

// Channel Icons
const EmailIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" className="w-4.5 h-4.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
  </svg>
);

const LinkedInIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" className="w-4.5 h-4.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
  </svg>
);

const SmsIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" className="w-4.5 h-4.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
  </svg>
);

const VoiceIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" className="w-4.5 h-4.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
  </svg>
);

const MailIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" className="w-4.5 h-4.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
  </svg>
);

export default function DashboardPage() {
  return (
    <AppShell>
      <div className="relative p-8 bg-bg-void min-h-screen overflow-hidden">
        {/* Ambient Background Orbs - VISIBLE now */}
        <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
          {/* Purple orb - top right - VISIBLE */}
          <div 
            className="absolute -top-20 -right-20 w-[600px] h-[600px] rounded-full opacity-30"
            style={{
              background: 'radial-gradient(circle, #7C3AED 0%, transparent 60%)',
              filter: 'blur(80px)',
            }}
          />
          {/* Blue orb - bottom left - VISIBLE */}
          <div 
            className="absolute -bottom-20 -left-20 w-[550px] h-[550px] rounded-full opacity-25"
            style={{
              background: 'radial-gradient(circle, #3B82F6 0%, transparent 60%)',
              filter: 'blur(70px)',
            }}
          />
          {/* Teal/cyan orb - center-right */}
          <div 
            className="absolute top-1/3 right-1/4 w-[400px] h-[400px] rounded-full opacity-20"
            style={{
              background: 'radial-gradient(circle, #06B6D4 0%, transparent 60%)',
              filter: 'blur(60px)',
            }}
          />
        </div>
        
        {/* Content layer - above ambient background */}
        <div className="relative z-10">
        {/* ROW 1: Hero Section - 2 column grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Meetings Booked Hero */}
          <GlassCard accentTop className="p-8">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-3">
              Meetings Booked
            </div>
            <div className="flex items-baseline gap-0">
              <span className="text-6xl font-extrabold text-text-primary font-mono tracking-tight">
                {mockMeetingsHero.current}
              </span>
              <span className="text-3xl font-extrabold text-text-muted font-mono">
                /{mockMeetingsHero.target}
              </span>
            </div>
            <div className="text-base text-text-secondary mt-3">
              <span className="text-status-success font-semibold">Target exceeded</span> — 3 days early
            </div>
            <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border-subtle text-sm">
              <span className="text-status-success">↑ {mockMeetingsHero.trendPercent}%</span>
              <span className="text-text-secondary">{mockMeetingsHero.trendLabel}</span>
            </div>
          </GlassCard>

          {/* Channel Orchestration */}
          <GlassCard className="p-8">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-4 text-center">
              5-Channel Orchestration
            </div>
            
            {/* Donut Chart Container */}
            <div className="flex justify-center mb-6">
              <div className="relative w-48 h-48">
                <svg className="w-full h-full" viewBox="0 0 200 200">
                  <circle cx="100" cy="100" r="80" fill="none" stroke="#221F30" strokeWidth="12"/>
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
                      <stop offset="0%" stopColor="#7C3AED"/>
                      <stop offset="100%" stopColor="#3B82F6"/>
                    </linearGradient>
                  </defs>
                </svg>
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                  <div className="text-4xl font-extrabold font-mono bg-gradient-to-r from-accent-primary to-accent-blue bg-clip-text text-transparent">
                    1.8K
                  </div>
                  <div className="text-xs text-text-muted uppercase tracking-wider">Touches</div>
                </div>
              </div>
            </div>

            {/* Channel Icons */}
            <div className="flex justify-center gap-4 mb-6">
              <div className="w-10 h-10 rounded-lg bg-accent-primary/15 flex items-center justify-center text-accent-primary">
                <EmailIcon />
              </div>
              <div className="w-10 h-10 rounded-lg bg-accent-blue/15 flex items-center justify-center text-accent-blue">
                <LinkedInIcon />
              </div>
              <div className="w-10 h-10 rounded-lg bg-accent-teal/15 flex items-center justify-center text-accent-teal">
                <SmsIcon />
              </div>
              <div className="w-10 h-10 rounded-lg bg-status-warning/15 flex items-center justify-center text-status-warning">
                <VoiceIcon />
              </div>
              <div className="w-10 h-10 rounded-lg bg-pink-500/15 flex items-center justify-center text-pink-500">
                <MailIcon />
              </div>
            </div>

            {/* Channel Stats */}
            <div className="grid grid-cols-5 gap-2">
              {mockChannelOrchestration.channels.map((channel) => (
                <div key={channel.id} className="text-center p-3 bg-bg-surface-hover rounded-lg">
                  <div className="text-lg font-bold font-mono text-text-primary">{channel.value}</div>
                  <div className="text-[10px] text-text-muted uppercase mt-1">{channel.label}</div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>

        {/* ROW 2: Stats Grid - 4 column */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {mockStatsGrid.map((stat) => (
            <GlassCard key={stat.id} glow className="p-6">
              <div className="text-3xl font-extrabold font-mono text-text-primary">{stat.value}</div>
              <div className="text-xs font-medium text-text-muted uppercase tracking-wider mt-2">
                {stat.label}
              </div>
              <div className={`text-sm font-medium mt-2 ${
                stat.positive === true ? 'text-status-success' : 
                stat.positive === false ? 'text-status-error' : 'text-text-muted'
              }`}>
                {stat.change}
              </div>
            </GlassCard>
          ))}
        </div>

        {/* ROW 3: Main Grid - 3 column */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Hot Prospects */}
          <GlassCard className="p-0 overflow-hidden">
            <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
              <div className="flex items-center gap-2.5 text-sm font-semibold text-text-primary">
                <span className="text-tier-hot"><FireIcon /></span>
                Hot Right Now
              </div>
              <Link href="/leads" className="text-sm text-accent-primary hover:underline">
                See All →
              </Link>
            </div>
            <div className="px-6 py-4">
              {mockHotProspects.map((prospect) => (
                <div 
                  key={prospect.id}
                  className="flex items-center gap-4 py-4 border-b border-border-subtle last:border-0 cursor-pointer hover:bg-bg-surface-hover hover:-mx-6 hover:px-6 transition-all"
                >
                  <div className={`w-11 h-11 rounded-lg flex items-center justify-center text-white text-sm font-semibold ${
                    prospect.tier === 'hot' 
                      ? 'bg-gradient-to-br from-tier-hot to-orange-500' 
                      : 'bg-gradient-to-br from-tier-warm to-yellow-400'
                  }`}>
                    {prospect.initials}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm text-text-primary">{prospect.name}</div>
                    <div className="text-sm text-text-secondary mt-0.5">
                      {prospect.company} • {prospect.title}
                    </div>
                    <div className="flex gap-1.5 mt-1.5">
                      {prospect.badges.map((badge, i) => (
                        <span 
                          key={i}
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wide ${
                            badge.variant === 'hot' ? 'bg-tier-hot/15 text-tier-hot' :
                            badge.variant === 'ceo' ? 'bg-accent-primary/15 text-accent-primary' :
                            'bg-status-success/15 text-status-success'
                          }`}
                        >
                          {badge.label}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-2xl font-extrabold font-mono ${
                      prospect.tier === 'hot' ? 'text-tier-hot' : 'text-tier-warm'
                    }`}>
                      {prospect.score}
                    </div>
                    <div className="text-[10px] text-text-muted uppercase">Score</div>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Smart Calling */}
          <GlassCard className="p-0 overflow-hidden">
            <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
              <div className="flex items-center gap-2.5 text-sm font-semibold text-text-primary">
                <span className="text-status-warning"><PhoneIcon /></span>
                Smart Calling
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 bg-status-success/10 border border-status-success/30 rounded-full text-xs font-medium text-status-success">
                <div className="w-2 h-2 bg-status-success rounded-full animate-pulse" />
                Active
              </div>
            </div>
            <div className="p-6">
              {/* Voice Stats */}
              <div className="grid grid-cols-4 gap-3 mb-5">
                <div className="text-center p-4 bg-bg-surface-hover rounded-lg">
                  <div className="text-2xl font-bold font-mono text-text-primary">{mockVoiceStats.calls}</div>
                  <div className="text-[11px] text-text-muted mt-1">Calls</div>
                </div>
                <div className="text-center p-4 bg-bg-surface-hover rounded-lg">
                  <div className="text-2xl font-bold font-mono text-text-primary">{mockVoiceStats.connected}</div>
                  <div className="text-[11px] text-text-muted mt-1">Connect</div>
                </div>
                <div className="text-center p-4 bg-bg-surface-hover rounded-lg">
                  <div className="text-2xl font-bold font-mono text-text-primary">{mockVoiceStats.booked}</div>
                  <div className="text-[11px] text-text-muted mt-1">Booked</div>
                </div>
                <div className="text-center p-4 bg-bg-surface-hover rounded-lg">
                  <div className="text-2xl font-bold font-mono text-text-primary">{mockVoiceStats.rate}</div>
                  <div className="text-[11px] text-text-muted mt-1">Rate</div>
                </div>
              </div>

              {/* Recent Calls */}
              {mockRecentCalls.map((call) => (
                <div key={call.id} className="flex items-start gap-3 py-3.5 border-b border-border-subtle last:border-0">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    call.outcome === 'BOOKED' ? 'bg-status-success/15 text-status-success' : 'bg-accent-blue/15 text-accent-blue'
                  }`}>
                    {call.outcome === 'BOOKED' ? <CheckIcon /> : <ClockIcon />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm">
                      <span className="font-semibold text-text-primary">{call.name}</span>
                      <span className={`ml-2 text-xs font-medium ${
                        call.outcome === 'BOOKED' ? 'text-status-success' : 'text-accent-blue'
                      }`}>
                        {call.outcome}
                      </span>
                    </div>
                    <div className="text-sm text-text-secondary mt-1">{call.summary}</div>
                    <div className="flex gap-4 mt-2">
                      <button className="text-xs text-accent-primary flex items-center gap-1 hover:underline">
                        ▶ Listen
                      </button>
                      <button className="text-xs text-accent-primary flex items-center gap-1 hover:underline">
                        📄 Transcript
                      </button>
                    </div>
                  </div>
                  <div className="text-sm text-text-muted font-mono">{call.duration}</div>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* What's Working */}
          <GlassCard className="p-0 overflow-hidden">
            <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
              <div className="flex items-center gap-2.5 text-sm font-semibold text-text-primary">
                <span className="text-accent-primary"><LightbulbIcon /></span>
                What's Working
              </div>
              <span className="text-xs text-text-muted">Updated 2h ago</span>
            </div>
            <div className="p-6">
              {/* Insights Grid */}
              <div className="grid grid-cols-2 gap-4 mb-5">
                <div className="bg-bg-surface-hover rounded-lg p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-3">
                    Who Converts
                  </div>
                  {mockInsights.whoConverts.map((item, i) => (
                    <div key={i} className="flex justify-between items-center py-2">
                      <span className="text-sm text-text-secondary">{item.label}</span>
                      <span className="text-sm font-semibold text-status-success">{item.value}</span>
                    </div>
                  ))}
                </div>
                <div className="bg-bg-surface-hover rounded-lg p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-3">
                    Best Channel Mix
                  </div>
                  {mockInsights.bestChannelMix.map((item, i) => (
                    <div key={i} className="flex justify-between items-center py-2">
                      <span className="text-sm text-text-secondary">{item.label}</span>
                      <span className="text-sm font-semibold text-status-success">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Discovery Banner */}
              <div className="p-4 rounded-lg bg-gradient-to-r from-accent-primary/10 to-accent-blue/10 border border-accent-primary/30">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-accent-primary mb-2">
                  <span className="text-tier-hot"><FireIcon /></span>
                  This Week's Discovery
                </div>
                <div className="text-sm text-text-primary leading-relaxed">
                  {mockInsights.discovery}
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* ROW 4: Bottom Grid - 3 column */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Activity */}
          <GlassCard className="p-0 overflow-hidden">
            <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
              <div className="flex items-center gap-2.5 text-sm font-semibold text-text-primary">
                <span className="text-status-warning"><BoltIcon /></span>
                Recent Activity
              </div>
              <span className="text-xs text-text-muted">Live</span>
            </div>
            <div className="p-6">
              {mockActivityFeed.map((activity) => (
                <div key={activity.id} className="flex items-start gap-3 py-3.5 border-b border-border-subtle last:border-0">
                  <div className={`w-2.5 h-2.5 rounded-full mt-1.5 ${
                    activity.status === 'success' ? 'bg-status-success' :
                    activity.status === 'warning' ? 'bg-status-warning' : 'bg-accent-blue'
                  }`} />
                  <div className="flex-1">
                    <div className="text-sm text-text-primary">
                      {activity.text}
                      {activity.subtext && <span className="text-text-muted"> {activity.subtext}</span>}
                    </div>
                    <div className="text-xs text-text-muted mt-1">{activity.time}</div>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Week Ahead */}
          <GlassCard className="p-0 overflow-hidden">
            <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
              <div className="flex items-center gap-2.5 text-sm font-semibold text-text-primary">
                <span className="text-accent-blue"><CalendarIcon /></span>
                Week Ahead
              </div>
              <span className="text-xs text-text-muted">{mockWeekAhead.length} meetings</span>
            </div>
            <div className="p-6">
              {mockWeekAhead.map((meeting) => (
                <div key={meeting.id} className="flex items-start gap-3 py-3.5 border-b border-border-subtle last:border-0">
                  <div className={`w-2.5 h-2.5 rounded-full mt-1.5 ${
                    meeting.status === 'success' ? 'bg-status-success' : 'bg-accent-blue'
                  }`} />
                  <div className="flex-1">
                    <div className="text-sm text-text-primary">
                      <span className="font-semibold">{meeting.datetime}</span> — {meeting.type}
                    </div>
                    <div className="text-xs text-text-muted mt-1">
                      {meeting.contact} • {meeting.company}
                      {meeting.dealValue && (
                        <span className="text-status-success ml-1">• {meeting.dealValue} deal</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Warm Replies */}
          <GlassCard className="p-0 overflow-hidden">
            <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
              <div className="flex items-center gap-2.5 text-sm font-semibold text-text-primary">
                <div className="w-2 h-2 bg-status-success rounded-full" />
                Warm Replies
              </div>
              <Link href="/replies" className="text-sm text-accent-primary hover:underline">
                Open Inbox →
              </Link>
            </div>
            <div className="p-6">
              {mockWarmReplies.map((reply) => (
                <div key={reply.id} className="flex items-start gap-3 py-3.5 border-b border-border-subtle last:border-0">
                  <div className="w-2.5 h-2.5 rounded-full mt-1.5 bg-status-success" />
                  <div className="flex-1">
                    <div className="text-sm text-text-primary italic">{reply.quote}</div>
                    <div className="text-xs text-text-muted mt-1">
                      {reply.contact} • {reply.company} • {reply.time}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
        </div>{/* End content layer */}
      </div>
    </AppShell>
  );
}

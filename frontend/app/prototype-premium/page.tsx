/**
 * Premium Dashboard Prototype
 *
 * Dark glassmorphism theme with interactive components:
 * - NumberTicker for animated stats
 * - MagicCard for spotlight hover effects
 * - BorderBeam for glowing borders
 * - AnimatedList for live activity feed
 * - MovingBorder for premium CTAs
 */

"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Target,
  Users,
  MessageSquare,
  BarChart3,
  Settings,
  Calendar,
  TrendingUp,
  TrendingDown,
  Mail,
  Linkedin,
  Phone,
  MessageCircle,
  Zap,
  Bell,
  Search,
  MoreHorizontal,
  ArrowUpRight,
  Activity,
  CheckCircle,
  Play,
  Pause,
  Plus,
  Building,
  Sparkles,
  ChevronRight,
} from "lucide-react";

// Premium UI Components
import { NumberTicker } from "@/components/ui/number-ticker";
import { MagicCard } from "@/components/ui/magic-card";
import { BorderBeam } from "@/components/ui/border-beam";
import { Button as MovingBorderButton } from "@/components/ui/moving-border";
import { ShineBorder } from "@/components/ui/shine-border";

// ============ TYPES ============
type PageKey = "dashboard" | "campaigns" | "leads" | "replies" | "reports" | "settings";

// ============ GLASSMORPHISM CARD ============
function GlassCard({
  children,
  className = "",
  hover = true,
  glow = false,
  glowColor = "cyan"
}: {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  glow?: boolean;
  glowColor?: "cyan" | "purple" | "emerald" | "orange";
}) {
  const glowColors = {
    cyan: "shadow-cyan-500/20",
    purple: "shadow-purple-500/20",
    emerald: "shadow-emerald-500/20",
    orange: "shadow-orange-500/20",
  };

  return (
    <div
      className={`
        relative overflow-hidden rounded-2xl
        bg-white/[0.03] backdrop-blur-xl
        border border-white/[0.08]
        ${hover ? "transition-all duration-300 hover:bg-white/[0.05] hover:border-white/[0.12]" : ""}
        ${glow ? `shadow-2xl ${glowColors[glowColor]}` : ""}
        ${className}
      `}
    >
      {children}
    </div>
  );
}

// ============ SIDEBAR ============
function Sidebar({ activePage, onNavigate }: { activePage: PageKey; onNavigate: (page: PageKey) => void }) {
  const navItems: { key: PageKey; label: string; icon: typeof LayoutDashboard; badge?: number }[] = [
    { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { key: "campaigns", label: "Campaigns", icon: Target, badge: 3 },
    { key: "leads", label: "Leads", icon: Users, badge: 150 },
    { key: "replies", label: "Replies", icon: MessageSquare, badge: 8 },
    { key: "reports", label: "Reports", icon: BarChart3 },
    { key: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <div className="w-64 bg-[#0a0a0f]/80 backdrop-blur-xl flex flex-col h-screen fixed left-0 top-0 border-r border-white/[0.06]">
      {/* Logo */}
      <div className="p-5 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 rounded-full border-2 border-[#0a0a0f]" />
          </div>
          <div>
            <span className="text-lg font-semibold text-white">Agency OS</span>
            <p className="text-[10px] text-cyan-400/60 font-mono">PREMIUM</p>
          </div>
        </div>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <button
            key={item.key}
            onClick={() => onNavigate(item.key)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 group ${
              activePage === item.key
                ? "bg-gradient-to-r from-cyan-500/20 to-blue-500/10 text-cyan-400 border border-cyan-500/20"
                : "text-gray-400 hover:text-white hover:bg-white/[0.03]"
            }`}
          >
            <item.icon className={`w-5 h-5 ${activePage === item.key ? "text-cyan-400" : "text-gray-500 group-hover:text-gray-300"}`} />
            <span className="flex-1 text-left">{item.label}</span>
            {item.badge && (
              <span className={`px-2 py-0.5 rounded-full text-xs font-mono ${
                activePage === item.key
                  ? "bg-cyan-500/20 text-cyan-400"
                  : "bg-white/[0.05] text-gray-500"
              }`}>
                {item.badge}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* User */}
      <div className="p-4 border-t border-white/[0.06]">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-400 to-cyan-500 flex items-center justify-center text-white text-sm font-bold">
            A
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">Acme Agency</p>
            <p className="text-[10px] text-emerald-400/60 font-mono">VELOCITY PLAN</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ HEADER ============
function Header() {
  return (
    <div className="h-16 bg-[#0a0a0f]/60 backdrop-blur-xl border-b border-white/[0.06] flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-white">Dashboard</h1>
        <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 text-[10px] font-mono rounded-full border border-emerald-500/20">
          LIVE
        </span>
      </div>
      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Search..."
            className="w-64 pl-10 pr-4 py-2 text-sm bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500/50 transition-colors"
          />
        </div>
        <button className="relative p-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-gray-400 hover:text-white hover:bg-white/[0.05] transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full" />
        </button>
      </div>
    </div>
  );
}

// ============ PREMIUM STAT CARD ============
function PremiumStatCard({
  label,
  value,
  change,
  icon: Icon,
  color = "cyan",
  delay = 0
}: {
  label: string;
  value: number;
  change?: number;
  icon: typeof Calendar;
  color?: "cyan" | "emerald" | "purple" | "orange";
  delay?: number;
}) {
  const colors = {
    cyan: { bg: "from-cyan-500/20 to-cyan-500/5", text: "text-cyan-400", border: "border-cyan-500/20" },
    emerald: { bg: "from-emerald-500/20 to-emerald-500/5", text: "text-emerald-400", border: "border-emerald-500/20" },
    purple: { bg: "from-purple-500/20 to-purple-500/5", text: "text-purple-400", border: "border-purple-500/20" },
    orange: { bg: "from-orange-500/20 to-orange-500/5", text: "text-orange-400", border: "border-orange-500/20" },
  };

  const { bg, text, border } = colors[color];

  return (
    <MagicCard
      className="rounded-2xl"
      gradientColor="#1a1a2e"
      gradientFrom={color === "cyan" ? "#06b6d4" : color === "emerald" ? "#10b981" : color === "purple" ? "#a855f7" : "#f97316"}
      gradientTo={color === "cyan" ? "#3b82f6" : color === "emerald" ? "#06b6d4" : color === "purple" ? "#ec4899" : "#ef4444"}
    >
      <div className={`relative p-5 bg-gradient-to-br ${bg} rounded-2xl border ${border}`}>
        <div className="flex items-start justify-between mb-3">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">{label}</span>
          <div className={`w-10 h-10 rounded-xl bg-white/[0.05] ${text} flex items-center justify-center`}>
            <Icon className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-4xl font-light text-white">
            <NumberTicker value={value} delay={delay} />
          </span>
          {label.includes("Rate") && <span className="text-xl text-gray-500">%</span>}
        </div>
        {change !== undefined && (
          <div className="flex items-center gap-1.5 mt-2">
            {change >= 0 ? (
              <ArrowUpRight className="w-4 h-4 text-emerald-400" />
            ) : (
              <TrendingDown className="w-4 h-4 text-red-400" />
            )}
            <span className={`text-sm font-medium ${change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {change >= 0 ? "+" : ""}{change}%
            </span>
            <span className="text-xs text-gray-500">vs last month</span>
          </div>
        )}
      </div>
    </MagicCard>
  );
}

// ============ HERO PROGRESS CARD ============
function HeroProgressCard({ meetings, target }: { meetings: number; target: number }) {
  const progress = (meetings / target) * 100;
  const isOnTrack = progress >= 60;

  return (
    <div className="relative overflow-hidden rounded-2xl">
      {/* Aurora background */}
      <div className="absolute inset-0 bg-[#0a0a0f]">
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] opacity-40"
          style={{
            background: isOnTrack
              ? "radial-gradient(ellipse at center, rgba(16,185,129,0.4) 0%, rgba(6,182,212,0.2) 40%, transparent 70%)"
              : "radial-gradient(ellipse at center, rgba(245,158,11,0.4) 0%, rgba(249,115,22,0.2) 40%, transparent 70%)",
            filter: "blur(40px)",
          }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 p-6 backdrop-blur-xl bg-white/[0.02] border border-white/[0.08] rounded-2xl">
        <BorderBeam
          colorFrom={isOnTrack ? "#10b981" : "#f59e0b"}
          colorTo={isOnTrack ? "#06b6d4" : "#ef4444"}
          duration={8}
        />

        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${isOnTrack ? "bg-emerald-500/20" : "bg-amber-500/20"}`}>
              <Activity className={`w-6 h-6 ${isOnTrack ? "text-emerald-400" : "text-amber-400"}`} />
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-400">Monthly Progress</h3>
              <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
                isOnTrack ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"
              }`}>
                <Zap className="w-3 h-3" />
                {isOnTrack ? "On Track" : "Behind Pace"}
              </div>
            </div>
          </div>
          <Sparkles className={`w-5 h-5 ${isOnTrack ? "text-emerald-400" : "text-amber-400"} animate-pulse`} />
        </div>

        <div className="flex items-baseline gap-3 mb-4">
          <span className="text-5xl font-light text-white">
            <NumberTicker value={meetings} />
          </span>
          <span className="text-gray-500">of {target} meetings</span>
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-white/[0.05] rounded-full overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${isOnTrack ? "bg-gradient-to-r from-emerald-500 to-cyan-500" : "bg-gradient-to-r from-amber-500 to-orange-500"}`}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 1.5, ease: "easeOut", delay: 0.5 }}
          />
        </div>
      </div>
    </div>
  );
}

// ============ CHANNEL ICON ============
function ChannelIcon({ channel, size = "md" }: { channel: string; size?: "sm" | "md" }) {
  const sizeClass = size === "sm" ? "w-7 h-7" : "w-9 h-9";
  const iconSize = size === "sm" ? "w-3.5 h-3.5" : "w-4 h-4";

  const config: Record<string, { bg: string; icon: typeof Mail }> = {
    email: { bg: "bg-blue-500/20 text-blue-400", icon: Mail },
    linkedin: { bg: "bg-sky-500/20 text-sky-400", icon: Linkedin },
    sms: { bg: "bg-emerald-500/20 text-emerald-400", icon: MessageCircle },
    voice: { bg: "bg-purple-500/20 text-purple-400", icon: Phone },
  };

  const { bg, icon: Icon } = config[channel] || config.email;

  return (
    <div className={`${sizeClass} rounded-lg ${bg} flex items-center justify-center`}>
      <Icon className={iconSize} />
    </div>
  );
}

// ============ CAMPAIGN CARD ============
function CampaignCard({ campaign, index }: {
  campaign: {
    id: number;
    name: string;
    priority: number;
    meetings: number;
    replyRate: number;
    showRate: number;
    channels: string[];
    isAI: boolean;
  };
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <MagicCard className="rounded-xl" gradientColor="#1a1a2e" gradientOpacity={0.5}>
        <div className="p-4 bg-white/[0.02] rounded-xl border border-white/[0.06] hover:border-white/[0.1] transition-colors">
          <div className="flex items-center gap-4">
            {/* Status & Name */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-medium text-white truncate">{campaign.name}</span>
                {campaign.isAI && (
                  <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-400 text-[10px] font-mono rounded border border-purple-500/20">
                    AI
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1.5">
                {campaign.channels.map((ch) => (
                  <ChannelIcon key={ch} channel={ch} size="sm" />
                ))}
              </div>
            </div>

            {/* Priority */}
            <div className="w-32">
              <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                <span>Priority</span>
                <span className="text-cyan-400 font-mono">{campaign.priority}%</span>
              </div>
              <div className="h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${campaign.priority}%` }}
                  transition={{ duration: 0.8, delay: index * 0.1 }}
                />
              </div>
            </div>

            {/* Stats */}
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className="text-lg font-semibold text-white">{campaign.meetings}</div>
                <div className="text-[10px] text-gray-500 uppercase">Meetings</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-semibold text-cyan-400">{campaign.replyRate}%</div>
                <div className="text-[10px] text-gray-500 uppercase">Reply</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-semibold text-emerald-400">{campaign.showRate}%</div>
                <div className="text-[10px] text-gray-500 uppercase">Show</div>
              </div>
            </div>

            <button className="p-2 text-gray-500 hover:text-white hover:bg-white/[0.05] rounded-lg transition-colors">
              <MoreHorizontal className="w-5 h-5" />
            </button>
          </div>
        </div>
      </MagicCard>
    </motion.div>
  );
}

// ============ ACTIVITY ITEM ============
function ActivityItem({ item }: { item: { channel: string; lead: string; company: string; action: string; time: string; tier: string } }) {
  const tierColors: Record<string, string> = {
    hot: "bg-orange-500/20 text-orange-400 border-orange-500/20",
    warm: "bg-yellow-500/20 text-yellow-400 border-yellow-500/20",
    cool: "bg-blue-500/20 text-blue-400 border-blue-500/20",
  };

  return (
    <div className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors">
      <ChannelIcon channel={item.channel} size="sm" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-white text-sm">{item.lead}</span>
          <span className="text-gray-600">at</span>
          <span className="text-gray-400 text-sm truncate">{item.company}</span>
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${tierColors[item.tier]}`}>
            {item.tier === "hot" ? "High Priority" : item.tier === "warm" ? "Engaged" : "Nurturing"}
          </span>
        </div>
        <p className="text-xs text-gray-500 truncate">{item.action}</p>
      </div>
      <span className="text-xs text-gray-600 whitespace-nowrap font-mono">{item.time}</span>
    </div>
  );
}

// ============ MEETING ITEM ============
function MeetingItem({ meeting, index }: {
  meeting: { lead: string; company: string; time: string; day: string; type: string };
  index: number;
}) {
  const typeColors: Record<string, string> = {
    Discovery: "bg-blue-500/20 text-blue-400 border-blue-500/20",
    Demo: "bg-emerald-500/20 text-emerald-400 border-emerald-500/20",
    "Follow-up": "bg-amber-500/20 text-amber-400 border-amber-500/20",
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors"
    >
      <div className="text-center min-w-[50px]">
        <div className="text-[10px] text-gray-500 uppercase font-mono">{meeting.day}</div>
        <div className="text-sm font-semibold text-white">{meeting.time}</div>
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-white text-sm">{meeting.lead}</div>
        <div className="text-xs text-gray-500">{meeting.company}</div>
      </div>
      <span className={`px-2 py-0.5 rounded text-[10px] font-medium border ${typeColors[meeting.type]}`}>
        {meeting.type}
      </span>
    </motion.div>
  );
}

// ============ DASHBOARD PAGE ============
function DashboardPage() {
  const [showConfetti, setShowConfetti] = useState(false);

  const campaigns = [
    { id: 1, name: "Tech Decision Makers", priority: 40, meetings: 6, replyRate: 5.1, showRate: 83, channels: ["email", "linkedin"], isAI: true },
    { id: 2, name: "Series A Startups", priority: 35, meetings: 4, replyRate: 5.6, showRate: 75, channels: ["email", "linkedin", "voice"], isAI: true },
    { id: 3, name: "Enterprise Accounts", priority: 25, meetings: 2, replyRate: 4.4, showRate: 100, channels: ["email"], isAI: false },
  ];

  const activities = [
    { id: 1, channel: "email", lead: "Sarah Chen", company: "TechCorp", action: "Positive reply - wants demo", time: "2m", tier: "hot" },
    { id: 2, channel: "email", lead: "Mike Johnson", company: "StartupXYZ", action: "Opened 3x - Subject: Scaling your team", time: "8m", tier: "warm" },
    { id: 3, channel: "voice", lead: "Lisa Park", company: "Acme Inc", action: "Meeting booked - Tomorrow 2pm", time: "15m", tier: "hot" },
    { id: 4, channel: "linkedin", lead: "David Lee", company: "Growth Co", action: "Clicked pricing link", time: "22m", tier: "warm" },
    { id: 5, channel: "linkedin", lead: "Emma Wilson", company: "Scale Labs", action: "Accepted connection", time: "35m", tier: "cool" },
  ];

  const meetings = [
    { id: 1, lead: "Sarah Chen", company: "TechCorp", time: "2:00 PM", day: "Today", type: "Discovery" },
    { id: 2, lead: "Mike Johnson", company: "StartupXYZ", time: "10:00 AM", day: "Tomorrow", type: "Demo" },
    { id: 3, lead: "Lisa Park", company: "Acme Inc", time: "3:30 PM", day: "Thu", type: "Follow-up" },
  ];

  return (
    <div className="p-6 space-y-6 min-h-screen">
      {/* Hero Row */}
      <div className="grid grid-cols-12 gap-6">
        {/* Progress Card */}
        <div className="col-span-5">
          <HeroProgressCard meetings={12} target={18} />
        </div>

        {/* Stat Cards */}
        <div className="col-span-7 grid grid-cols-3 gap-4">
          <PremiumStatCard label="Meetings Booked" value={12} change={25} icon={Calendar} color="cyan" delay={0.2} />
          <PremiumStatCard label="Show Rate" value={83} change={5} icon={CheckCircle} color="emerald" delay={0.4} />
          <PremiumStatCard label="Reply Rate" value={5} change={12} icon={MessageSquare} color="purple" delay={0.6} />
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Column */}
        <div className="col-span-8 space-y-6">
          {/* Campaigns */}
          <GlassCard>
            <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="text-sm font-semibold text-white">Active Campaigns</h2>
                <span className="px-2 py-0.5 bg-white/[0.05] text-gray-400 text-xs font-mono rounded-full">
                  3 of 5 slots
                </span>
              </div>
              <button className="flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-medium transition-colors">
                <Plus className="w-3.5 h-3.5" /> Add Campaign
              </button>
            </div>
            <div className="p-4 space-y-3">
              {campaigns.map((campaign, i) => (
                <CampaignCard key={campaign.id} campaign={campaign} index={i} />
              ))}
            </div>
            <div className="px-5 py-4 border-t border-white/[0.06] flex items-center justify-between">
              <button className="px-4 py-2 bg-red-500/10 text-red-400 text-xs font-medium rounded-lg hover:bg-red-500/20 flex items-center gap-1.5 border border-red-500/20 transition-colors">
                <Pause className="w-3.5 h-3.5" />
                Emergency Pause
              </button>
              <MovingBorderButton
                containerClassName="h-10 w-44"
                borderClassName="bg-[radial-gradient(#10b981_40%,transparent_60%)]"
                className="text-xs font-medium"
              >
                <Play className="w-3.5 h-3.5 mr-2" />
                Confirm & Activate
              </MovingBorderButton>
            </div>
          </GlassCard>

          {/* Live Activity */}
          <GlassCard>
            <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="text-sm font-semibold text-white">Live Activity</h2>
                <span className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 text-emerald-400 text-xs font-mono rounded-full border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                  Live
                </span>
              </div>
              <button className="text-xs text-gray-500 hover:text-white transition-colors flex items-center gap-1">
                View All <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="p-4 space-y-2 max-h-80 overflow-y-auto">
              {activities.map((item) => (
                <ActivityItem key={item.id} item={item} />
              ))}
            </div>
          </GlassCard>
        </div>

        {/* Right Column */}
        <div className="col-span-4 space-y-6">
          {/* Upcoming Meetings */}
          <GlassCard glow glowColor="cyan">
            <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Upcoming Meetings</h2>
              <span className="px-2 py-0.5 bg-cyan-500/10 text-cyan-400 text-xs font-mono rounded-full border border-cyan-500/20">
                {meetings.length} scheduled
              </span>
            </div>
            <div className="p-4 space-y-2">
              {meetings.map((meeting, i) => (
                <MeetingItem key={meeting.id} meeting={meeting} index={i} />
              ))}
            </div>
          </GlassCard>

          {/* Priority Prospects */}
          <GlassCard glow glowColor="orange">
            <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Priority Prospects</h2>
              <span className="px-2 py-0.5 bg-orange-500/10 text-orange-400 text-xs font-mono rounded-full border border-orange-500/20">
                Action Needed
              </span>
            </div>
            <div className="divide-y divide-white/[0.04]">
              {[
                { name: "Sarah Chen", company: "TechCorp", tier: "hot", signals: ["Requested demo", "Opened 3x"] },
                { name: "Lisa Park", company: "Acme Inc", tier: "hot", signals: ["Meeting scheduled", "LinkedIn engaged"] },
                { name: "Tom Wilson", company: "DataFlow", tier: "warm", signals: ["Positive reply", "Website visit"] },
              ].map((lead) => (
                <div key={lead.name} className="px-5 py-3 hover:bg-white/[0.02] transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="font-medium text-white text-sm">{lead.name}</div>
                      <div className="text-xs text-gray-500">{lead.company}</div>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-medium border ${
                      lead.tier === "hot"
                        ? "bg-orange-500/20 text-orange-400 border-orange-500/20"
                        : "bg-yellow-500/20 text-yellow-400 border-yellow-500/20"
                    }`}>
                      {lead.tier === "hot" ? "High Priority" : "Engaged"}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {lead.signals.map((signal, i) => (
                      <span key={i} className="px-2 py-0.5 bg-white/[0.03] text-gray-400 text-[10px] rounded border border-white/[0.06]">
                        {signal}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Channel Distribution */}
          <GlassCard>
            <div className="px-5 py-4 border-b border-white/[0.06]">
              <h2 className="text-sm font-semibold text-white">Prospect Distribution</h2>
            </div>
            <div className="p-5 space-y-3">
              {[
                { label: "High Priority", count: 23, pct: 15, color: "bg-orange-500" },
                { label: "Engaged", count: 45, pct: 30, color: "bg-yellow-500" },
                { label: "Nurturing", count: 52, pct: 35, color: "bg-blue-500" },
                { label: "Low Activity", count: 22, pct: 15, color: "bg-gray-500" },
                { label: "Inactive", count: 8, pct: 5, color: "bg-gray-700" },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 w-24">{item.label}</span>
                  <div className="flex-1 h-2 bg-white/[0.05] rounded-full overflow-hidden">
                    <motion.div
                      className={`h-full ${item.color} rounded-full`}
                      initial={{ width: 0 }}
                      animate={{ width: `${item.pct}%` }}
                      transition={{ duration: 0.8, delay: 0.5 }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-8 text-right font-mono">{item.count}</span>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}

// ============ MAIN PAGE ============
export default function PremiumPrototypePage() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute top-0 left-1/4 w-[800px] h-[600px] opacity-30"
          style={{
            background: "radial-gradient(ellipse at center, rgba(6,182,212,0.15) 0%, transparent 60%)",
            filter: "blur(100px)",
          }}
        />
        <div
          className="absolute bottom-0 right-1/4 w-[600px] h-[500px] opacity-20"
          style={{
            background: "radial-gradient(ellipse at center, rgba(168,85,247,0.15) 0%, transparent 60%)",
            filter: "blur(100px)",
          }}
        />
      </div>

      {/* Sidebar */}
      <Sidebar activePage={activePage} onNavigate={setActivePage} />

      {/* Main Content */}
      <div className="ml-64">
        <Header />
        <DashboardPage />
      </div>
    </div>
  );
}

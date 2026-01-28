/**
 * Prototype Preview Page - Information Dense Dashboard
 * Complete rewrite with proper navigation and rich data display
 */

"use client";

import { useState, useEffect } from "react";
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
  Clock,
  Zap,
  Bell,
  Search,
  ChevronRight,
  ChevronDown,
  MoreHorizontal,
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  Eye,
  MousePointer,
  Send,
  CheckCircle,
  XCircle,
  AlertCircle,
  Star,
  Filter,
  Download,
  RefreshCw,
  Play,
  Pause,
  Plus,
  ExternalLink,
  Building,
  MapPin,
  DollarSign,
  Users2,
  Briefcase,
  Globe,
  Sparkles
} from "lucide-react";

// ============ TYPES ============
type PageKey = "dashboard" | "campaigns" | "leads" | "replies" | "reports" | "settings";

// ============ SIDEBAR ============
function Sidebar({ activePage, onNavigate }: { activePage: PageKey; onNavigate: (page: PageKey) => void }) {
  const [clickedItem, setClickedItem] = useState<PageKey | null>(null);

  const navItems: { key: PageKey; label: string; icon: typeof LayoutDashboard; badge?: string }[] = [
    { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { key: "campaigns", label: "Campaigns", icon: Target, badge: "3" },
    { key: "leads", label: "Leads", icon: Users, badge: "150" },
    { key: "replies", label: "Replies", icon: MessageSquare, badge: "8" },
    { key: "reports", label: "Reports", icon: BarChart3 },
    { key: "settings", label: "Settings", icon: Settings },
  ];

  const handleNavClick = (key: PageKey) => {
    if (key === activePage) return;
    setClickedItem(key);
    // Small delay for click animation before navigation
    setTimeout(() => {
      onNavigate(key);
      setClickedItem(null);
    }, 150);
  };

  return (
    <div className="w-60 bg-[#0F172A] flex flex-col h-screen fixed left-0 top-0">
      {/* Logo */}
      <div className="p-4 border-b border-[#1E293B]">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center animate-pulse">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-bold text-white">Agency OS</span>
        </div>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <button
            key={item.key}
            onClick={() => handleNavClick(item.key)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 transform ${
              activePage === item.key
                ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30 scale-100"
                : clickedItem === item.key
                ? "bg-blue-500 text-white scale-95"
                : "text-slate-400 hover:text-white hover:bg-slate-800 hover:scale-[1.02] active:scale-95"
            }`}
          >
            <item.icon className={`w-5 h-5 transition-transform duration-200 ${clickedItem === item.key ? "rotate-12" : ""}`} />
            <span className="flex-1 text-left">{item.label}</span>
            {item.badge && (
              <span className={`px-2 py-0.5 rounded-full text-xs transition-all duration-200 ${
                activePage === item.key ? "bg-blue-500 text-white" : "bg-slate-700 text-slate-300"
              } ${clickedItem === item.key ? "scale-110" : ""}`}>
                {item.badge}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* User */}
      <div className="p-3 border-t border-[#1E293B]">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center text-white text-sm font-medium">
            A
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">Acme Agency</p>
            <p className="text-xs text-slate-500">Velocity Plan</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ HEADER ============
function Header({ title }: { title: string }) {
  return (
    <div className="h-14 bg-white border-b border-slate-200 shadow-md shadow-black/5 flex items-center justify-between px-6">
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search..."
            className="w-64 pl-9 pr-4 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button className="relative p-2 text-slate-400 hover:text-slate-600">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>
      </div>
    </div>
  );
}

// ============ MINI COMPONENTS ============
function StatCard({ label, value, change, changeLabel, icon: Icon, color = "blue" }: {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon: typeof Calendar;
  color?: "blue" | "green" | "orange" | "purple" | "red";
}) {
  const colors = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-emerald-50 text-emerald-600",
    orange: "bg-orange-50 text-orange-600",
    purple: "bg-purple-50 text-purple-600",
    red: "bg-red-50 text-red-600",
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-md shadow-black/10 p-4">
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</span>
        <div className={`w-8 h-8 rounded-lg ${colors[color]} flex items-center justify-center`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      {change !== undefined && (
        <div className="flex items-center gap-1 mt-1">
          {change >= 0 ? (
            <ArrowUpRight className="w-3 h-3 text-emerald-500" />
          ) : (
            <ArrowDownRight className="w-3 h-3 text-red-500" />
          )}
          <span className={`text-xs font-medium ${change >= 0 ? "text-emerald-600" : "text-red-600"}`}>
            {change >= 0 ? "+" : ""}{change}%
          </span>
          {changeLabel && <span className="text-xs text-slate-400">{changeLabel}</span>}
        </div>
      )}
    </div>
  );
}

function MiniChart({ data, color = "#3B82F6" }: { data: number[]; color?: string }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * 100;
    const y = 100 - ((v - min) / range) * 80 - 10;
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg viewBox="0 0 100 50" className="w-full h-12">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ChannelIcon({ channel, size = "sm" }: { channel: string; size?: "sm" | "md" }) {
  const sizeClass = size === "sm" ? "w-6 h-6" : "w-8 h-8";
  const iconSize = size === "sm" ? "w-3 h-3" : "w-4 h-4";

  const config: Record<string, { bg: string; icon: typeof Mail }> = {
    email: { bg: "bg-blue-100 text-blue-600", icon: Mail },
    linkedin: { bg: "bg-sky-100 text-sky-600", icon: Linkedin },
    sms: { bg: "bg-emerald-100 text-emerald-600", icon: MessageCircle },
    voice: { bg: "bg-purple-100 text-purple-600", icon: Phone },
  };

  const { bg, icon: Icon } = config[channel] || config.email;

  return (
    <div className={`${sizeClass} rounded-full ${bg} flex items-center justify-center`}>
      <Icon className={iconSize} />
    </div>
  );
}

// Per LEADS.md spec: Clients see friendly labels, NOT internal tier names
// Hot → "High Priority", Warm → "Engaged", Cool → "Nurturing", Cold → "Low Activity", Dead → "Inactive"
function TierBadge({ tier, showInternalLabel = false }: { tier: string; showInternalLabel?: boolean }) {
  const config: Record<string, { style: string; clientLabel: string }> = {
    hot: { style: "bg-orange-100 text-orange-700", clientLabel: "High Priority" },
    warm: { style: "bg-yellow-100 text-yellow-700", clientLabel: "Engaged" },
    cool: { style: "bg-blue-100 text-blue-700", clientLabel: "Nurturing" },
    cold: { style: "bg-slate-100 text-slate-600", clientLabel: "Low Activity" },
    dead: { style: "bg-slate-100 text-slate-500", clientLabel: "Inactive" },
  };

  const tierConfig = config[tier] || config.cool;
  const label = showInternalLabel
    ? tier.charAt(0).toUpperCase() + tier.slice(1)
    : tierConfig.clientLabel;

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${tierConfig.style}`}>
      {label}
    </span>
  );
}

// ============ DASHBOARD PAGE ============
function DashboardPage({ onConfirmActivate, onNewCampaign }: { onConfirmActivate: () => void; onNewCampaign: () => void }) {
  const [hasChanges, setHasChanges] = useState(false);
  const campaigns = [
    { id: 1, name: "Tech Decision Makers", priority: 40, meetings: 6, replies: 23, sent: 450, replyRate: 5.1, showRate: 83, status: "active", isAI: true, channels: ["email", "linkedin"] },
    { id: 2, name: "Series A Startups", priority: 35, meetings: 4, replies: 18, sent: 320, replyRate: 5.6, showRate: 75, status: "active", isAI: true, channels: ["email", "linkedin", "voice"] },
    { id: 3, name: "Enterprise Accounts", priority: 25, meetings: 2, replies: 8, sent: 180, replyRate: 4.4, showRate: 100, status: "active", isAI: false, channels: ["email"] },
  ];

  const recentActivity = [
    { id: 1, type: "reply", channel: "email", lead: "Sarah Chen", company: "TechCorp", action: "Positive reply - wants demo", time: "2m", tier: "hot" },
    { id: 2, type: "open", channel: "email", lead: "Mike Johnson", company: "StartupXYZ", action: "Opened 3x - Subject: Scaling your team", time: "8m", tier: "warm" },
    { id: 3, type: "meeting", channel: "voice", lead: "Lisa Park", company: "Acme Inc", action: "Meeting booked - Tomorrow 2pm", time: "15m", tier: "hot" },
    { id: 4, type: "click", channel: "email", lead: "David Lee", company: "Growth Co", action: "Clicked pricing link", time: "22m", tier: "warm" },
    { id: 5, type: "connect", channel: "linkedin", lead: "Emma Wilson", company: "Scale Labs", action: "Accepted connection", time: "35m", tier: "cool" },
    { id: 6, type: "reply", channel: "linkedin", lead: "James Brown", company: "Innovate Inc", action: "Question about integration", time: "1h", tier: "warm" },
  ];

  const meetings = [
    { id: 1, lead: "Sarah Chen", company: "TechCorp", time: "2:00 PM", day: "Today", type: "Discovery", duration: 30 },
    { id: 2, lead: "Mike Johnson", company: "StartupXYZ", time: "10:00 AM", day: "Tomorrow", type: "Demo", duration: 45 },
    { id: 3, lead: "Lisa Park", company: "Acme Inc", time: "3:30 PM", day: "Thu", type: "Follow-up", duration: 30 },
  ];

  const channelStats = [
    { channel: "email", sent: 892, delivered: 876, opened: 412, replied: 42, meetings: 8 },
    { channel: "linkedin", sent: 245, delivered: 245, opened: 189, replied: 28, meetings: 3 },
    { channel: "sms", sent: 56, delivered: 54, opened: 54, replied: 12, meetings: 1 },
    { channel: "voice", sent: 34, delivered: 28, opened: 28, replied: 8, meetings: 2 },
  ];

  return (
    <div className="p-6 space-y-6 min-h-screen">
      {/* Top Stats Row - Per DASHBOARD.md: T1 Hero metrics only */}
      {/* Approved: Meetings booked, Show rate, Status (ahead/on_track/behind) */}
      {/* Banned: Credits remaining, Lead count (including "Hot Leads") */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Meetings Booked" value={12} change={25} changeLabel="vs last month" icon={Calendar} color="blue" />
        <StatCard label="Show Rate" value="83%" change={5} changeLabel="vs last month" icon={CheckCircle} color="green" />
        <StatCard label="Deals Created" value={3} change={50} changeLabel="vs last month" icon={Briefcase} color="green" />
        {/* Status indicator per spec */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-md shadow-black/10 p-4">
          <div className="flex items-start justify-between mb-2">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">Campaign Status</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-emerald-600">On Track</span>
          </div>
          <div className="text-xs text-slate-500 mt-1">3 active campaigns performing well</div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Column - Campaigns & Activity */}
        <div className="col-span-8 space-y-6">
          {/* Campaigns */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-900">Active Campaigns</h2>
                <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded-full">3 of 5 slots</span>
              </div>
              <button onClick={onNewCampaign} className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1">
                <Plus className="w-3 h-3" /> Add Campaign
              </button>
            </div>
            <div className="divide-y divide-slate-100">
              {campaigns.map((campaign) => (
                <div key={campaign.id} className="px-4 py-3 hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-4">
                    {/* Name & Status */}
                    <div className="w-48">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${campaign.status === "active" ? "bg-emerald-500" : "bg-slate-300"}`} />
                        <span className="font-medium text-slate-900 text-sm">{campaign.name}</span>
                        {campaign.isAI && (
                          <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 text-[10px] font-medium rounded">AI</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        {campaign.channels.map((ch) => (
                          <ChannelIcon key={ch} channel={ch} size="sm" />
                        ))}
                      </div>
                    </div>

                    {/* Priority Slider */}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500 w-12">Priority</span>
                        <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: `${campaign.priority}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium text-slate-700 w-10 text-right">{campaign.priority}%</span>
                      </div>
                    </div>

                    {/* Stats */}
                    <div className="flex items-center gap-6 text-sm">
                      <div className="text-center">
                        <div className="font-semibold text-slate-900">{campaign.meetings}</div>
                        <div className="text-[10px] text-slate-500">Meetings</div>
                      </div>
                      <div className="text-center">
                        <div className="font-semibold text-slate-900">{campaign.replyRate}%</div>
                        <div className="text-[10px] text-slate-500">Reply Rate</div>
                      </div>
                      <div className="text-center">
                        <div className="font-semibold text-slate-900">{campaign.showRate}%</div>
                        <div className="text-[10px] text-slate-500">Show Rate</div>
                      </div>
                      <div className="text-center">
                        <div className="font-semibold text-slate-900">{campaign.sent}</div>
                        <div className="text-[10px] text-slate-500">Sent</div>
                      </div>
                    </div>

                    <button className="p-1 text-slate-400 hover:text-slate-600">
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="px-4 py-3 border-t border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-xs text-slate-500">Total allocation: <span className="font-medium text-slate-900">100%</span></span>
                {/* Emergency Pause Button - Per SETTINGS.md spec: Critical safety feature */}
                <button className="px-3 py-1.5 bg-red-100 text-red-700 text-xs font-medium rounded-lg hover:bg-red-200 flex items-center gap-1.5 border border-red-200">
                  <Pause className="w-3 h-3" />
                  Emergency Pause All
                </button>
              </div>
              <button
                onClick={onConfirmActivate}
                className="px-4 py-1.5 bg-emerald-600 text-white text-xs font-medium rounded-lg hover:bg-emerald-700 flex items-center gap-1.5"
              >
                <Play className="w-3 h-3" />
                Confirm & Activate
              </button>
            </div>
          </div>

          {/* Live Activity */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-900">Live Activity</h2>
                <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs rounded-full">
                  <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                  Live
                </span>
              </div>
              <button className="text-xs text-slate-500 hover:text-slate-700">View All</button>
            </div>
            <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
              {recentActivity.map((item) => (
                <div key={item.id} className="px-4 py-2.5 hover:bg-slate-50 flex items-center gap-3">
                  <ChannelIcon channel={item.channel} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-900 text-sm">{item.lead}</span>
                      <span className="text-slate-400">at</span>
                      <span className="text-slate-600 text-sm">{item.company}</span>
                      <TierBadge tier={item.tier} />
                    </div>
                    <p className="text-xs text-slate-500 truncate">{item.action}</p>
                  </div>
                  <span className="text-xs text-slate-400 whitespace-nowrap">{item.time}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Channel Performance */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10">
            <div className="px-4 py-3 border-b border-slate-100">
              <h2 className="text-sm font-semibold text-slate-900">Channel Performance</h2>
            </div>
            <div className="p-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-slate-500 border-b border-slate-100">
                    <th className="text-left py-2 font-medium">Channel</th>
                    <th className="text-right py-2 font-medium">Sent</th>
                    <th className="text-right py-2 font-medium">Delivered</th>
                    <th className="text-right py-2 font-medium">Opened</th>
                    <th className="text-right py-2 font-medium">Open Rate</th>
                    <th className="text-right py-2 font-medium">Replied</th>
                    <th className="text-right py-2 font-medium">Reply Rate</th>
                    <th className="text-right py-2 font-medium">Meetings</th>
                  </tr>
                </thead>
                <tbody>
                  {channelStats.map((ch) => (
                    <tr key={ch.channel} className="border-b border-slate-50 last:border-0">
                      <td className="py-2.5">
                        <div className="flex items-center gap-2">
                          <ChannelIcon channel={ch.channel} />
                          <span className="font-medium text-slate-900 capitalize">{ch.channel}</span>
                        </div>
                      </td>
                      <td className="text-right text-slate-600">{ch.sent}</td>
                      <td className="text-right text-slate-600">{ch.delivered}</td>
                      <td className="text-right text-slate-600">{ch.opened}</td>
                      <td className="text-right">
                        <span className="text-emerald-600 font-medium">{((ch.opened / ch.delivered) * 100).toFixed(0)}%</span>
                      </td>
                      <td className="text-right text-slate-600">{ch.replied}</td>
                      <td className="text-right">
                        <span className="text-blue-600 font-medium">{((ch.replied / ch.sent) * 100).toFixed(1)}%</span>
                      </td>
                      <td className="text-right font-semibold text-slate-900">{ch.meetings}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column - Meetings, Hot Leads, ALS */}
        <div className="col-span-4 space-y-6">
          {/* On Track */}
          <div className="bg-gradient-to-r from-emerald-500 to-emerald-600 rounded-xl p-4 text-white">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-emerald-100">Monthly Progress</span>
              <span className="px-2 py-0.5 bg-white/20 text-white text-xs rounded-full">On Track</span>
            </div>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold">12</span>
              <span className="text-emerald-100 mb-1">of 15-20 meetings</span>
            </div>
            <div className="mt-3 h-2 bg-emerald-400/30 rounded-full overflow-hidden">
              <div className="h-full bg-white rounded-full" style={{ width: "70%" }} />
            </div>
          </div>

          {/* Upcoming Meetings */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900">Upcoming Meetings</h2>
              <span className="text-xs text-slate-500">{meetings.length} scheduled</span>
            </div>
            <div className="divide-y divide-slate-100">
              {meetings.map((meeting) => (
                <div key={meeting.id} className="px-4 py-3 hover:bg-slate-50">
                  <div className="flex items-start gap-3">
                    <div className="text-center min-w-[50px]">
                      <div className="text-[10px] text-slate-500 uppercase">{meeting.day}</div>
                      <div className="text-sm font-semibold text-slate-900">{meeting.time}</div>
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-slate-900 text-sm">{meeting.lead}</div>
                      <div className="text-xs text-slate-500">{meeting.company}</div>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                        meeting.type === "Discovery" ? "bg-blue-100 text-blue-700" :
                        meeting.type === "Demo" ? "bg-emerald-100 text-emerald-700" :
                        "bg-amber-100 text-amber-700"
                      }`}>
                        {meeting.type}
                      </span>
                      <div className="text-[10px] text-slate-400 mt-1">{meeting.duration}m</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Priority Prospects - Per LEADS.md: NO raw ALS scores for clients, show tier badge + signals */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-900">Priority Prospects</h2>
                <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs rounded-full">Needs Attention</span>
              </div>
            </div>
            <div className="divide-y divide-slate-100">
              {[
                { id: 1, name: "Sarah Chen", company: "TechCorp", tier: "hot", signals: ["Requested demo", "Opened 3x today", "Clicked pricing"] },
                { id: 2, name: "Lisa Park", company: "Acme Inc", tier: "hot", signals: ["Meeting scheduled", "LinkedIn engaged", "Referral source"] },
                { id: 3, name: "Tom Wilson", company: "DataFlow", tier: "warm", signals: ["Positive reply", "Website visit", "Content download"] },
              ].map((lead) => (
                <div key={lead.id} className="px-4 py-3 hover:bg-slate-50">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="font-medium text-slate-900 text-sm">{lead.name}</div>
                      <div className="text-xs text-slate-500">{lead.company}</div>
                    </div>
                    {/* Show tier badge, NOT numeric score */}
                    <TierBadge tier={lead.tier} />
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {lead.signals.map((signal, i) => (
                      <span key={i} className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] rounded">
                        {signal}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Prospect Distribution - Per LEADS.md: Use client-friendly tier labels */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-4">
            <h2 className="text-sm font-semibold text-slate-900 mb-3">Prospect Distribution</h2>
            <div className="space-y-2">
              {[
                { label: "High Priority", count: 23, pct: 15, color: "bg-orange-500" },
                { label: "Engaged", count: 45, pct: 30, color: "bg-yellow-500" },
                { label: "Nurturing", count: 52, pct: 35, color: "bg-blue-500" },
                { label: "Low Activity", count: 22, pct: 15, color: "bg-slate-400" },
                { label: "Inactive", count: 8, pct: 5, color: "bg-slate-300" },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-2">
                  <span className="text-xs text-slate-600 w-20">{item.label}</span>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.pct}%` }} />
                  </div>
                  <span className="text-xs text-slate-500 w-8 text-right">{item.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ NEW CAMPAIGN MODAL ============
function NewCampaignModal({ isOpen, onClose, onSubmit }: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; description: string; permissionMode: string }) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [permissionMode, setPermissionMode] = useState("autopilot");

  if (!isOpen) return null;

  const handleSubmit = () => {
    if (!name.trim()) return;
    onSubmit({ name, description, permissionMode });
    setName("");
    setDescription("");
    setPermissionMode("autopilot");
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">New Campaign</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <XCircle className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Campaign Name */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Campaign Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Tech Decision Makers Q1"
              className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Description <span className="text-slate-400">(optional)</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of your target audience..."
              rows={3}
              className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
          </div>

          {/* Permission Mode */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              Permission Mode
            </label>
            <div className="space-y-2">
              {[
                { id: "autopilot", label: "Autopilot", desc: "AI handles everything automatically", icon: Sparkles },
                { id: "co_pilot", label: "Co-Pilot", desc: "Review before sending", icon: Eye },
                { id: "manual", label: "Manual", desc: "Full control over every action", icon: MousePointer },
              ].map((mode) => (
                <button
                  key={mode.id}
                  onClick={() => setPermissionMode(mode.id)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg border-2 transition-all ${
                    permissionMode === mode.id
                      ? "border-blue-500 bg-blue-50"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    permissionMode === mode.id ? "bg-blue-500 text-white" : "bg-slate-100 text-slate-500"
                  }`}>
                    <mode.icon className="w-5 h-5" />
                  </div>
                  <div className="text-left">
                    <div className="font-medium text-slate-900">{mode.label}</div>
                    <div className="text-xs text-slate-500">{mode.desc}</div>
                  </div>
                  {permissionMode === mode.id && (
                    <CheckCircle className="w-5 h-5 text-blue-500 ml-auto" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="px-6 py-4 border-t border-slate-200 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-600 text-sm font-medium hover:text-slate-800"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!name.trim()}
            className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Create Campaign
          </button>
        </div>
      </div>
    </div>
  );
}

// ============ PROCESSING OVERLAY ============
function ProcessingOverlay({ isVisible, stage }: { isVisible: boolean; stage: number }) {
  if (!isVisible) return null;

  const stages = [
    { label: "Preparing your campaigns...", icon: RefreshCw },
    { label: "Finding ideal prospects...", icon: Search },
    { label: "Researching & qualifying leads...", icon: Users },
    { label: "Setting up outreach sequences...", icon: Send },
    { label: "Activating campaigns...", icon: Play },
  ];

  return (
    <div className="fixed inset-0 bg-white/95 flex items-center justify-center z-50">
      <div className="text-center max-w-md mx-4">
        <div className="w-16 h-16 mx-auto mb-6 relative">
          <div className="absolute inset-0 border-4 border-blue-100 rounded-full" />
          <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin" />
        </div>
        <h2 className="text-xl font-semibold text-slate-900 mb-2">
          {stages[stage]?.label || "Processing..."}
        </h2>
        <p className="text-sm text-slate-500 mb-8">
          This usually takes a few moments. Your campaigns will be ready shortly.
        </p>

        {/* Progress Steps */}
        <div className="space-y-3">
          {stages.map((s, i) => (
            <div
              key={i}
              className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-all ${
                i < stage ? "bg-emerald-50" : i === stage ? "bg-blue-50" : "bg-slate-50"
              }`}
            >
              <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                i < stage ? "bg-emerald-500 text-white" :
                i === stage ? "bg-blue-500 text-white" :
                "bg-slate-200 text-slate-400"
              }`}>
                {i < stage ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  <s.icon className={`w-3 h-3 ${i === stage ? "animate-pulse" : ""}`} />
                )}
              </div>
              <span className={`text-sm ${
                i < stage ? "text-emerald-700" :
                i === stage ? "text-blue-700 font-medium" :
                "text-slate-400"
              }`}>
                {s.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============ CAMPAIGNS PAGE ============
function CampaignsPage({ onNewCampaign }: { onNewCampaign: () => void }) {
  // Per CAMPAIGNS.md: NO lead counts visible to clients
  // Show: Name, status, permission mode, meetings, reply rate, show rate, channels
  const campaigns = [
    {
      id: 1,
      name: "Tech Decision Makers",
      status: "active",
      permissionMode: "autopilot",
      createdAt: "Jan 15",
      meetings: 6,
      replyRate: 5.1,
      showRate: 83,
      channels: ["email", "linkedin"],
    },
    {
      id: 2,
      name: "Series A Startups",
      status: "active",
      permissionMode: "co_pilot",
      createdAt: "Jan 10",
      meetings: 4,
      replyRate: 5.6,
      showRate: 75,
      channels: ["email", "linkedin", "voice"],
    },
    {
      id: 3,
      name: "Enterprise Accounts",
      status: "active",
      permissionMode: "manual",
      createdAt: "Jan 5",
      meetings: 2,
      replyRate: 4.4,
      showRate: 100,
      channels: ["email"],
    },
  ];

  return (
    <div className="p-6 min-h-screen">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Campaigns</h2>
          <p className="text-sm text-slate-500">3 active campaigns • 2 slots available</p>
        </div>
        <button
          onClick={onNewCampaign}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> New Campaign
        </button>
      </div>

      {/* AI Campaign Suggestions - Per CAMPAIGNS.md spec: CampaignSuggesterEngine generates during onboarding */}
      <div className="mb-6 bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl border border-purple-200">
        <div className="px-4 py-3 border-b border-purple-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-600" />
            <h3 className="text-sm font-semibold text-slate-900">AI Campaign Suggestions</h3>
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">Based on your ICP</span>
          </div>
          <button className="text-xs text-purple-600 hover:text-purple-700 font-medium">Regenerate</button>
        </div>
        <div className="p-4 space-y-3">
          {[
            {
              name: "C-Suite Tech Leaders",
              description: "CTOs and CIOs at mid-market SaaS companies",
              targets: ["SaaS", "Technology", "CTO", "CIO", "51-200 emp"],
              allocation: 40,
              reasoning: "Highest decision-making authority with budget control.",
            },
            {
              name: "Series A Founders",
              description: "CEOs and Founders at recently funded startups",
              targets: ["FinTech", "SaaS", "CEO", "Founder", "11-50 emp"],
              allocation: 35,
              reasoning: "Post-funding companies actively seeking growth solutions.",
            },
          ].map((suggestion, idx) => (
            <div key={idx} className="bg-white rounded-lg border border-slate-200 shadow-md shadow-black/10 p-3 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-purple-100 text-purple-700 text-xs font-medium flex items-center justify-center">
                      {idx + 1}
                    </span>
                    <span className="font-medium text-slate-900 text-sm">{suggestion.name}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 ml-7">{suggestion.description}</p>
                </div>
                <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs font-medium rounded">
                  {suggestion.allocation}%
                </span>
              </div>
              <div className="flex flex-wrap gap-1 ml-7 mb-2">
                {suggestion.targets.map((t) => (
                  <span key={t} className="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-[10px] rounded">{t}</span>
                ))}
              </div>
              <div className="ml-7 flex items-center gap-2">
                <button
                  onClick={onNewCampaign}
                  className="px-3 py-1 bg-purple-600 text-white text-xs font-medium rounded hover:bg-purple-700 flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" /> Create
                </button>
                <button className="px-3 py-1 text-slate-500 text-xs hover:text-slate-700">Dismiss</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Your Campaigns */}
      <h3 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Your Campaigns</h3>

      {/* Campaign Cards */}
      <div className="grid gap-4">
        {campaigns.map((campaign) => (
          <div key={campaign.id} className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-5">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${campaign.status === "active" ? "bg-emerald-500" : "bg-slate-300"}`} />
                <div>
                  <h3 className="font-semibold text-slate-900">{campaign.name}</h3>
                  <p className="text-xs text-slate-500">Created {campaign.createdAt}</p>
                </div>
              </div>
              <span className={`px-2.5 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 ${
                campaign.permissionMode === "autopilot" ? "bg-purple-100 text-purple-700" :
                campaign.permissionMode === "co_pilot" ? "bg-blue-100 text-blue-700" :
                "bg-slate-100 text-slate-700"
              }`}>
                {campaign.permissionMode === "autopilot" && <Sparkles className="w-3 h-3" />}
                {campaign.permissionMode === "co_pilot" && <Eye className="w-3 h-3" />}
                {campaign.permissionMode === "manual" && <MousePointer className="w-3 h-3" />}
                {campaign.permissionMode.replace("_", " ")}
              </span>
            </div>

            <div className="flex items-center gap-6">
              {/* Channels */}
              <div className="flex items-center gap-1">
                {campaign.channels.map((ch) => (
                  <ChannelIcon key={ch} channel={ch} />
                ))}
              </div>

              {/* Stats - Per CAMPAIGNS.md: Show Meetings, Reply Rate, Show Rate. NO lead count */}
              <div className="flex items-center gap-6 text-sm">
                <div>
                  <span className="text-slate-500">Meetings:</span>
                  <span className="ml-1.5 font-semibold text-slate-900">{campaign.meetings}</span>
                </div>
                <div>
                  <span className="text-slate-500">Reply Rate:</span>
                  <span className="ml-1.5 font-semibold text-slate-900">{campaign.replyRate}%</span>
                </div>
                <div>
                  <span className="text-slate-500">Show Rate:</span>
                  <span className={`ml-1.5 font-semibold ${campaign.showRate >= 80 ? "text-emerald-600" : "text-amber-600"}`}>
                    {campaign.showRate}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Empty Slots */}
      <div className="mt-4 grid gap-4">
        {[1, 2].map((slot) => (
          <button
            key={slot}
            onClick={onNewCampaign}
            className="border-2 border-dashed border-slate-200 rounded-xl p-6 text-center hover:border-blue-300 hover:bg-blue-50/50 transition-colors group"
          >
            <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-slate-100 group-hover:bg-blue-100 flex items-center justify-center">
              <Plus className="w-5 h-5 text-slate-400 group-hover:text-blue-500" />
            </div>
            <p className="text-sm text-slate-500 group-hover:text-blue-600">Add new campaign</p>
          </button>
        ))}
      </div>
    </div>
  );
}

// ============ LEADS PAGE ============
// Per LEADS.md spec: Show tier badge, NOT raw ALS score to clients
// Columns: Lead (name/email), Company (name/industry), Tier, Status
function LeadsPage() {
  const [selectedTier, setSelectedTier] = useState<string | null>(null);

  const leads = [
    { id: 1, name: "Sarah Chen", email: "sarah@techcorp.com", company: "TechCorp", industry: "Technology", title: "VP Engineering", tier: "hot", status: "in_sequence", lastActivity: "2m ago" },
    { id: 2, name: "Mike Johnson", email: "mike@startupxyz.com", company: "StartupXYZ", industry: "SaaS", title: "CEO", tier: "warm", status: "replied", lastActivity: "15m ago" },
    { id: 3, name: "Lisa Park", email: "lisa@acme.com", company: "Acme Inc", industry: "Fintech", title: "CTO", tier: "hot", status: "converted", lastActivity: "1h ago" },
    { id: 4, name: "David Lee", email: "david@growth.co", company: "Growth Co", industry: "Marketing", title: "Founder", tier: "warm", status: "in_sequence", lastActivity: "2h ago" },
    { id: 5, name: "Emma Wilson", email: "emma@scale.io", company: "Scale Labs", industry: "Technology", title: "Head of Ops", tier: "cool", status: "enriched", lastActivity: "3h ago" },
    { id: 6, name: "James Brown", email: "james@innovate.co", company: "Innovate Inc", industry: "SaaS", title: "CRO", tier: "cold", status: "new", lastActivity: "1d ago" },
  ];

  // Tier filter cards per spec - clickable to filter
  const tierCounts = [
    { tier: "hot", label: "High Priority", count: 23, color: "border-orange-500 bg-orange-50", textColor: "text-orange-700" },
    { tier: "warm", label: "Engaged", count: 45, color: "border-yellow-500 bg-yellow-50", textColor: "text-yellow-700" },
    { tier: "cool", label: "Nurturing", count: 52, color: "border-blue-500 bg-blue-50", textColor: "text-blue-700" },
    { tier: "cold", label: "Low Activity", count: 22, color: "border-slate-400 bg-slate-50", textColor: "text-slate-600" },
    { tier: "dead", label: "Inactive", count: 8, color: "border-slate-300 bg-slate-100", textColor: "text-slate-500" },
  ];

  // Client-friendly status labels per spec
  const statusLabels: Record<string, { label: string; style: string }> = {
    new: { label: "New", style: "bg-slate-100 text-slate-600" },
    enriched: { label: "Enriched", style: "bg-blue-100 text-blue-700" },
    scored: { label: "Scored", style: "bg-blue-100 text-blue-700" },
    in_sequence: { label: "In Sequence", style: "bg-purple-100 text-purple-700" },
    converted: { label: "Meeting Booked", style: "bg-emerald-100 text-emerald-700" },
    replied: { label: "Replied", style: "bg-sky-100 text-sky-700" },
    unsubscribed: { label: "Unsubscribed", style: "bg-slate-100 text-slate-500" },
    bounced: { label: "Bounced", style: "bg-red-100 text-red-600" },
  };

  const filteredLeads = selectedTier
    ? leads.filter(l => l.tier === selectedTier)
    : leads;

  return (
    <div className="p-6 min-h-screen">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Leads</h2>
          <p className="text-sm text-slate-500">{filteredLeads.length} prospects in pipeline</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search name, email, company..."
              className="w-64 pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Tier Filter Cards - Per spec: 5 clickable cards with counts */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        {tierCounts.map((item) => (
          <button
            key={item.tier}
            onClick={() => setSelectedTier(selectedTier === item.tier ? null : item.tier)}
            className={`p-4 rounded-lg border-2 text-left transition-all ${item.color} ${
              selectedTier === item.tier ? "ring-2 ring-blue-500 ring-offset-2" : "hover:shadow-md"
            }`}
          >
            <div className={`text-2xl font-bold ${item.textColor}`}>{item.count}</div>
            <div className="text-sm text-slate-600">{item.label}</div>
          </button>
        ))}
      </div>

      {/* Lead Table - Per spec: NO raw ALS score column for clients */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-xs text-slate-500">
              <th className="text-left p-4 font-medium">Lead</th>
              <th className="text-left p-4 font-medium">Company</th>
              <th className="text-left p-4 font-medium">Priority</th>
              <th className="text-left p-4 font-medium">Status</th>
              <th className="text-left p-4 font-medium">Last Activity</th>
              <th className="text-right p-4 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {filteredLeads.map((lead) => (
              <tr key={lead.id} className="border-b border-slate-50 hover:bg-slate-50">
                <td className="p-4">
                  <div className="font-medium text-slate-900">{lead.name}</div>
                  <div className="text-xs text-slate-500">{lead.email}</div>
                </td>
                <td className="p-4">
                  <div className="text-slate-900">{lead.company}</div>
                  <div className="text-xs text-slate-500">{lead.industry}</div>
                </td>
                <td className="p-4">
                  {/* Per spec: Show tier label, NOT raw score */}
                  <TierBadge tier={lead.tier} />
                </td>
                <td className="p-4">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${statusLabels[lead.status]?.style || "bg-slate-100 text-slate-600"}`}>
                    {statusLabels[lead.status]?.label || lead.status}
                  </span>
                </td>
                <td className="p-4 text-slate-500 text-xs">{lead.lastActivity}</td>
                <td className="p-4 text-right">
                  <button className="text-blue-600 hover:text-blue-700 text-xs font-medium">View</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ REPLIES PAGE ============
// Per REPLY_HANDLING.md spec: Uses intent classification and handled status
function RepliesPage() {
  const [selectedReply, setSelectedReply] = useState<number | null>(1);
  const [channelFilter, setChannelFilter] = useState<string | null>(null);
  const [showHandled, setShowHandled] = useState(false);

  // Per spec: intent values from ReplyIntent enum
  // meeting_interest, question, positive_engagement, not_interested, out_of_office, wrong_person, referral, angry_or_complaint
  const replies = [
    { id: 1, lead: "Sarah Chen", company: "TechCorp", channel: "email", subject: "Re: Scaling your engineering team", preview: "Hi, thanks for reaching out. I'd love to learn more about...", time: "2m", handled: false, intent: "meeting_interest", tier: "hot" },
    { id: 2, lead: "Mike Johnson", company: "StartupXYZ", channel: "linkedin", subject: "Connection accepted", preview: "Thanks for connecting! I saw your profile and...", time: "15m", handled: false, intent: "positive_engagement", tier: "warm" },
    { id: 3, lead: "Lisa Park", company: "Acme Inc", channel: "email", subject: "Re: Quick question", preview: "Not interested at this time, but please keep me...", time: "1h", handled: false, intent: "not_interested", tier: "warm" },
    { id: 4, lead: "David Lee", company: "Growth Co", channel: "email", subject: "Re: Partnership opportunity", preview: "This sounds interesting. Can you send more details about...", time: "2h", handled: true, intent: "question", tier: "warm" },
    { id: 5, lead: "Emma Wilson", company: "Scale Labs", channel: "sms", subject: "SMS Reply", preview: "Yes, I'm available Thursday afternoon. What time works?", time: "3h", handled: true, intent: "meeting_interest", tier: "hot" },
    { id: 6, lead: "James Brown", company: "Innovate Inc", channel: "linkedin", subject: "Message reply", preview: "We already have a solution in place, but thanks for...", time: "5h", handled: true, intent: "not_interested", tier: "cool" },
    { id: 7, lead: "Amy Zhang", company: "NextGen AI", channel: "email", subject: "OOO: Away until next week", preview: "I'm currently out of office until...", time: "6h", handled: true, intent: "out_of_office", tier: "warm" },
    { id: 8, lead: "Robert Kim", company: "DataSoft", channel: "email", subject: "Re: Quick question", preview: "You should talk to my colleague Mark instead...", time: "1d", handled: false, intent: "referral", tier: "cool" },
  ];

  const selected = replies.find(r => r.id === selectedReply);

  // Intent labels and colors per spec
  const intentConfig: Record<string, { label: string; style: string }> = {
    meeting_interest: { label: "Meeting Interest", style: "bg-emerald-100 text-emerald-700" },
    question: { label: "Question", style: "bg-blue-100 text-blue-700" },
    positive_engagement: { label: "Positive", style: "bg-sky-100 text-sky-700" },
    not_interested: { label: "Not Interested", style: "bg-orange-100 text-orange-700" },
    out_of_office: { label: "Out of Office", style: "bg-slate-100 text-slate-600" },
    wrong_person: { label: "Wrong Person", style: "bg-amber-100 text-amber-700" },
    referral: { label: "Referral", style: "bg-purple-100 text-purple-700" },
    angry_or_complaint: { label: "Complaint", style: "bg-red-100 text-red-700" },
  };

  // Filter replies based on channel and handled status
  const filteredReplies = replies.filter(r => {
    if (channelFilter && r.channel !== channelFilter) return false;
    if (!showHandled && r.handled) return false;
    return true;
  });

  return (
    <div className="p-6 min-h-screen">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Replies</h2>
          <p className="text-sm text-slate-500">{filteredReplies.filter(r => !r.handled).length} pending replies requiring attention</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Channel Filter */}
          <div className="flex items-center gap-1 border border-slate-200 rounded-lg p-1">
            {[
              { key: null, label: "All" },
              { key: "email", label: "Email", icon: Mail },
              { key: "linkedin", label: "LinkedIn", icon: Linkedin },
              { key: "sms", label: "SMS", icon: MessageCircle },
            ].map((ch) => (
              <button
                key={ch.key || "all"}
                onClick={() => setChannelFilter(ch.key)}
                className={`px-2.5 py-1.5 text-xs font-medium rounded flex items-center gap-1.5 ${
                  channelFilter === ch.key ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                {ch.icon && <ch.icon className="w-3.5 h-3.5" />}
                {ch.label}
              </button>
            ))}
          </div>
          {/* Show Handled Toggle */}
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={showHandled}
              onChange={(e) => setShowHandled(e.target.checked)}
              className="w-4 h-4 rounded border-slate-300"
            />
            Show handled
          </label>
        </div>
      </div>

      {/* Split View */}
      <div className="grid grid-cols-12 gap-4 h-[calc(100vh-180px)]">
        {/* Reply List */}
        <div className="col-span-4 bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 overflow-hidden flex flex-col">
          <div className="p-3 border-b border-slate-100 flex items-center gap-2">
            <span className="text-xs text-slate-500">Filter by intent:</span>
            <button className="px-2.5 py-1 bg-emerald-50 text-emerald-700 text-xs font-medium rounded-lg">Meeting</button>
            <button className="px-2.5 py-1 text-slate-600 text-xs font-medium rounded-lg hover:bg-slate-50">Question</button>
            <button className="px-2.5 py-1 text-slate-600 text-xs font-medium rounded-lg hover:bg-slate-50">Referral</button>
          </div>
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {filteredReplies.map((reply) => (
              <button
                key={reply.id}
                onClick={() => setSelectedReply(reply.id)}
                className={`w-full p-3 text-left hover:bg-slate-50 transition-colors ${
                  selectedReply === reply.id ? "bg-blue-50 border-l-2 border-l-blue-500" : ""
                } ${!reply.handled ? "bg-blue-50/50" : ""}`}
              >
                <div className="flex items-start gap-3">
                  <ChannelIcon channel={reply.channel} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className={`font-medium text-sm ${!reply.handled ? "text-slate-900" : "text-slate-600"}`}>
                        {reply.lead}
                      </span>
                      <div className="flex items-center gap-2">
                        {reply.handled && <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />}
                        <span className="text-xs text-slate-400">{reply.time}</span>
                      </div>
                    </div>
                    <div className="text-xs text-slate-500 mb-1">{reply.company}</div>
                    <p className="text-xs text-slate-600 truncate">{reply.preview}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <TierBadge tier={reply.tier} />
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${intentConfig[reply.intent]?.style || "bg-slate-100 text-slate-600"}`}>
                        {intentConfig[reply.intent]?.label || reply.intent}
                      </span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Reply Detail */}
        <div className="col-span-8 bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 overflow-hidden flex flex-col">
          {selected ? (
            <>
              <div className="p-4 border-b border-slate-100">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-slate-900">{selected.lead}</h3>
                    <p className="text-sm text-slate-500">{selected.company}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <TierBadge tier={selected.tier} />
                    <span className={`px-2 py-1 rounded text-xs font-medium ${intentConfig[selected.intent]?.style || "bg-slate-100 text-slate-600"}`}>
                      {intentConfig[selected.intent]?.label || selected.intent}
                    </span>
                    {selected.handled && (
                      <span className="px-2 py-1 rounded text-xs font-medium bg-emerald-100 text-emerald-700 flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" /> Handled
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-4 text-sm text-slate-500">
                  <span className="flex items-center gap-1"><ChannelIcon channel={selected.channel} size="sm" /> via {selected.channel}</span>
                  <span>{selected.time} ago</span>
                </div>
              </div>

              <div className="flex-1 p-4 overflow-y-auto">
                <div className="bg-slate-50 rounded-lg p-4 mb-4">
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {selected.preview} This is the full message content that would appear here. The lead has responded to your outreach and this is their complete reply that you can read and respond to appropriately.
                  </p>
                </div>

                {/* AI Suggested Response */}
                <div className="border border-purple-200 bg-purple-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-purple-600" />
                    <span className="text-sm font-medium text-purple-900">AI Suggested Response</span>
                  </div>
                  <p className="text-sm text-purple-800 leading-relaxed mb-3">
                    Hi {selected.lead.split(" ")[0]}, thank you for your response! I'd be happy to share more details. Would you have 15 minutes this week for a quick call? I can walk you through how we've helped similar companies in your space.
                  </p>
                  <div className="flex items-center gap-2">
                    <button className="px-3 py-1.5 bg-purple-600 text-white text-xs font-medium rounded-lg hover:bg-purple-700">
                      Use This Response
                    </button>
                    <button className="px-3 py-1.5 border border-purple-300 text-purple-700 text-xs font-medium rounded-lg hover:bg-purple-100">
                      Edit
                    </button>
                    <button className="px-3 py-1.5 text-purple-600 text-xs font-medium hover:text-purple-800">
                      Regenerate
                    </button>
                  </div>
                </div>
              </div>

              <div className="p-4 border-t border-slate-100">
                <textarea
                  placeholder="Type your reply..."
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                />
                <div className="flex items-center justify-between mt-3">
                  <div className="flex items-center gap-2">
                    <button className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
                      <Calendar className="w-4 h-4" />
                    </button>
                    <button className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
                      <Clock className="w-4 h-4" />
                    </button>
                  </div>
                  <button className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2">
                    <Send className="w-4 h-4" /> Send Reply
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400">
              Select a reply to view
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============ REPORTS PAGE ============
function ReportsPage() {
  const weeklyData = [
    { week: "W1", meetings: 2, replies: 15, sent: 180 },
    { week: "W2", meetings: 4, replies: 22, sent: 210 },
    { week: "W3", meetings: 3, replies: 18, sent: 195 },
    { week: "W4", meetings: 5, replies: 28, sent: 240 },
  ];

  // Per DASHBOARD.md: Campaign performance shows client-visible metrics only
  // NO cost or cost-per-meeting (internal metrics not for clients)
  const campaignPerformance = [
    { name: "Tech Decision Makers", meetings: 6, replyRate: 5.1, showRate: 83, openRate: 47 },
    { name: "Series A Startups", meetings: 4, replyRate: 5.6, showRate: 75, openRate: 52 },
    { name: "Enterprise Accounts", meetings: 2, replyRate: 4.4, showRate: 100, openRate: 38 },
  ];

  const funnelData = [
    { stage: "Sourced", count: 1500, pct: 100 },
    { stage: "Enriched", count: 1200, pct: 80 },
    { stage: "Contacted", count: 950, pct: 63 },
    { stage: "Replied", count: 90, pct: 6 },
    { stage: "Meeting Booked", count: 14, pct: 0.9 },
    { stage: "Showed", count: 12, pct: 0.8 },
  ];

  return (
    <div className="p-6 min-h-screen">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Reports</h2>
          <p className="text-sm text-slate-500">Performance analytics and insights</p>
        </div>
        <div className="flex items-center gap-2">
          <select className="px-3 py-2 border border-slate-200 text-slate-700 text-sm rounded-lg bg-white">
            <option>Last 30 days</option>
            <option>Last 7 days</option>
            <option>Last 90 days</option>
            <option>This month</option>
          </select>
          <button className="px-3 py-2 border border-slate-200 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-50 flex items-center gap-2">
            <Download className="w-4 h-4" /> Export
          </button>
        </div>
      </div>

      {/* Summary Stats - Per DASHBOARD.md: Only metrics that exist in API */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-4">
          <div className="text-xs text-slate-500 mb-1">Total Meetings</div>
          <div className="text-2xl font-bold text-slate-900">14</div>
          <div className="text-xs text-emerald-600 flex items-center gap-1 mt-1">
            <ArrowUpRight className="w-3 h-3" /> +40% vs last period
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-4">
          <div className="text-xs text-slate-500 mb-1">Avg Show Rate</div>
          <div className="text-2xl font-bold text-slate-900">85.7%</div>
          <div className="text-xs text-emerald-600 flex items-center gap-1 mt-1">
            <ArrowUpRight className="w-3 h-3" /> +5% vs last period
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-4">
          <div className="text-xs text-slate-500 mb-1">Reply Rate</div>
          <div className="text-2xl font-bold text-slate-900">4.8%</div>
          <div className="text-xs text-emerald-600 flex items-center gap-1 mt-1">
            <ArrowUpRight className="w-3 h-3" /> +0.3% vs last period
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-4">
          <div className="text-xs text-slate-500 mb-1">Deals Closed</div>
          <div className="text-2xl font-bold text-slate-900">3</div>
          <div className="text-xs text-emerald-600 flex items-center gap-1 mt-1">
            <ArrowUpRight className="w-3 h-3" /> +50% vs last period
          </div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Weekly Trend */}
        <div className="col-span-8 bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Weekly Performance</h3>
          <div className="h-48 flex items-end gap-4">
            {weeklyData.map((week) => (
              <div key={week.week} className="flex-1 flex flex-col items-center gap-2">
                <div className="w-full flex flex-col gap-1">
                  <div className="w-full bg-blue-500 rounded-t" style={{ height: `${week.meetings * 20}px` }} title={`${week.meetings} meetings`} />
                  <div className="w-full bg-emerald-500" style={{ height: `${week.replies * 2}px` }} title={`${week.replies} replies`} />
                  <div className="w-full bg-slate-200 rounded-b" style={{ height: `${week.sent / 10}px` }} title={`${week.sent} sent`} />
                </div>
                <span className="text-xs text-slate-500">{week.week}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center justify-center gap-6 mt-4 pt-4 border-t border-slate-100">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-blue-500" />
              <span className="text-xs text-slate-600">Meetings</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-emerald-500" />
              <span className="text-xs text-slate-600">Replies</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-slate-200" />
              <span className="text-xs text-slate-600">Sent</span>
            </div>
          </div>
        </div>

        {/* Funnel */}
        <div className="col-span-4 bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Conversion Funnel</h3>
          <div className="space-y-3">
            {funnelData.map((stage, i) => (
              <div key={stage.stage}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-slate-600">{stage.stage}</span>
                  <span className="font-medium text-slate-900">{stage.count.toLocaleString()}</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full"
                    style={{ width: `${stage.pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Campaign Performance Table - Per DASHBOARD.md: Client-visible metrics only */}
        <div className="col-span-12 bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10">
          <div className="px-5 py-4 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-900">Campaign Performance</h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs text-slate-500">
                <th className="text-left p-4 font-medium">Campaign</th>
                <th className="text-right p-4 font-medium">Meetings</th>
                <th className="text-right p-4 font-medium">Open Rate</th>
                <th className="text-right p-4 font-medium">Reply Rate</th>
                <th className="text-right p-4 font-medium">Show Rate</th>
                <th className="text-right p-4 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {campaignPerformance.map((campaign) => (
                <tr key={campaign.name} className="border-b border-slate-50">
                  <td className="p-4 font-medium text-slate-900">{campaign.name}</td>
                  <td className="p-4 text-right text-slate-900">{campaign.meetings}</td>
                  <td className="p-4 text-right">
                    <span className="text-slate-600">{campaign.openRate}%</span>
                  </td>
                  <td className="p-4 text-right">
                    <span className="text-blue-600 font-medium">{campaign.replyRate}%</span>
                  </td>
                  <td className="p-4 text-right">
                    <span className={`font-medium ${campaign.showRate >= 80 ? "text-emerald-600" : "text-orange-600"}`}>
                      {campaign.showRate}%
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      campaign.showRate >= 80 ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                    }`}>
                      {campaign.showRate >= 80 ? "On Track" : "Needs Review"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ============ SETTINGS PAGE ============
function SettingsPage() {
  const [activeTab, setActiveTab] = useState("icp");

  const tabs = [
    { id: "icp", label: "ICP Settings", icon: Target },
    { id: "linkedin", label: "LinkedIn", icon: Linkedin },
    { id: "profile", label: "Company Profile", icon: Building },
    { id: "notifications", label: "Notifications", icon: Bell },
  ];

  return (
    <div className="p-6 min-h-screen">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-slate-900">Settings</h2>
        <p className="text-sm text-slate-500">Configure your account and targeting preferences</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar Tabs */}
        <div className="w-56 space-y-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-blue-50 text-blue-700 border border-blue-200"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === "icp" && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-1">Ideal Customer Profile</h3>
              <p className="text-sm text-slate-500 mb-6">Define who you want to target</p>

              <div className="space-y-6">
                {/* Industries */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Target Industries</label>
                  <div className="flex flex-wrap gap-2">
                    {["SaaS", "FinTech", "HealthTech", "E-commerce", "MarTech"].map((ind) => (
                      <span key={ind} className="px-3 py-1.5 bg-blue-50 text-blue-700 text-sm rounded-lg flex items-center gap-2">
                        {ind}
                        <button className="text-blue-400 hover:text-blue-600">×</button>
                      </span>
                    ))}
                    <button className="px-3 py-1.5 border border-dashed border-slate-300 text-slate-500 text-sm rounded-lg hover:border-blue-400 hover:text-blue-600">
                      + Add Industry
                    </button>
                  </div>
                </div>

                {/* Company Size */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Company Size</label>
                  <div className="grid grid-cols-4 gap-3">
                    {[
                      { label: "1-10", selected: false },
                      { label: "11-50", selected: true },
                      { label: "51-200", selected: true },
                      { label: "201-500", selected: true },
                    ].map((size) => (
                      <button
                        key={size.label}
                        className={`px-4 py-2 rounded-lg text-sm font-medium border ${
                          size.selected
                            ? "bg-blue-50 border-blue-200 text-blue-700"
                            : "border-slate-200 text-slate-600 hover:border-blue-200"
                        }`}
                      >
                        {size.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Job Titles */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Target Job Titles</label>
                  <div className="flex flex-wrap gap-2">
                    {["CEO", "CTO", "VP Engineering", "Head of Product", "Founder"].map((title) => (
                      <span key={title} className="px-3 py-1.5 bg-emerald-50 text-emerald-700 text-sm rounded-lg flex items-center gap-2">
                        {title}
                        <button className="text-emerald-400 hover:text-emerald-600">×</button>
                      </span>
                    ))}
                    <button className="px-3 py-1.5 border border-dashed border-slate-300 text-slate-500 text-sm rounded-lg hover:border-emerald-400 hover:text-emerald-600">
                      + Add Title
                    </button>
                  </div>
                </div>

                {/* Geography */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Target Geography</label>
                  <div className="flex flex-wrap gap-2">
                    {["Australia", "United States", "United Kingdom"].map((geo) => (
                      <span key={geo} className="px-3 py-1.5 bg-purple-50 text-purple-700 text-sm rounded-lg flex items-center gap-2">
                        {geo}
                        <button className="text-purple-400 hover:text-purple-600">×</button>
                      </span>
                    ))}
                    <button className="px-3 py-1.5 border border-dashed border-slate-300 text-slate-500 text-sm rounded-lg hover:border-purple-400 hover:text-purple-600">
                      + Add Location
                    </button>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100">
                  <button className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
                    Save ICP Settings
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === "linkedin" && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-1">LinkedIn Connection</h3>
              <p className="text-sm text-slate-500 mb-6">Manage your LinkedIn account integration</p>

              <div className="space-y-6">
                {/* Connected Account */}
                <div className="flex items-center justify-between p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-emerald-500 rounded-full flex items-center justify-center">
                      <CheckCircle className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <p className="font-medium text-emerald-900">Connected</p>
                      <p className="text-sm text-emerald-700">john.smith@company.com</p>
                    </div>
                  </div>
                  <button className="px-3 py-1.5 text-emerald-700 text-sm font-medium hover:bg-emerald-100 rounded-lg">
                    Disconnect
                  </button>
                </div>

                {/* Daily Limits */}
                <div>
                  <h4 className="text-sm font-medium text-slate-700 mb-3">Daily Activity Limits</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 border border-slate-200 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-slate-600">Connection Requests</span>
                        <span className="font-medium text-slate-900">25/day</span>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500 rounded-full" style={{ width: "60%" }} />
                      </div>
                      <p className="text-xs text-slate-500 mt-1">15 sent today</p>
                    </div>
                    <div className="p-4 border border-slate-200 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-slate-600">Messages</span>
                        <span className="font-medium text-slate-900">50/day</span>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-emerald-500 rounded-full" style={{ width: "40%" }} />
                      </div>
                      <p className="text-xs text-slate-500 mt-1">20 sent today</p>
                    </div>
                  </div>
                </div>

                {/* Health Score */}
                <div className="p-4 border border-slate-200 rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-slate-700">Account Health</h4>
                    <span className="px-2 py-1 bg-emerald-100 text-emerald-700 text-xs font-medium rounded">Excellent</span>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-slate-900">98%</div>
                      <div className="text-xs text-slate-500">Acceptance Rate</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-slate-900">0</div>
                      <div className="text-xs text-slate-500">Warnings</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-slate-900">45d</div>
                      <div className="text-xs text-slate-500">Account Age</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "profile" && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-1">Company Profile</h3>
              <p className="text-sm text-slate-500 mb-6">Your company information for outreach</p>

              {/* Coming Soon Banner - Per audit: NOT IMPLEMENTED in backend */}
              <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
                <div>
                  <p className="font-medium text-amber-800">Coming Soon</p>
                  <p className="text-sm text-amber-700">Company profile settings are being implemented. This preview shows the planned interface.</p>
                </div>
              </div>

              <div className="space-y-5 opacity-60">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Company Name</label>
                  <input
                    type="text"
                    defaultValue="Acme Agency"
                    disabled
                    className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm bg-slate-50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Website</label>
                  <input
                    type="text"
                    defaultValue="https://acmeagency.com"
                    disabled
                    className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm bg-slate-50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Description</label>
                  <textarea
                    defaultValue="We help B2B companies scale their outbound sales through AI-powered lead generation and multi-channel outreach."
                    rows={3}
                    disabled
                    className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm bg-slate-50 resize-none"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Industry</label>
                    <select disabled className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm bg-slate-50">
                      <option>Marketing Agency</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Team Size</label>
                    <select disabled className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm bg-slate-50">
                      <option>1-10</option>
                    </select>
                  </div>
                </div>
                <div className="pt-4 border-t border-slate-100">
                  <button disabled className="px-4 py-2 bg-slate-300 text-slate-500 text-sm font-medium rounded-lg cursor-not-allowed">
                    Save Profile
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === "notifications" && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-lg shadow-black/10 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-1">Notification Preferences</h3>
              <p className="text-sm text-slate-500 mb-6">Choose how you want to be notified</p>

              {/* Coming Soon Banner - Per audit: NOT IMPLEMENTED in backend */}
              <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
                <div>
                  <p className="font-medium text-amber-800">Coming Soon</p>
                  <p className="text-sm text-amber-700">Notification preferences are being implemented. This preview shows the planned interface.</p>
                </div>
              </div>

              <div className="space-y-4 opacity-60">
                {[
                  { id: "replies", label: "New Replies", desc: "Get notified when leads reply to your messages", enabled: true },
                  { id: "meetings", label: "Meeting Booked", desc: "Get notified when a meeting is scheduled", enabled: true },
                  { id: "priority_alert", label: "High Priority Alert", desc: "Get notified when a prospect shows strong interest", enabled: true },
                  { id: "daily_digest", label: "Daily Digest", desc: "Receive a daily summary of all activity", enabled: false },
                  { id: "weekly_report", label: "Weekly Report", desc: "Receive a weekly performance report", enabled: true },
                ].map((notif) => (
                  <div key={notif.id} className="flex items-center justify-between p-4 border border-slate-200 rounded-lg">
                    <div>
                      <p className="font-medium text-slate-900">{notif.label}</p>
                      <p className="text-sm text-slate-500">{notif.desc}</p>
                    </div>
                    <div
                      className={`w-12 h-6 rounded-full ${
                        notif.enabled ? "bg-blue-400" : "bg-slate-200"
                      }`}
                    >
                      <div
                        className={`w-5 h-5 bg-white rounded-full shadow ${
                          notif.enabled ? "translate-x-6" : "translate-x-0.5"
                        }`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============ MAIN PAGE ============
export default function PrototypePage() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const [showNewCampaignModal, setShowNewCampaignModal] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState(0);
  const [isPageTransitioning, setIsPageTransitioning] = useState(false);
  const [pageAnimationKey, setPageAnimationKey] = useState(0);

  const titles: Record<PageKey, string> = {
    dashboard: "Dashboard",
    campaigns: "Campaigns",
    leads: "Leads",
    replies: "Replies",
    reports: "Reports",
    settings: "Settings",
  };

  // Handle page navigation with animation
  const handleNavigate = (page: PageKey) => {
    if (page === activePage) return;
    setIsPageTransitioning(true);

    // Brief exit animation, then switch page
    setTimeout(() => {
      setActivePage(page);
      setPageAnimationKey(prev => prev + 1);

      // Allow entrance animation to play
      setTimeout(() => {
        setIsPageTransitioning(false);
      }, 50);
    }, 200);
  };

  const handleNewCampaign = (data: { name: string; description: string; permissionMode: string }) => {
    setShowNewCampaignModal(false);
    // In real app, this would call API to create campaign
    // then trigger the processing state
    handleConfirmActivate();
  };

  const handleConfirmActivate = () => {
    setIsProcessing(true);
    setProcessingStage(0);

    // Simulate processing stages
    const stageTimings = [1500, 2000, 2500, 2000, 1500];
    let currentStage = 0;

    const advanceStage = () => {
      currentStage++;
      if (currentStage < stageTimings.length) {
        setProcessingStage(currentStage);
        setTimeout(advanceStage, stageTimings[currentStage]);
      } else {
        // Done processing
        setTimeout(() => {
          setIsProcessing(false);
          setProcessingStage(0);
        }, 1000);
      }
    };

    setTimeout(advanceStage, stageTimings[0]);
  };

  const renderPage = () => {
    switch (activePage) {
      case "dashboard": return <DashboardPage onConfirmActivate={handleConfirmActivate} onNewCampaign={() => setShowNewCampaignModal(true)} />;
      case "campaigns": return <CampaignsPage onNewCampaign={() => setShowNewCampaignModal(true)} />;
      case "leads": return <LeadsPage />;
      case "replies": return <RepliesPage />;
      case "reports": return <ReportsPage />;
      case "settings": return <SettingsPage />;
      default: return <DashboardPage onConfirmActivate={handleConfirmActivate} onNewCampaign={() => setShowNewCampaignModal(true)} />;
    }
  };

  return (
    <div className="flex min-h-screen bg-[#8a8e96]">
      <Sidebar activePage={activePage} onNavigate={handleNavigate} />
      <div className="flex-1 ml-60">
        <Header title={titles[activePage]} />

        {/* Page Content with Animations */}
        <div
          key={pageAnimationKey}
          className={`transition-all duration-300 ease-out ${
            isPageTransitioning
              ? "opacity-0 scale-95 translate-y-4"
              : "opacity-100 scale-100 translate-y-0"
          }`}
          style={{
            animation: !isPageTransitioning ? "pageEnter 0.4s ease-out forwards" : "none",
          }}
        >
          {renderPage()}
        </div>
      </div>

      {/* New Campaign Modal */}
      <NewCampaignModal
        isOpen={showNewCampaignModal}
        onClose={() => setShowNewCampaignModal(false)}
        onSubmit={handleNewCampaign}
      />

      {/* Processing Overlay */}
      <ProcessingOverlay isVisible={isProcessing} stage={processingStage} />

      {/* Page Transition Styles */}
      <style jsx global>{`
        @keyframes pageEnter {
          0% {
            opacity: 0;
            transform: scale(0.96) translateY(20px);
          }
          50% {
            opacity: 0.8;
            transform: scale(0.99) translateY(8px);
          }
          100% {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }

        @keyframes cardStagger {
          0% {
            opacity: 0;
            transform: translateY(20px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-card-enter {
          animation: cardStagger 0.4s ease-out forwards;
        }
      `}</style>
    </div>
  );
}

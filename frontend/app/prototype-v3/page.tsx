/**
 * V3 — "Corporate Blue"
 * Professional blue palette, sharp clean lines, data-dense, structured layout
 */
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  LayoutDashboard, Target, Users, MessageSquare, BarChart3, Settings,
  Calendar, TrendingDown, Mail, Linkedin, Phone,
  MessageCircle, Zap, Bell, Search, MoreHorizontal, ArrowUpRight,
  Activity, CheckCircle, Play, Pause, Plus, Sparkles, ChevronRight,
} from "lucide-react";
import { NumberTicker } from "@/components/ui/number-ticker";

type PageKey = "dashboard" | "campaigns" | "leads" | "replies" | "reports" | "settings";

function Sidebar({ activePage, onNavigate }: { activePage: PageKey; onNavigate: (p: PageKey) => void }) {
  const navItems: { key: PageKey; label: string; icon: typeof LayoutDashboard; badge?: number }[] = [
    { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { key: "campaigns", label: "Campaigns", icon: Target, badge: 3 },
    { key: "leads", label: "Leads", icon: Users, badge: 150 },
    { key: "replies", label: "Replies", icon: MessageSquare, badge: 8 },
    { key: "reports", label: "Reports", icon: BarChart3 },
    { key: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <div className="w-[240px] bg-[#1e3a5f] flex flex-col h-screen fixed left-0 top-0">
      <div className="p-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-white/10 rounded-lg flex items-center justify-center">
            <Zap className="w-5 h-5 text-cyan-400" />
          </div>
          <span className="text-[15px] font-bold text-white tracking-tight">Agency OS</span>
        </div>
      </div>
      <nav className="flex-1 px-3 space-y-0.5">
        {navItems.map((item) => (
          <button key={item.key} onClick={() => onNavigate(item.key)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all ${
              activePage === item.key ? "bg-white text-[#1e3a5f] shadow-lg" : "text-blue-100/60 hover:text-white hover:bg-white/10"
            }`}>
            <item.icon className="w-[18px] h-[18px]" />
            <span className="flex-1 text-left">{item.label}</span>
            {item.badge && <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${activePage === item.key ? "bg-[#1e3a5f]/10 text-[#1e3a5f]" : "bg-white/10 text-blue-200"}`}>{item.badge}</span>}
          </button>
        ))}
      </nav>
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-lg bg-cyan-500 flex items-center justify-center text-white text-xs font-bold">A</div>
          <div><p className="text-[13px] font-medium text-white">Acme Agency</p><p className="text-[11px] text-blue-200/50">Velocity Plan</p></div>
        </div>
      </div>
    </div>
  );
}

function ChannelIcon({ channel }: { channel: string }) {
  const config: Record<string, { bg: string; icon: typeof Mail }> = {
    email: { bg: "bg-blue-100 text-blue-700", icon: Mail },
    linkedin: { bg: "bg-sky-100 text-sky-700", icon: Linkedin },
    sms: { bg: "bg-teal-100 text-teal-700", icon: MessageCircle },
    voice: { bg: "bg-indigo-100 text-indigo-700", icon: Phone },
  };
  const { bg, icon: Icon } = config[channel] || config.email;
  return <div className={`w-7 h-7 rounded ${bg} flex items-center justify-center`}><Icon className="w-3.5 h-3.5" /></div>;
}

export default function PrototypeV3() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");

  const campaigns = [
    { id: 1, name: "Tech Decision Makers", priority: 40, meetings: 6, replyRate: 5.1, showRate: 83, channels: ["email", "linkedin"], isAI: true },
    { id: 2, name: "Series A Startups", priority: 35, meetings: 4, replyRate: 5.6, showRate: 75, channels: ["email", "linkedin", "voice"], isAI: true },
    { id: 3, name: "Enterprise Accounts", priority: 25, meetings: 2, replyRate: 4.4, showRate: 100, channels: ["email"], isAI: false },
  ];

  const activities = [
    { id: 1, channel: "email", lead: "Sarah Chen", company: "TechCorp", action: "Positive reply - wants demo", time: "2m", tier: "hot" },
    { id: 2, channel: "email", lead: "Mike Johnson", company: "StartupXYZ", action: "Opened 3x", time: "8m", tier: "warm" },
    { id: 3, channel: "voice", lead: "Lisa Park", company: "Acme Inc", action: "Meeting booked - Tomorrow 2pm", time: "15m", tier: "hot" },
    { id: 4, channel: "linkedin", lead: "David Lee", company: "Growth Co", action: "Clicked pricing link", time: "22m", tier: "warm" },
    { id: 5, channel: "linkedin", lead: "Emma Wilson", company: "Scale Labs", action: "Accepted connection", time: "35m", tier: "cool" },
  ];

  const meetings = [
    { lead: "Sarah Chen", company: "TechCorp", time: "2:00 PM", day: "Today", type: "Discovery" },
    { lead: "Mike Johnson", company: "StartupXYZ", time: "10:00 AM", day: "Tomorrow", type: "Demo" },
    { lead: "Lisa Park", company: "Acme Inc", time: "3:30 PM", day: "Thu", type: "Follow-up" },
  ];

  const tierLabel: Record<string, { label: string; style: string }> = {
    hot: { label: "High Priority", style: "bg-red-50 text-red-700 border-red-200" },
    warm: { label: "Engaged", style: "bg-amber-50 text-amber-700 border-amber-200" },
    cool: { label: "Nurturing", style: "bg-blue-50 text-blue-700 border-blue-200" },
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <div className="ml-[240px]">
        <div className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-10 shadow-sm">
          <div className="flex items-center gap-3">
            <h1 className="text-[15px] font-bold text-[#1e3a5f]">Dashboard Overview</h1>
            <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[11px] font-semibold rounded border border-emerald-200">LIVE</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input className="w-60 pl-9 pr-4 py-1.5 text-[13px] bg-gray-50 border border-gray-200 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300" placeholder="Search..." />
            </div>
            <button className="relative p-2 text-gray-400 hover:text-gray-700"><Bell className="w-5 h-5" /><span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" /></button>
          </div>
        </div>

        <div className="p-6 space-y-5">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "Meetings Booked", value: 12, change: 25, icon: Calendar, accent: "border-l-blue-500" },
              { label: "Show Rate", value: 83, suffix: "%", change: 5, icon: CheckCircle, accent: "border-l-emerald-500" },
              { label: "Deals Created", value: 3, change: 50, icon: Sparkles, accent: "border-l-purple-500" },
              { label: "Reply Rate", value: 5, suffix: "%", change: 12, icon: MessageSquare, accent: "border-l-amber-500" },
            ].map((s, i) => (
              <div key={s.label} className={`bg-white rounded-lg border border-gray-200 border-l-4 ${s.accent} p-4 shadow-sm hover:shadow-md transition-shadow`}>
                <div className="flex items-start justify-between mb-2">
                  <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">{s.label}</span>
                  <s.icon className="w-4 h-4 text-gray-300" />
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-[#1e3a5f]"><NumberTicker value={s.value} delay={i * 0.15} /></span>
                  {s.suffix && <span className="text-lg text-gray-400">{s.suffix}</span>}
                </div>
                <div className="flex items-center gap-1 mt-1">
                  <ArrowUpRight className="w-3 h-3 text-emerald-600" />
                  <span className="text-[11px] font-semibold text-emerald-600">+{s.change}%</span>
                  <span className="text-[10px] text-gray-400">vs last month</span>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-12 gap-5">
            {/* Campaigns */}
            <div className="col-span-8 space-y-5">
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                  <div className="flex items-center gap-2">
                    <h2 className="text-[13px] font-bold text-[#1e3a5f]">Active Campaigns</h2>
                    <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-[11px] font-semibold rounded">3/5</span>
                  </div>
                  <button className="text-[12px] text-blue-600 font-semibold flex items-center gap-1"><Plus className="w-3.5 h-3.5" /> New Campaign</button>
                </div>
                {/* Table-style header */}
                <div className="px-5 py-2 border-b border-gray-100 flex items-center gap-4 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                  <span className="flex-1">Campaign</span>
                  <span className="w-28 text-center">Priority</span>
                  <span className="w-16 text-center">Meetings</span>
                  <span className="w-16 text-center">Reply %</span>
                  <span className="w-16 text-center">Show %</span>
                  <span className="w-8" />
                </div>
                <div className="divide-y divide-gray-100">
                  {campaigns.map((c, i) => (
                    <motion.div key={c.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.08 }}
                      className="px-5 py-3 hover:bg-blue-50/30 transition-colors flex items-center gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-emerald-500" />
                          <span className="text-[13px] font-medium text-gray-900">{c.name}</span>
                          {c.isAI && <span className="px-1 py-0.5 bg-purple-100 text-purple-700 text-[9px] font-bold rounded">AI</span>}
                        </div>
                        <div className="flex gap-1 mt-1">{c.channels.map(ch => <ChannelIcon key={ch} channel={ch} />)}</div>
                      </div>
                      <div className="w-28">
                        <div className="h-2 bg-gray-100 rounded overflow-hidden">
                          <motion.div className="h-full bg-blue-600 rounded" initial={{ width: 0 }} animate={{ width: `${c.priority}%` }} transition={{ duration: 0.5, delay: i * 0.1 }} />
                        </div>
                        <div className="text-[10px] text-gray-500 text-center mt-0.5">{c.priority}%</div>
                      </div>
                      <div className="w-16 text-center text-[14px] font-bold text-gray-900">{c.meetings}</div>
                      <div className="w-16 text-center text-[14px] font-bold text-blue-600">{c.replyRate}%</div>
                      <div className="w-16 text-center text-[14px] font-bold text-emerald-600">{c.showRate}%</div>
                      <button className="w-8 text-gray-300 hover:text-gray-600"><MoreHorizontal className="w-4 h-4" /></button>
                    </motion.div>
                  ))}
                </div>
                <div className="px-5 py-3 border-t border-gray-100 bg-gray-50/50 flex justify-between">
                  <button className="px-3 py-1.5 bg-white text-red-600 text-[12px] font-semibold rounded border border-red-200 flex items-center gap-1.5 hover:bg-red-50"><Pause className="w-3 h-3" /> Pause All</button>
                  <button className="px-4 py-1.5 bg-[#1e3a5f] text-white text-[12px] font-semibold rounded flex items-center gap-1.5 hover:bg-[#2a4a73] transition-colors"><Play className="w-3 h-3" /> Confirm & Activate</button>
                </div>
              </div>

              {/* Activity */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h2 className="text-[13px] font-bold text-[#1e3a5f]">Live Activity</h2>
                    <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[11px] font-semibold rounded"><span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" /> Live</span>
                  </div>
                  <button className="text-[12px] text-blue-600 font-semibold">View All</button>
                </div>
                <div className="divide-y divide-gray-100">
                  {activities.map((a, i) => (
                    <motion.div key={a.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.06 }}
                      className="px-5 py-2.5 hover:bg-blue-50/30 flex items-center gap-3 transition-colors">
                      <ChannelIcon channel={a.channel} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[13px] font-medium text-gray-900">{a.lead}</span>
                          <span className="text-[12px] text-gray-300">at</span>
                          <span className="text-[12px] text-gray-500">{a.company}</span>
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border ${tierLabel[a.tier]?.style}`}>{tierLabel[a.tier]?.label}</span>
                        </div>
                        <p className="text-[11px] text-gray-400 truncate">{a.action}</p>
                      </div>
                      <span className="text-[11px] text-gray-400 font-mono">{a.time}</span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right */}
            <div className="col-span-4 space-y-5">
              {/* Progress */}
              <div className="bg-[#1e3a5f] rounded-lg p-5 text-white">
                <div className="flex justify-between mb-3">
                  <span className="text-[11px] text-blue-200/60 uppercase tracking-wider font-semibold">Monthly Target</span>
                  <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-[11px] font-semibold rounded">On Track</span>
                </div>
                <div className="flex items-baseline gap-2 mb-3">
                  <span className="text-4xl font-bold"><NumberTicker value={12} className="text-white" /></span>
                  <span className="text-blue-200/50">/18 meetings</span>
                </div>
                <div className="h-2.5 bg-white/10 rounded overflow-hidden">
                  <motion.div className="h-full bg-cyan-400 rounded" initial={{ width: 0 }} animate={{ width: "67%" }} transition={{ duration: 1, delay: 0.4 }} />
                </div>
              </div>

              {/* Meetings */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 bg-gray-50/50 flex justify-between">
                  <h2 className="text-[13px] font-bold text-[#1e3a5f]">Upcoming Meetings</h2>
                  <span className="text-[11px] text-gray-400 font-mono">{meetings.length}</span>
                </div>
                <div className="divide-y divide-gray-100">
                  {meetings.map((m, i) => (
                    <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.1 }}
                      className="px-5 py-3 hover:bg-blue-50/30 flex items-center gap-3 transition-colors">
                      <div className="text-center min-w-[44px] bg-blue-50 rounded px-2 py-1"><div className="text-[9px] text-blue-600 uppercase font-bold">{m.day}</div><div className="text-[12px] font-bold text-[#1e3a5f]">{m.time}</div></div>
                      <div className="flex-1"><div className="text-[13px] font-medium text-gray-900">{m.lead}</div><div className="text-[11px] text-gray-400">{m.company}</div></div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                        m.type === "Discovery" ? "bg-blue-50 text-blue-700 border-blue-200" : m.type === "Demo" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-amber-50 text-amber-700 border-amber-200"
                      }`}>{m.type}</span>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Prospects */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-gray-100 bg-gray-50/50 flex justify-between">
                  <h2 className="text-[13px] font-bold text-[#1e3a5f]">Priority Prospects</h2>
                  <span className="px-2 py-0.5 bg-red-50 text-red-700 text-[11px] font-semibold rounded border border-red-200">Urgent</span>
                </div>
                <div className="divide-y divide-gray-100">
                  {[
                    { name: "Sarah Chen", company: "TechCorp", tier: "hot", signals: ["Requested demo", "Opened 3x"] },
                    { name: "Lisa Park", company: "Acme Inc", tier: "hot", signals: ["Meeting scheduled", "LinkedIn engaged"] },
                    { name: "Tom Wilson", company: "DataFlow", tier: "warm", signals: ["Positive reply", "Website visit"] },
                  ].map((l) => (
                    <div key={l.name} className="px-5 py-3 hover:bg-blue-50/30 transition-colors">
                      <div className="flex justify-between mb-1.5">
                        <div><div className="text-[13px] font-medium text-gray-900">{l.name}</div><div className="text-[11px] text-gray-400">{l.company}</div></div>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border ${tierLabel[l.tier]?.style}`}>{tierLabel[l.tier]?.label}</span>
                      </div>
                      <div className="flex gap-1">{l.signals.map((s, i) => <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-[10px] rounded">{s}</span>)}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

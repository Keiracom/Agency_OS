/**
 * V2 — "Soft Gradient"
 * Warm gradients, pastel accents, layered depth, soft rounded cards
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
    <div className="w-[260px] bg-gradient-to-b from-indigo-50 via-white to-purple-50/30 flex flex-col h-screen fixed left-0 top-0 border-r border-indigo-100/50">
      <div className="p-5 border-b border-indigo-100/40">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-200">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-[15px] font-bold text-gray-900">Agency OS</span>
            <p className="text-[10px] text-indigo-400 font-medium">Dashboard</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <button key={item.key} onClick={() => onNavigate(item.key)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all ${
              activePage === item.key
                ? "bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-md shadow-indigo-200"
                : "text-gray-500 hover:text-gray-800 hover:bg-indigo-50/50"
            }`}>
            <item.icon className="w-[18px] h-[18px]" />
            <span className="flex-1 text-left">{item.label}</span>
            {item.badge && <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${activePage === item.key ? "bg-white/20" : "bg-indigo-50 text-indigo-500"}`}>{item.badge}</span>}
          </button>
        ))}
      </nav>
      <div className="p-4 border-t border-indigo-100/40">
        <div className="flex items-center gap-3 px-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white text-sm font-bold shadow-md shadow-amber-200">A</div>
          <div><p className="text-[13px] font-medium text-gray-900">Acme Agency</p><p className="text-[11px] text-indigo-400">Velocity Plan</p></div>
        </div>
      </div>
    </div>
  );
}

function ChannelIcon({ channel }: { channel: string }) {
  const config: Record<string, { bg: string; icon: typeof Mail }> = {
    email: { bg: "bg-blue-100 text-blue-600", icon: Mail },
    linkedin: { bg: "bg-sky-100 text-sky-600", icon: Linkedin },
    sms: { bg: "bg-emerald-100 text-emerald-600", icon: MessageCircle },
    voice: { bg: "bg-purple-100 text-purple-600", icon: Phone },
  };
  const { bg, icon: Icon } = config[channel] || config.email;
  return <div className={`w-7 h-7 rounded-lg ${bg} flex items-center justify-center`}><Icon className="w-3.5 h-3.5" /></div>;
}

export default function PrototypeV2() {
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
    hot: { label: "High Priority", style: "bg-gradient-to-r from-orange-100 to-red-50 text-orange-700 border-orange-200" },
    warm: { label: "Engaged", style: "bg-gradient-to-r from-amber-100 to-yellow-50 text-amber-700 border-amber-200" },
    cool: { label: "Nurturing", style: "bg-gradient-to-r from-blue-100 to-indigo-50 text-blue-700 border-blue-200" },
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-indigo-50/30 to-purple-50/20">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <div className="ml-[260px]">
        <div className="h-14 bg-white/60 backdrop-blur-xl border-b border-indigo-100/40 flex items-center justify-between px-6 sticky top-0 z-10">
          <h1 className="text-[15px] font-semibold text-gray-900">Dashboard</h1>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input className="w-56 pl-9 pr-4 py-1.5 text-[13px] bg-white border border-indigo-100/60 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-200" placeholder="Search..." />
            </div>
            <button className="relative p-2 text-gray-400 hover:text-gray-900 transition-colors"><Bell className="w-5 h-5" /><span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" /></button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "Meetings Booked", value: 12, change: 25, icon: Calendar, gradient: "from-blue-500 to-indigo-600", shadow: "shadow-blue-200" },
              { label: "Show Rate", value: 83, suffix: "%", change: 5, icon: CheckCircle, gradient: "from-emerald-500 to-teal-600", shadow: "shadow-emerald-200" },
              { label: "Deals Created", value: 3, change: 50, icon: Sparkles, gradient: "from-purple-500 to-pink-600", shadow: "shadow-purple-200" },
              { label: "Reply Rate", value: 5, suffix: "%", change: 12, icon: MessageSquare, gradient: "from-amber-500 to-orange-600", shadow: "shadow-amber-200" },
            ].map((s, i) => (
              <div key={s.label} className={`bg-gradient-to-br ${s.gradient} rounded-2xl p-5 text-white shadow-xl ${s.shadow}`}>
                <div className="flex items-start justify-between mb-3">
                  <span className="text-[11px] font-medium text-white/70 uppercase tracking-widest">{s.label}</span>
                  <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center"><s.icon className="w-[18px] h-[18px]" /></div>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-bold"><NumberTicker value={s.value} delay={i * 0.15} className="text-white" /></span>
                  {s.suffix && <span className="text-lg text-white/60">{s.suffix}</span>}
                </div>
                <div className="flex items-center gap-1 mt-2">
                  <ArrowUpRight className="w-3.5 h-3.5 text-white/80" />
                  <span className="text-[12px] font-medium text-white/90">+{s.change}%</span>
                  <span className="text-[11px] text-white/50">vs last month</span>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-12 gap-6">
            {/* Campaigns */}
            <div className="col-span-8 space-y-6">
              <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-indigo-100/40 shadow-lg shadow-indigo-50 overflow-hidden">
                <div className="px-5 py-4 border-b border-indigo-50 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h2 className="text-[13px] font-semibold text-gray-900">Active Campaigns</h2>
                    <span className="px-2 py-0.5 bg-indigo-50 text-indigo-500 text-[11px] rounded-full">3 of 5</span>
                  </div>
                  <button className="text-[12px] text-indigo-600 font-medium flex items-center gap-1"><Plus className="w-3.5 h-3.5" /> Add</button>
                </div>
                <div className="divide-y divide-indigo-50/50">
                  {campaigns.map((c, i) => (
                    <motion.div key={c.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
                      className="px-5 py-4 hover:bg-indigo-50/30 transition-colors">
                      <div className="flex items-center gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1.5">
                            <span className="w-2 h-2 rounded-full bg-emerald-500" />
                            <span className="text-[13px] font-medium text-gray-900">{c.name}</span>
                            {c.isAI && <span className="px-1.5 py-0.5 bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 text-[10px] font-medium rounded">AI</span>}
                          </div>
                          <div className="flex gap-1.5">{c.channels.map(ch => <ChannelIcon key={ch} channel={ch} />)}</div>
                        </div>
                        <div className="w-28">
                          <div className="flex justify-between text-[11px] text-gray-400 mb-1"><span>Priority</span><span className="text-indigo-600 font-medium">{c.priority}%</span></div>
                          <div className="h-2 bg-indigo-50 rounded-full overflow-hidden">
                            <motion.div className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full" initial={{ width: 0 }} animate={{ width: `${c.priority}%` }} transition={{ duration: 0.6, delay: i * 0.1 }} />
                          </div>
                        </div>
                        <div className="flex gap-6 text-center">
                          <div><div className="text-[15px] font-bold text-gray-900">{c.meetings}</div><div className="text-[10px] text-gray-400">Meetings</div></div>
                          <div><div className="text-[15px] font-bold text-indigo-600">{c.replyRate}%</div><div className="text-[10px] text-gray-400">Reply</div></div>
                          <div><div className="text-[15px] font-bold text-emerald-600">{c.showRate}%</div><div className="text-[10px] text-gray-400">Show</div></div>
                        </div>
                        <button className="p-1.5 text-gray-300 hover:text-gray-600"><MoreHorizontal className="w-4 h-4" /></button>
                      </div>
                    </motion.div>
                  ))}
                </div>
                <div className="px-5 py-3 border-t border-indigo-50 flex justify-between">
                  <button className="px-3 py-1.5 bg-red-50 text-red-600 text-[12px] font-medium rounded-lg flex items-center gap-1.5 border border-red-100"><Pause className="w-3 h-3" /> Emergency Pause</button>
                  <button className="px-4 py-1.5 bg-gradient-to-r from-indigo-500 to-purple-500 text-white text-[12px] font-medium rounded-lg flex items-center gap-1.5 shadow-md shadow-indigo-200 hover:shadow-lg transition-shadow"><Play className="w-3 h-3" /> Confirm & Activate</button>
                </div>
              </div>

              {/* Activity */}
              <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-indigo-100/40 shadow-lg shadow-indigo-50 overflow-hidden">
                <div className="px-5 py-4 border-b border-indigo-50 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h2 className="text-[13px] font-semibold text-gray-900">Live Activity</h2>
                    <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-50 text-emerald-600 text-[11px] rounded-full"><span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" /> Live</span>
                  </div>
                  <button className="text-[12px] text-gray-400 hover:text-gray-900 flex items-center gap-0.5">View All <ChevronRight className="w-3.5 h-3.5" /></button>
                </div>
                <div className="divide-y divide-indigo-50/50">
                  {activities.map((a, i) => (
                    <motion.div key={a.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.06 }}
                      className="px-5 py-3 hover:bg-indigo-50/30 flex items-center gap-3 transition-colors">
                      <ChannelIcon channel={a.channel} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[13px] font-medium text-gray-900">{a.lead}</span>
                          <span className="text-[12px] text-gray-300">at</span>
                          <span className="text-[12px] text-gray-500">{a.company}</span>
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${tierLabel[a.tier]?.style}`}>{tierLabel[a.tier]?.label}</span>
                        </div>
                        <p className="text-[11px] text-gray-400 truncate">{a.action}</p>
                      </div>
                      <span className="text-[11px] text-gray-300">{a.time}</span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right */}
            <div className="col-span-4 space-y-6">
              {/* Progress */}
              <div className="bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 rounded-2xl p-5 text-white shadow-xl shadow-indigo-200">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] text-white/70 uppercase tracking-widest">Monthly Progress</span>
                  <span className="px-2 py-0.5 bg-white/20 text-white text-[11px] rounded-full">On Track</span>
                </div>
                <div className="flex items-baseline gap-2 mb-3">
                  <span className="text-5xl font-light"><NumberTicker value={12} className="text-white" /></span>
                  <span className="text-white/50">of 18</span>
                </div>
                <div className="h-2 bg-white/20 rounded-full overflow-hidden">
                  <motion.div className="h-full bg-white rounded-full" initial={{ width: 0 }} animate={{ width: "67%" }} transition={{ duration: 1, delay: 0.4 }} />
                </div>
              </div>

              {/* Meetings */}
              <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-indigo-100/40 shadow-lg shadow-indigo-50 overflow-hidden">
                <div className="px-5 py-4 border-b border-indigo-50 flex justify-between">
                  <h2 className="text-[13px] font-semibold text-gray-900">Upcoming Meetings</h2>
                  <span className="text-[11px] text-indigo-400">{meetings.length} scheduled</span>
                </div>
                <div className="divide-y divide-indigo-50/50">
                  {meetings.map((m, i) => (
                    <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                      className="px-5 py-3 hover:bg-indigo-50/30 flex items-center gap-3 transition-colors">
                      <div className="text-center min-w-[44px]"><div className="text-[10px] text-gray-400 uppercase">{m.day}</div><div className="text-[13px] font-semibold text-gray-900">{m.time}</div></div>
                      <div className="flex-1"><div className="text-[13px] font-medium text-gray-900">{m.lead}</div><div className="text-[11px] text-gray-400">{m.company}</div></div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium border ${
                        m.type === "Discovery" ? "bg-blue-50 text-blue-600 border-blue-100" : m.type === "Demo" ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "bg-amber-50 text-amber-600 border-amber-100"
                      }`}>{m.type}</span>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Prospects */}
              <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-indigo-100/40 shadow-lg shadow-indigo-50 overflow-hidden">
                <div className="px-5 py-4 border-b border-indigo-50 flex justify-between">
                  <h2 className="text-[13px] font-semibold text-gray-900">Priority Prospects</h2>
                  <span className="px-2 py-0.5 bg-orange-50 text-orange-600 text-[11px] rounded-full border border-orange-200">Action</span>
                </div>
                <div className="divide-y divide-indigo-50/50">
                  {[
                    { name: "Sarah Chen", company: "TechCorp", tier: "hot", signals: ["Requested demo", "Opened 3x"] },
                    { name: "Lisa Park", company: "Acme Inc", tier: "hot", signals: ["Meeting scheduled", "LinkedIn engaged"] },
                    { name: "Tom Wilson", company: "DataFlow", tier: "warm", signals: ["Positive reply", "Website visit"] },
                  ].map((l) => (
                    <div key={l.name} className="px-5 py-3 hover:bg-indigo-50/30 transition-colors">
                      <div className="flex justify-between mb-1.5">
                        <div><div className="text-[13px] font-medium text-gray-900">{l.name}</div><div className="text-[11px] text-gray-400">{l.company}</div></div>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${tierLabel[l.tier]?.style}`}>{tierLabel[l.tier]?.label}</span>
                      </div>
                      <div className="flex gap-1">{l.signals.map((s, i) => <span key={i} className="px-2 py-0.5 bg-indigo-50 text-indigo-600 text-[10px] rounded">{s}</span>)}</div>
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

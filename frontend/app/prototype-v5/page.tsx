/**
 * V5 — "Vibrant Modern"
 * Bold accent colors, colored card left-borders, playful shadows, energetic
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
  const navItems: { key: PageKey; label: string; icon: typeof LayoutDashboard; badge?: number; color: string }[] = [
    { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, color: "bg-violet-500" },
    { key: "campaigns", label: "Campaigns", icon: Target, badge: 3, color: "bg-blue-500" },
    { key: "leads", label: "Leads", icon: Users, badge: 150, color: "bg-emerald-500" },
    { key: "replies", label: "Replies", icon: MessageSquare, badge: 8, color: "bg-amber-500" },
    { key: "reports", label: "Reports", icon: BarChart3, color: "bg-pink-500" },
    { key: "settings", label: "Settings", icon: Settings, color: "bg-gray-500" },
  ];

  return (
    <div className="w-[260px] bg-white flex flex-col h-screen fixed left-0 top-0 border-r border-gray-100">
      <div className="p-5 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-pink-500 rounded-2xl flex items-center justify-center shadow-lg shadow-violet-200">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-[15px] font-extrabold text-gray-900">Agency OS</span>
            <p className="text-[10px] text-violet-500 font-bold tracking-wider">DASHBOARD</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <button key={item.key} onClick={() => onNavigate(item.key)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-semibold transition-all ${
              activePage === item.key
                ? "bg-gray-900 text-white shadow-lg shadow-gray-200"
                : "text-gray-400 hover:text-gray-900 hover:bg-gray-50"
            }`}>
            <div className={`w-6 h-6 rounded-lg ${activePage === item.key ? "bg-white/20" : item.color + "/10"} flex items-center justify-center`}>
              <item.icon className={`w-3.5 h-3.5 ${activePage === item.key ? "text-white" : ""}`} style={activePage !== item.key ? { color: item.color.replace("bg-", "").includes("violet") ? "#8b5cf6" : item.color.replace("bg-", "").includes("blue") ? "#3b82f6" : item.color.replace("bg-", "").includes("emerald") ? "#10b981" : item.color.replace("bg-", "").includes("amber") ? "#f59e0b" : item.color.replace("bg-", "").includes("pink") ? "#ec4899" : "#6b7280" } : {}} />
            </div>
            <span className="flex-1 text-left">{item.label}</span>
            {item.badge && <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${activePage === item.key ? "bg-white/20" : "bg-gray-100 text-gray-500"}`}>{item.badge}</span>}
          </button>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-100">
        <div className="flex items-center gap-3 px-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center text-white text-sm font-bold shadow-md shadow-emerald-200">A</div>
          <div><p className="text-[13px] font-bold text-gray-900">Acme Agency</p><p className="text-[11px] text-violet-400 font-medium">Velocity Plan</p></div>
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
    voice: { bg: "bg-violet-100 text-violet-600", icon: Phone },
  };
  const { bg, icon: Icon } = config[channel] || config.email;
  return <div className={`w-7 h-7 rounded-lg ${bg} flex items-center justify-center`}><Icon className="w-3.5 h-3.5" /></div>;
}

export default function PrototypeV5() {
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
    hot: { label: "High Priority", style: "bg-rose-50 text-rose-600 border-rose-200" },
    warm: { label: "Engaged", style: "bg-amber-50 text-amber-600 border-amber-200" },
    cool: { label: "Nurturing", style: "bg-sky-50 text-sky-600 border-sky-200" },
  };

  const statCards = [
    { label: "Meetings Booked", value: 12, change: 25, icon: Calendar, border: "border-l-violet-500", iconBg: "bg-violet-50 text-violet-600", shadow: "hover:shadow-violet-100" },
    { label: "Show Rate", value: 83, suffix: "%", change: 5, icon: CheckCircle, border: "border-l-emerald-500", iconBg: "bg-emerald-50 text-emerald-600", shadow: "hover:shadow-emerald-100" },
    { label: "Deals Created", value: 3, change: 50, icon: Sparkles, border: "border-l-pink-500", iconBg: "bg-pink-50 text-pink-600", shadow: "hover:shadow-pink-100" },
    { label: "Reply Rate", value: 5, suffix: "%", change: 12, icon: MessageSquare, border: "border-l-blue-500", iconBg: "bg-blue-50 text-blue-600", shadow: "hover:shadow-blue-100" },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <div className="ml-[260px]">
        <div className="h-14 bg-white border-b border-gray-100 flex items-center justify-between px-6 sticky top-0 z-10 shadow-sm">
          <div className="flex items-center gap-3">
            <h1 className="text-[15px] font-extrabold text-gray-900">Dashboard</h1>
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 rounded-full">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              <span className="text-[11px] font-bold text-emerald-600">LIVE</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-300" />
              <input className="w-56 pl-9 pr-4 py-1.5 text-[13px] bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-300" placeholder="Search..." />
            </div>
            <button className="relative p-2 bg-gray-50 rounded-xl text-gray-400 hover:text-gray-900 transition-colors"><Bell className="w-5 h-5" /><span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white" /></button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-4">
            {statCards.map((s, i) => (
              <motion.div key={s.label} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
                className={`bg-white rounded-2xl border border-gray-100 border-l-4 ${s.border} p-5 shadow-sm ${s.shadow} hover:shadow-lg transition-all hover:-translate-y-1`}>
                <div className="flex items-start justify-between mb-3">
                  <span className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">{s.label}</span>
                  <div className={`w-9 h-9 rounded-xl ${s.iconBg} flex items-center justify-center`}><s.icon className="w-[18px] h-[18px]" /></div>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-extrabold text-gray-900"><NumberTicker value={s.value} delay={i * 0.15} /></span>
                  {s.suffix && <span className="text-xl text-gray-300 font-bold">{s.suffix}</span>}
                </div>
                <div className="flex items-center gap-1 mt-2">
                  <ArrowUpRight className="w-3.5 h-3.5 text-emerald-500" />
                  <span className="text-[12px] font-bold text-emerald-500">+{s.change}%</span>
                  <span className="text-[11px] text-gray-300">vs last month</span>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-8 space-y-6">
              {/* Campaigns */}
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h2 className="text-[13px] font-extrabold text-gray-900">Active Campaigns</h2>
                    <span className="px-2.5 py-0.5 bg-violet-50 text-violet-600 text-[11px] font-bold rounded-full">3 of 5</span>
                  </div>
                  <button className="px-3 py-1.5 bg-violet-50 text-violet-600 text-[12px] font-bold rounded-lg flex items-center gap-1 hover:bg-violet-100 transition-colors"><Plus className="w-3.5 h-3.5" /> Add</button>
                </div>
                <div className="divide-y divide-gray-50">
                  {campaigns.map((c, i) => (
                    <motion.div key={c.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
                      className="px-5 py-4 hover:bg-violet-50/30 transition-colors">
                      <div className="flex items-center gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-emerald-100" />
                            <span className="text-[13px] font-bold text-gray-900">{c.name}</span>
                            {c.isAI && <span className="px-1.5 py-0.5 bg-gradient-to-r from-violet-500 to-pink-500 text-white text-[9px] font-bold rounded">AI</span>}
                          </div>
                          <div className="flex gap-1.5">{c.channels.map(ch => <ChannelIcon key={ch} channel={ch} />)}</div>
                        </div>
                        <div className="w-28">
                          <div className="flex justify-between text-[11px] text-gray-400 mb-1"><span>Priority</span><span className="text-violet-600 font-bold">{c.priority}%</span></div>
                          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <motion.div className="h-full bg-gradient-to-r from-violet-500 to-pink-500 rounded-full" initial={{ width: 0 }} animate={{ width: `${c.priority}%` }} transition={{ duration: 0.6, delay: i * 0.1 }} />
                          </div>
                        </div>
                        <div className="flex gap-6 text-center">
                          <div><div className="text-[16px] font-extrabold text-gray-900">{c.meetings}</div><div className="text-[10px] text-gray-400 font-medium">Meetings</div></div>
                          <div><div className="text-[16px] font-extrabold text-violet-600">{c.replyRate}%</div><div className="text-[10px] text-gray-400 font-medium">Reply</div></div>
                          <div><div className="text-[16px] font-extrabold text-emerald-600">{c.showRate}%</div><div className="text-[10px] text-gray-400 font-medium">Show</div></div>
                        </div>
                        <button className="p-1.5 text-gray-300 hover:text-gray-600"><MoreHorizontal className="w-4 h-4" /></button>
                      </div>
                    </motion.div>
                  ))}
                </div>
                <div className="px-5 py-3 border-t border-gray-50 flex justify-between">
                  <button className="px-3 py-1.5 bg-red-50 text-red-500 text-[12px] font-bold rounded-xl flex items-center gap-1.5 border border-red-100 hover:bg-red-100 transition-colors"><Pause className="w-3 h-3" /> Emergency Pause</button>
                  <button className="px-4 py-2 bg-gradient-to-r from-violet-500 to-pink-500 text-white text-[12px] font-bold rounded-xl flex items-center gap-1.5 shadow-lg shadow-violet-200 hover:shadow-xl hover:-translate-y-0.5 transition-all"><Play className="w-3.5 h-3.5" /> Confirm & Activate</button>
                </div>
              </div>

              {/* Activity */}
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h2 className="text-[13px] font-extrabold text-gray-900">Live Activity</h2>
                    <div className="flex items-center gap-1 px-2 py-0.5 bg-emerald-50 rounded-full"><span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" /><span className="text-[11px] font-bold text-emerald-600">Live</span></div>
                  </div>
                  <button className="text-[12px] text-violet-500 font-bold flex items-center gap-0.5">View All <ChevronRight className="w-3.5 h-3.5" /></button>
                </div>
                <div className="divide-y divide-gray-50">
                  {activities.map((a, i) => (
                    <motion.div key={a.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.06 }}
                      className="px-5 py-3 hover:bg-violet-50/20 flex items-center gap-3 transition-colors">
                      <ChannelIcon channel={a.channel} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[13px] font-semibold text-gray-900">{a.lead}</span>
                          <span className="text-[12px] text-gray-300">at</span>
                          <span className="text-[12px] text-gray-500">{a.company}</span>
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${tierLabel[a.tier]?.style}`}>{tierLabel[a.tier]?.label}</span>
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
              <div className="bg-gradient-to-br from-violet-500 to-pink-500 rounded-2xl p-5 text-white shadow-xl shadow-violet-200">
                <div className="flex justify-between mb-3"><span className="text-[11px] text-white/70 uppercase tracking-widest font-bold">Monthly Progress</span><span className="px-2 py-0.5 bg-white/20 text-white text-[11px] font-bold rounded-full">On Track</span></div>
                <div className="flex items-baseline gap-2 mb-3"><span className="text-5xl font-light"><NumberTicker value={12} className="text-white" /></span><span className="text-white/50 text-lg">of 18</span></div>
                <div className="h-2.5 bg-white/20 rounded-full overflow-hidden"><motion.div className="h-full bg-white rounded-full" initial={{ width: 0 }} animate={{ width: "67%" }} transition={{ duration: 1, delay: 0.4 }} /></div>
              </div>

              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-50 flex justify-between"><h2 className="text-[13px] font-extrabold text-gray-900">Upcoming Meetings</h2><span className="text-[11px] text-violet-400 font-bold">{meetings.length} scheduled</span></div>
                <div className="divide-y divide-gray-50">
                  {meetings.map((m, i) => (
                    <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                      className="px-5 py-3 hover:bg-violet-50/20 flex items-center gap-3 transition-colors">
                      <div className="text-center min-w-[44px] bg-violet-50 rounded-lg px-2 py-1"><div className="text-[9px] text-violet-600 uppercase font-bold">{m.day}</div><div className="text-[12px] font-bold text-gray-900">{m.time}</div></div>
                      <div className="flex-1"><div className="text-[13px] font-semibold text-gray-900">{m.lead}</div><div className="text-[11px] text-gray-400">{m.company}</div></div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${m.type === "Discovery" ? "bg-blue-50 text-blue-600 border-blue-200" : m.type === "Demo" ? "bg-emerald-50 text-emerald-600 border-emerald-200" : "bg-amber-50 text-amber-600 border-amber-200"}`}>{m.type}</span>
                    </motion.div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-50 flex justify-between"><h2 className="text-[13px] font-extrabold text-gray-900">Priority Prospects</h2><span className="px-2 py-0.5 bg-rose-50 text-rose-500 text-[11px] font-bold rounded-full border border-rose-200">Action</span></div>
                <div className="divide-y divide-gray-50">
                  {[
                    { name: "Sarah Chen", company: "TechCorp", tier: "hot", signals: ["Requested demo", "Opened 3x"] },
                    { name: "Lisa Park", company: "Acme Inc", tier: "hot", signals: ["Meeting scheduled", "LinkedIn engaged"] },
                    { name: "Tom Wilson", company: "DataFlow", tier: "warm", signals: ["Positive reply", "Website visit"] },
                  ].map((l) => (
                    <div key={l.name} className="px-5 py-3 hover:bg-violet-50/20 transition-colors">
                      <div className="flex justify-between mb-1.5">
                        <div><div className="text-[13px] font-semibold text-gray-900">{l.name}</div><div className="text-[11px] text-gray-400">{l.company}</div></div>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${tierLabel[l.tier]?.style}`}>{tierLabel[l.tier]?.label}</span>
                      </div>
                      <div className="flex gap-1">{l.signals.map((s, i) => <span key={i} className="px-2 py-0.5 bg-violet-50 text-violet-600 text-[10px] font-medium rounded">{s}</span>)}</div>
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

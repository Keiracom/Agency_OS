/**
 * V4 — "Warm Neutral"
 * Sand/cream tones, organic rounded shapes, warm amber/earth accents
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
    <div className="w-[260px] bg-[#faf8f5] flex flex-col h-screen fixed left-0 top-0 border-r border-[#e8e2da]">
      <div className="p-5 border-b border-[#e8e2da]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-amber-600 to-orange-700 rounded-2xl flex items-center justify-center shadow-lg shadow-amber-200/50">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-[15px] font-bold text-stone-800">Agency OS</span>
            <p className="text-[10px] text-amber-600 font-medium">WORKSPACE</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-0.5">
        {navItems.map((item) => (
          <button key={item.key} onClick={() => onNavigate(item.key)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all ${
              activePage === item.key
                ? "bg-stone-800 text-white shadow-md"
                : "text-stone-400 hover:text-stone-800 hover:bg-[#f0ebe4]"
            }`}>
            <item.icon className="w-[18px] h-[18px]" />
            <span className="flex-1 text-left">{item.label}</span>
            {item.badge && <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${activePage === item.key ? "bg-white/20" : "bg-stone-100 text-stone-500"}`}>{item.badge}</span>}
          </button>
        ))}
      </nav>
      <div className="p-4 border-t border-[#e8e2da]">
        <div className="flex items-center gap-3 px-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-white text-sm font-bold">A</div>
          <div><p className="text-[13px] font-medium text-stone-800">Acme Agency</p><p className="text-[11px] text-stone-400">Velocity Plan</p></div>
        </div>
      </div>
    </div>
  );
}

function ChannelIcon({ channel }: { channel: string }) {
  const config: Record<string, { bg: string; icon: typeof Mail }> = {
    email: { bg: "bg-sky-100 text-sky-700", icon: Mail },
    linkedin: { bg: "bg-blue-100 text-blue-700", icon: Linkedin },
    sms: { bg: "bg-emerald-100 text-emerald-700", icon: MessageCircle },
    voice: { bg: "bg-purple-100 text-purple-700", icon: Phone },
  };
  const { bg, icon: Icon } = config[channel] || config.email;
  return <div className={`w-7 h-7 rounded-lg ${bg} flex items-center justify-center`}><Icon className="w-3.5 h-3.5" /></div>;
}

export default function PrototypeV4() {
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
    hot: { label: "High Priority", style: "bg-orange-50 text-orange-700 border-orange-200" },
    warm: { label: "Engaged", style: "bg-amber-50 text-amber-700 border-amber-200" },
    cool: { label: "Nurturing", style: "bg-sky-50 text-sky-700 border-sky-200" },
  };

  return (
    <div className="min-h-screen bg-[#f5f2ed]">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <div className="ml-[260px]">
        <div className="h-14 bg-[#faf8f5]/80 backdrop-blur-xl border-b border-[#e8e2da] flex items-center justify-between px-6 sticky top-0 z-10">
          <h1 className="text-[15px] font-bold text-stone-800">Dashboard</h1>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-stone-300" />
              <input className="w-56 pl-9 pr-4 py-1.5 text-[13px] bg-white border border-[#e8e2da] rounded-xl text-stone-900 placeholder-stone-300 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-300" placeholder="Search..." />
            </div>
            <button className="relative p-2 text-stone-400 hover:text-stone-800"><Bell className="w-5 h-5" /><span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" /></button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "Meetings Booked", value: 12, change: 25, icon: Calendar, bg: "bg-white" },
              { label: "Show Rate", value: 83, suffix: "%", change: 5, icon: CheckCircle, bg: "bg-white" },
              { label: "Deals Created", value: 3, change: 50, icon: Sparkles, bg: "bg-white" },
              { label: "Reply Rate", value: 5, suffix: "%", change: 12, icon: MessageSquare, bg: "bg-white" },
            ].map((s, i) => (
              <div key={s.label} className={`${s.bg} rounded-2xl border border-[#e8e2da] p-5 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5`}>
                <div className="flex items-start justify-between mb-3">
                  <span className="text-[11px] font-medium text-stone-400 uppercase tracking-widest">{s.label}</span>
                  <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center"><s.icon className="w-[18px] h-[18px]" /></div>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-stone-800"><NumberTicker value={s.value} delay={i * 0.15} /></span>
                  {s.suffix && <span className="text-lg text-stone-300">{s.suffix}</span>}
                </div>
                <div className="flex items-center gap-1 mt-2">
                  <ArrowUpRight className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-[12px] font-medium text-emerald-600">+{s.change}%</span>
                  <span className="text-[11px] text-stone-300">vs last month</span>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-8 space-y-6">
              {/* Campaigns */}
              <div className="bg-white rounded-2xl border border-[#e8e2da] shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-[#f0ebe4] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h2 className="text-[13px] font-bold text-stone-800">Active Campaigns</h2>
                    <span className="px-2 py-0.5 bg-amber-50 text-amber-700 text-[11px] rounded-full border border-amber-200">3 of 5</span>
                  </div>
                  <button className="text-[12px] text-amber-700 font-medium flex items-center gap-1"><Plus className="w-3.5 h-3.5" /> Add Campaign</button>
                </div>
                <div className="divide-y divide-[#f0ebe4]">
                  {campaigns.map((c, i) => (
                    <motion.div key={c.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
                      className="px-5 py-4 hover:bg-amber-50/30 transition-colors">
                      <div className="flex items-center gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-emerald-100" />
                            <span className="text-[13px] font-semibold text-stone-800">{c.name}</span>
                            {c.isAI && <span className="px-1.5 py-0.5 bg-purple-50 text-purple-700 text-[10px] font-bold rounded border border-purple-200">AI</span>}
                          </div>
                          <div className="flex gap-1.5">{c.channels.map(ch => <ChannelIcon key={ch} channel={ch} />)}</div>
                        </div>
                        <div className="w-28">
                          <div className="flex justify-between text-[11px] text-stone-400 mb-1"><span>Priority</span><span className="text-amber-700 font-medium">{c.priority}%</span></div>
                          <div className="h-2 bg-stone-100 rounded-full overflow-hidden">
                            <motion.div className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full" initial={{ width: 0 }} animate={{ width: `${c.priority}%` }} transition={{ duration: 0.6, delay: i * 0.1 }} />
                          </div>
                        </div>
                        <div className="flex gap-6 text-center">
                          <div><div className="text-[15px] font-bold text-stone-800">{c.meetings}</div><div className="text-[10px] text-stone-400">Meetings</div></div>
                          <div><div className="text-[15px] font-bold text-amber-700">{c.replyRate}%</div><div className="text-[10px] text-stone-400">Reply</div></div>
                          <div><div className="text-[15px] font-bold text-emerald-700">{c.showRate}%</div><div className="text-[10px] text-stone-400">Show</div></div>
                        </div>
                        <button className="p-1.5 text-stone-300 hover:text-stone-600"><MoreHorizontal className="w-4 h-4" /></button>
                      </div>
                    </motion.div>
                  ))}
                </div>
                <div className="px-5 py-3 border-t border-[#f0ebe4] flex justify-between">
                  <button className="px-3 py-1.5 bg-red-50 text-red-700 text-[12px] font-medium rounded-xl flex items-center gap-1.5 border border-red-200"><Pause className="w-3 h-3" /> Emergency Pause</button>
                  <button className="px-4 py-1.5 bg-stone-800 text-white text-[12px] font-medium rounded-xl flex items-center gap-1.5 hover:bg-stone-700 transition-colors shadow-md"><Play className="w-3 h-3" /> Confirm & Activate</button>
                </div>
              </div>

              {/* Activity */}
              <div className="bg-white rounded-2xl border border-[#e8e2da] shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-[#f0ebe4] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h2 className="text-[13px] font-bold text-stone-800">Live Activity</h2>
                    <span className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[11px] rounded-full border border-emerald-200"><span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" /> Live</span>
                  </div>
                  <button className="text-[12px] text-stone-400 hover:text-stone-800 flex items-center gap-0.5">View All <ChevronRight className="w-3.5 h-3.5" /></button>
                </div>
                <div className="divide-y divide-[#f0ebe4]">
                  {activities.map((a, i) => (
                    <motion.div key={a.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.06 }}
                      className="px-5 py-3 hover:bg-amber-50/20 flex items-center gap-3 transition-colors">
                      <ChannelIcon channel={a.channel} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[13px] font-medium text-stone-800">{a.lead}</span>
                          <span className="text-[12px] text-stone-300">at</span>
                          <span className="text-[12px] text-stone-500">{a.company}</span>
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${tierLabel[a.tier]?.style}`}>{tierLabel[a.tier]?.label}</span>
                        </div>
                        <p className="text-[11px] text-stone-400 truncate">{a.action}</p>
                      </div>
                      <span className="text-[11px] text-stone-300">{a.time}</span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right */}
            <div className="col-span-4 space-y-6">
              <div className="bg-gradient-to-br from-stone-800 to-stone-900 rounded-2xl p-5 text-white shadow-xl">
                <div className="flex justify-between mb-3"><span className="text-[11px] text-stone-400 uppercase tracking-widest">Monthly Progress</span><span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-[11px] rounded-full">On Track</span></div>
                <div className="flex items-baseline gap-2 mb-3"><span className="text-4xl font-light"><NumberTicker value={12} className="text-white" /></span><span className="text-stone-500">of 18</span></div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden"><motion.div className="h-full bg-gradient-to-r from-amber-500 to-orange-400 rounded-full" initial={{ width: 0 }} animate={{ width: "67%" }} transition={{ duration: 1, delay: 0.4 }} /></div>
              </div>

              <div className="bg-white rounded-2xl border border-[#e8e2da] shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-[#f0ebe4] flex justify-between"><h2 className="text-[13px] font-bold text-stone-800">Upcoming Meetings</h2><span className="text-[11px] text-stone-400">{meetings.length} scheduled</span></div>
                <div className="divide-y divide-[#f0ebe4]">
                  {meetings.map((m, i) => (
                    <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                      className="px-5 py-3 hover:bg-amber-50/20 flex items-center gap-3 transition-colors">
                      <div className="text-center min-w-[44px]"><div className="text-[10px] text-stone-400 uppercase">{m.day}</div><div className="text-[13px] font-semibold text-stone-800">{m.time}</div></div>
                      <div className="flex-1"><div className="text-[13px] font-medium text-stone-800">{m.lead}</div><div className="text-[11px] text-stone-400">{m.company}</div></div>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium border ${m.type === "Discovery" ? "bg-sky-50 text-sky-700 border-sky-200" : m.type === "Demo" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-amber-50 text-amber-700 border-amber-200"}`}>{m.type}</span>
                    </motion.div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-2xl border border-[#e8e2da] shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-[#f0ebe4] flex justify-between"><h2 className="text-[13px] font-bold text-stone-800">Priority Prospects</h2><span className="px-2 py-0.5 bg-orange-50 text-orange-700 text-[11px] rounded-full border border-orange-200">Action</span></div>
                <div className="divide-y divide-[#f0ebe4]">
                  {[
                    { name: "Sarah Chen", company: "TechCorp", tier: "hot", signals: ["Requested demo", "Opened 3x"] },
                    { name: "Lisa Park", company: "Acme Inc", tier: "hot", signals: ["Meeting scheduled", "LinkedIn engaged"] },
                    { name: "Tom Wilson", company: "DataFlow", tier: "warm", signals: ["Positive reply", "Website visit"] },
                  ].map((l) => (
                    <div key={l.name} className="px-5 py-3 hover:bg-amber-50/20 transition-colors">
                      <div className="flex justify-between mb-1.5">
                        <div><div className="text-[13px] font-medium text-stone-800">{l.name}</div><div className="text-[11px] text-stone-400">{l.company}</div></div>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${tierLabel[l.tier]?.style}`}>{tierLabel[l.tier]?.label}</span>
                      </div>
                      <div className="flex gap-1">{l.signals.map((s, i) => <span key={i} className="px-2 py-0.5 bg-[#f5f2ed] text-stone-500 text-[10px] rounded">{s}</span>)}</div>
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
